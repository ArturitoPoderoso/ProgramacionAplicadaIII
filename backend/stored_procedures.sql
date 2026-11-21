-- =============================================================================
-- SUITE COMPLETA DE PROCEDIMIENTOS ALMACENADOS Y FUNCIONES PL/pgSQL
-- SISTEMA JESMI - ARQUITECTURA EMPRESARIAL DE BASE DE DATOS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. VENTAS: sp_procesar_venta y sp_anular_venta
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_procesar_venta;
CREATE OR REPLACE PROCEDURE sp_procesar_venta(
    p_id_usuario INT,
    p_id_sede INT,
    p_id_cliente INT,
    p_cliente_nombre VARCHAR,
    p_cliente_doc VARCHAR,
    p_correlativo VARCHAR,
    p_total DOUBLE PRECISION,
    p_descuento_total DOUBLE PRECISION,
    p_metodo_pago VARCHAR,
    p_detalles JSONB,
    INOUT o_id_venta INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_item JSONB;
    v_id_producto INT;
    v_cantidad INT;
    v_precio_unitario DOUBLE PRECISION;
    v_descuento_unitario DOUBLE PRECISION;
    v_subtotal DOUBLE PRECISION;
    v_stock_actual INT;
    v_precio_compra DOUBLE PRECISION;
    v_nombre_prod VARCHAR;
    v_precio_efectivo DOUBLE PRECISION;
BEGIN
    IF p_detalles IS NULL OR jsonb_array_length(p_detalles) = 0 THEN
        RAISE EXCEPTION 'La venta debe contener al menos un producto.';
    END IF;

    -- Validar stock de cada producto con bloqueo atómico FOR UPDATE
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_detalles)
    LOOP
        v_id_producto := (v_item->>'id_producto')::INT;
        v_cantidad := (v_item->>'cantidad')::INT;
        v_precio_unitario := (v_item->>'precio_unitario')::DOUBLE PRECISION;
        v_descuento_unitario := COALESCE((v_item->>'descuento_unitario')::DOUBLE PRECISION, 0.0);
        v_precio_efectivo := v_precio_unitario - v_descuento_unitario;

        SELECT i.stock_actual, COALESCE(i.precio_compra, 0.0), p.nombre 
        INTO v_stock_actual, v_precio_compra, v_nombre_prod
        FROM inventario_sedes i
        JOIN productos p ON p.id_producto = i.id_producto
        WHERE i.id_producto = v_id_producto AND i.id_sede = p_id_sede
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'El producto ID % no existe en el inventario de esta sede.', v_id_producto;
        END IF;

        IF v_stock_actual < v_cantidad THEN
            RAISE EXCEPTION 'Stock insuficiente para "%" en esta sede. Stock actual: %, solicitado: %', 
                v_nombre_prod, v_stock_actual, v_cantidad;
        END IF;

        IF v_precio_efectivo < v_precio_compra THEN
            RAISE EXCEPTION 'El precio final de "%" (S/ %) es inferior al costo de compra (S/ %).',
                v_nombre_prod, v_precio_efectivo, v_precio_compra;
        END IF;
    END LOOP;

    -- Insertar cabecera de la venta
    INSERT INTO ventas (
        correlativo, total, descuento_total, metodo_pago,
        id_usuario, id_sede, id_cliente, cliente_nombre, cliente_doc,
        fecha_venta, estado_registro
    ) VALUES (
        p_correlativo, p_total, p_descuento_total, p_metodo_pago,
        p_id_usuario, p_id_sede, p_id_cliente, p_cliente_nombre, p_cliente_doc,
        NOW(), 1
    ) RETURNING id_venta INTO o_id_venta;

    -- Descontar inventario, insertar detalles y registrar movimiento en Kardex
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_detalles)
    LOOP
        v_id_producto := (v_item->>'id_producto')::INT;
        v_cantidad := (v_item->>'cantidad')::INT;
        v_precio_unitario := (v_item->>'precio_unitario')::DOUBLE PRECISION;
        v_descuento_unitario := COALESCE((v_item->>'descuento_unitario')::DOUBLE PRECISION, 0.0);
        v_subtotal := (v_item->>'subtotal')::DOUBLE PRECISION;

        UPDATE inventario_sedes
        SET stock_actual = stock_actual - v_cantidad
        WHERE id_producto = v_id_producto AND id_sede = p_id_sede;

        INSERT INTO detalle_ventas (
            id_venta, id_producto, cantidad,
            precio_unitario, descuento_unitario, subtotal
        ) VALUES (
            o_id_venta, v_id_producto, v_cantidad,
            v_precio_unitario, v_descuento_unitario, v_subtotal
        );

        INSERT INTO movimientos_almacen (
            id_producto, id_sede, tipo, cantidad,
            id_usuario, observacion, fecha
        ) VALUES (
            v_id_producto, p_id_sede, 'SALIDA', -v_cantidad,
            p_id_usuario, CONCAT('Venta ticket ', p_correlativo), NOW()
        );
    END LOOP;

    o_mensaje := 'Venta procesada exitosamente';
END;
$$;

DROP PROCEDURE IF EXISTS sp_anular_venta;
CREATE OR REPLACE PROCEDURE sp_anular_venta(
    p_id_venta INT,
    p_id_usuario INT,
    p_motivo VARCHAR,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_venta RECORD;
    v_det RECORD;
BEGIN
    SELECT * INTO v_venta FROM ventas WHERE id_venta = p_id_venta FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Venta ID % no encontrada.', p_id_venta;
    END IF;

    IF v_venta.estado_registro = 0 THEN
        RAISE EXCEPTION 'La venta ID % ya fue anulada previamente.', p_id_venta;
    END IF;

    -- Devolver stock al inventario y registrar en Kardex
    FOR v_det IN SELECT * FROM detalle_ventas WHERE id_venta = p_id_venta
    LOOP
        UPDATE inventario_sedes
        SET stock_actual = stock_actual + v_det.cantidad
        WHERE id_producto = v_det.id_producto AND id_sede = v_venta.id_sede;

        INSERT INTO movimientos_almacen (
            id_producto, id_sede, tipo, cantidad,
            id_usuario, observacion, fecha
        ) VALUES (
            v_det.id_producto, v_venta.id_sede, 'ENTRADA', v_det.cantidad,
            p_id_usuario, CONCAT('Anulación venta ticket ', v_venta.correlativo, ': ', COALESCE(p_motivo, 'Sin motivo')), NOW()
        );
    END LOOP;

    -- Marcar venta como anulada
    UPDATE ventas 
    SET estado_registro = 0 
    WHERE id_venta = p_id_venta;

    o_mensaje := 'Venta anulada correctamente y stock devuelto.';
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. CLIENTES: sp_guardar_cliente y sp_eliminar_cliente
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_guardar_cliente;
CREATE OR REPLACE PROCEDURE sp_guardar_cliente(
    p_id_cliente INT,
    p_tipo_documento VARCHAR,
    p_numero_documento VARCHAR,
    p_nombre VARCHAR,
    p_telefono VARCHAR,
    INOUT o_id_cliente INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existente RECORD;
BEGIN
    IF p_id_cliente IS NOT NULL AND p_id_cliente > 0 THEN
        SELECT id_cliente, nombre INTO v_existente 
        FROM clientes 
        WHERE numero_documento = p_numero_documento 
          AND id_cliente <> p_id_cliente 
          AND estado_registro = 1;

        IF FOUND THEN
            RAISE EXCEPTION 'El documento % ya está registrado para otro cliente (%).', p_numero_documento, v_existente.nombre;
        END IF;

        UPDATE clientes
        SET tipo_documento = COALESCE(p_tipo_documento, tipo_documento),
            numero_documento = COALESCE(p_numero_documento, numero_documento),
            nombre = COALESCE(p_nombre, nombre),
            telefono = COALESCE(p_telefono, telefono),
            estado_registro = 1
        WHERE id_cliente = p_id_cliente;

        o_id_cliente := p_id_cliente;
        o_mensaje := 'Cliente actualizado con éxito';
    ELSE
        SELECT id_cliente, estado_registro, nombre INTO v_existente
        FROM clientes
        WHERE numero_documento = p_numero_documento;

        IF FOUND THEN
            IF v_existente.estado_registro = 1 THEN
                RAISE EXCEPTION 'El documento % ya está registrado a nombre de "%".', p_numero_documento, v_existente.nombre;
            ELSE
                UPDATE clientes
                SET tipo_documento = p_tipo_documento,
                    nombre = p_nombre,
                    telefono = p_telefono,
                    estado_registro = 1
                WHERE id_cliente = v_existente.id_cliente;

                o_id_cliente := v_existente.id_cliente;
                o_mensaje := 'Cliente reactivado y actualizado con éxito';
            END IF;
        ELSE
            INSERT INTO clientes (
                tipo_documento, numero_documento, nombre, telefono, estado_registro, fecha_registro
            ) VALUES (
                p_tipo_documento, p_numero_documento, p_nombre, p_telefono, 1, NOW()
            ) RETURNING id_cliente INTO o_id_cliente;

            o_mensaje := 'Cliente registrado exitosamente';
        END IF;
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS sp_eliminar_cliente;
CREATE OR REPLACE PROCEDURE sp_eliminar_cliente(
    p_id_cliente INT,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_cliente RECORD;
BEGIN
    SELECT * INTO v_cliente FROM clientes WHERE id_cliente = p_id_cliente AND estado_registro = 1;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cliente ID % no encontrado o ya inactivo.', p_id_cliente;
    END IF;

    UPDATE clientes SET estado_registro = 0 WHERE id_cliente = p_id_cliente;
    o_mensaje := CONCAT('Cliente "', v_cliente.nombre, '" eliminado exitosamente');
END;
$$;

-- -----------------------------------------------------------------------------
-- 3. ALMACÉN Y PRODUCTOS: sp_guardar_producto
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_guardar_producto;
CREATE OR REPLACE PROCEDURE sp_guardar_producto(
    p_id_producto INT,
    p_codigo_producto VARCHAR,
    p_nombre VARCHAR,
    p_descripcion VARCHAR,
    p_id_categoria INT,
    p_id_subcategoria INT,
    p_precio_venta DOUBLE PRECISION,
    p_precio_compra DOUBLE PRECISION,
    p_stock_actual INT,
    p_stock_minimo INT,
    p_id_sede INT,
    p_id_usuario INT,
    INOUT o_id_producto INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sede RECORD;
    v_prod RECORD;
BEGIN
    IF p_id_producto IS NOT NULL AND p_id_producto > 0 THEN
        UPDATE productos
        SET nombre = p_nombre,
            codigo_producto = p_codigo_producto,
            descripcion = p_descripcion,
            id_categoria = p_id_categoria,
            id_subcategoria = p_id_subcategoria
        WHERE id_producto = p_id_producto;
        o_id_producto := p_id_producto;

        IF p_id_sede IS NOT NULL THEN
            UPDATE inventario_sedes
            SET precio_venta = COALESCE(p_precio_venta, precio_venta),
                precio_compra = COALESCE(p_precio_compra, precio_compra),
                stock_minimo = COALESCE(p_stock_minimo, stock_minimo)
            WHERE id_producto = p_id_producto AND id_sede = p_id_sede;
        END IF;

        o_mensaje := 'Producto actualizado exitosamente';
    ELSE
        SELECT * INTO v_prod FROM productos WHERE codigo_producto = p_codigo_producto;
        IF FOUND THEN
            o_id_producto := v_prod.id_producto;
        ELSE
            INSERT INTO productos (
                codigo_producto, nombre, descripcion, id_categoria, id_subcategoria, estado_registro
            ) VALUES (
                p_codigo_producto, p_nombre, p_descripcion, p_id_categoria, p_id_subcategoria, 1
            ) RETURNING id_producto INTO o_id_producto;
        END IF;

        FOR v_sede IN SELECT id_sede FROM sedes
        LOOP
            INSERT INTO inventario_sedes (
                id_producto, id_sede, stock_actual, stock_minimo, precio_compra, precio_venta, estado_registro
            ) VALUES (
                o_id_producto, v_sede.id_sede, 0, COALESCE(p_stock_minimo, 5), COALESCE(p_precio_compra, 0.0), COALESCE(p_precio_venta, 0.0), 1
            ) ON CONFLICT DO NOTHING;
        END LOOP;

        IF p_id_sede IS NOT NULL THEN
            UPDATE inventario_sedes
            SET stock_actual = COALESCE(p_stock_actual, 0),
                precio_compra = COALESCE(p_precio_compra, 0.0),
                precio_venta = COALESCE(p_precio_venta, 0.0),
                stock_minimo = COALESCE(p_stock_minimo, 5)
            WHERE id_producto = o_id_producto AND id_sede = p_id_sede;

            IF p_stock_actual IS NOT NULL AND p_stock_actual > 0 THEN
                INSERT INTO movimientos_almacen (
                    id_producto, id_sede, tipo, cantidad,
                    id_usuario, observacion, fecha
                ) VALUES (
                    o_id_producto, p_id_sede, 'ENTRADA', p_stock_actual,
                    p_id_usuario, 'Stock inicial al crear/agregar producto a sede', NOW()
                );
            END IF;
        END IF;

        o_mensaje := 'Producto creado e inicializado exitosamente';
    END IF;
END;
$$;

-- -----------------------------------------------------------------------------
-- 4. COMPRAS: sp_procesar_compra, sp_recibir_compra y sp_anular_compra
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_procesar_compra;
CREATE OR REPLACE PROCEDURE sp_procesar_compra(
    p_id_usuario INT,
    p_id_sede INT,
    p_id_proveedor INT,
    p_correlativo VARCHAR,
    p_total DOUBLE PRECISION,
    p_fecha_esperada VARCHAR,
    p_observacion TEXT,
    p_detalles JSONB,
    INOUT o_id_compra INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_item JSONB;
    v_id_producto INT;
    v_cantidad INT;
    v_precio_unitario DOUBLE PRECISION;
    v_subtotal DOUBLE PRECISION;
BEGIN
    IF p_detalles IS NULL OR jsonb_array_length(p_detalles) = 0 THEN
        RAISE EXCEPTION 'La orden de compra debe contener al menos un producto.';
    END IF;

    INSERT INTO ordenes_compra (
        correlativo, id_proveedor, id_sede, id_usuario,
        fecha_emision, fecha_esperada, estado, total, observacion, estado_registro
    ) VALUES (
        p_correlativo, p_id_proveedor, p_id_sede, p_id_usuario,
        NOW(), p_fecha_esperada, 'PENDIENTE', p_total, p_observacion, 1
    ) RETURNING id_orden_compra INTO o_id_compra;

    FOR v_item IN SELECT * FROM jsonb_array_elements(p_detalles)
    LOOP
        v_id_producto := (v_item->>'id_producto')::INT;
        v_cantidad := (v_item->>'cantidad')::INT;
        v_precio_unitario := (v_item->>'precio_unitario')::DOUBLE PRECISION;
        v_subtotal := (v_item->>'subtotal')::DOUBLE PRECISION;

        INSERT INTO detalle_ordenes_compra (
            id_orden_compra, id_producto, cantidad_solicitada, cantidad_recibida, precio_unitario, subtotal
        ) VALUES (
            o_id_compra, v_id_producto, v_cantidad, 0, v_precio_unitario, v_subtotal
        );
    END LOOP;

    o_mensaje := CONCAT('Orden de compra ', p_correlativo, ' emitida con éxito.');
END;
$$;

DROP PROCEDURE IF EXISTS sp_recibir_compra;
CREATE OR REPLACE PROCEDURE sp_recibir_compra(
    p_id_orden INT,
    p_id_usuario INT,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_orden RECORD;
    v_det RECORD;
    v_prov_nombre VARCHAR;
BEGIN
    SELECT * INTO v_orden FROM ordenes_compra WHERE id_orden_compra = p_id_orden AND estado_registro = 1 FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Orden de compra ID % no encontrada.', p_id_orden;
    END IF;

    IF v_orden.estado = 'RECIBIDA' THEN
        RAISE EXCEPTION 'La orden % ya fue recibida e ingresada al almacén anteriormente.', v_orden.correlativo;
    END IF;

    IF v_orden.estado = 'ANULADA' THEN
        RAISE EXCEPTION 'La orden % está anulada. No se puede recibir mercadería.', v_orden.correlativo;
    END IF;

    SELECT razon_social INTO v_prov_nombre FROM proveedores WHERE id_proveedor = v_orden.id_proveedor;

    FOR v_det IN SELECT * FROM detalle_ordenes_compra WHERE id_orden_compra = p_id_orden
    LOOP
        UPDATE detalle_ordenes_compra
        SET cantidad_recibida = v_det.cantidad_solicitada
        WHERE id_detalle_oc = v_det.id_detalle_oc;

        INSERT INTO inventario_sedes (
            id_producto, id_sede, stock_actual, stock_minimo, precio_compra, precio_venta, estado_registro
        ) VALUES (
            v_det.id_producto, v_orden.id_sede, v_det.cantidad_solicitada, 5, v_det.precio_unitario, ROUND((v_det.precio_unitario * 1.30)::numeric, 2), 1
        )
        ON CONFLICT (id_producto, id_sede) 
        DO UPDATE SET 
            stock_actual = inventario_sedes.stock_actual + v_det.cantidad_solicitada,
            precio_compra = v_det.precio_unitario,
            estado_registro = 1;

        INSERT INTO movimientos_almacen (
            id_producto, id_sede, tipo, cantidad,
            id_usuario, observacion, fecha
        ) VALUES (
            v_det.id_producto, v_orden.id_sede, 'ENTRADA', v_det.cantidad_solicitada,
            p_id_usuario, CONCAT('Ingreso por Compra ', v_orden.correlativo, ' - Proveedor: ', COALESCE(v_prov_nombre, 'Proveedor')), NOW()
        );
    END LOOP;

    UPDATE ordenes_compra
    SET estado = 'RECIBIDA',
        fecha_recepcion = NOW()
    WHERE id_orden_compra = p_id_orden;

    o_mensaje := CONCAT('¡Mercadería de la orden ', v_orden.correlativo, ' recibida exitosamente! Se actualizó el stock en almacén.');
END;
$$;

DROP PROCEDURE IF EXISTS sp_anular_compra;
CREATE OR REPLACE PROCEDURE sp_anular_compra(
    p_id_orden INT,
    p_id_usuario INT,
    p_motivo VARCHAR,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_orden RECORD;
    v_det RECORD;
    v_stock_actual INT;
    v_cant_revertir INT;
    v_prod_nombre VARCHAR;
BEGIN
    SELECT * INTO v_orden FROM ordenes_compra WHERE id_orden_compra = p_id_orden AND estado_registro = 1 FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Orden de compra ID % no encontrada.', p_id_orden;
    END IF;

    IF v_orden.estado = 'ANULADA' THEN
        RAISE EXCEPTION 'Esta orden ya se encuentra anulada.';
    END IF;

    IF v_orden.estado = 'RECIBIDA' THEN
        FOR v_det IN SELECT * FROM detalle_ordenes_compra WHERE id_orden_compra = p_id_orden
        LOOP
            v_cant_revertir := COALESCE(v_det.cantidad_recibida, v_det.cantidad_solicitada);
            SELECT i.stock_actual, p.nombre INTO v_stock_actual, v_prod_nombre
            FROM inventario_sedes i
            JOIN productos p ON p.id_producto = i.id_producto
            WHERE i.id_producto = v_det.id_producto AND i.id_sede = v_orden.id_sede;

            IF v_stock_actual IS NULL OR v_stock_actual < v_cant_revertir THEN
                RAISE EXCEPTION 'No se puede anular: El producto "%" ya fue vendido o despachado y no cuenta con suficiente stock en almacén para revertir.', v_prod_nombre;
            END IF;
        END LOOP;

        FOR v_det IN SELECT * FROM detalle_ordenes_compra WHERE id_orden_compra = p_id_orden
        LOOP
            v_cant_revertir := COALESCE(v_det.cantidad_recibida, v_det.cantidad_solicitada);

            UPDATE inventario_sedes
            SET stock_actual = stock_actual - v_cant_revertir
            WHERE id_producto = v_det.id_producto AND id_sede = v_orden.id_sede;

            INSERT INTO movimientos_almacen (
                id_producto, id_sede, tipo, cantidad,
                id_usuario, observacion, fecha
            ) VALUES (
                v_det.id_producto, v_orden.id_sede, 'SALIDA', -v_cant_revertir,
                p_id_usuario, CONCAT('Reversión por Anulación de Compra ', v_orden.correlativo, '. Motivo: ', COALESCE(p_motivo, 'Sin motivo')), NOW()
            );
        END LOOP;
    END IF;

    UPDATE ordenes_compra
    SET estado = 'ANULADA',
        observacion = CONCAT(COALESCE(observacion, ''), ' [ANULADA: ', COALESCE(p_motivo, 'Sin motivo'), ']')
    WHERE id_orden_compra = p_id_orden;

    o_mensaje := CONCAT('Orden de compra ', v_orden.correlativo, ' anulada correctamente.');
END;
$$;

-- -----------------------------------------------------------------------------
-- 5. PROVEEDORES: sp_guardar_proveedor y sp_eliminar_proveedor
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_guardar_proveedor;
CREATE OR REPLACE PROCEDURE sp_guardar_proveedor(
    p_id_proveedor INT,
    p_id_sede INT,
    p_ruc VARCHAR,
    p_razon_social VARCHAR,
    p_nombre_contacto VARCHAR,
    p_telefono VARCHAR,
    p_correo VARCHAR,
    p_direccion VARCHAR,
    p_condiciones_pago VARCHAR,
    INOUT o_id_proveedor INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existente RECORD;
BEGIN
    IF p_id_proveedor IS NOT NULL AND p_id_proveedor > 0 THEN
        SELECT id_proveedor, razon_social INTO v_existente
        FROM proveedores
        WHERE ruc = p_ruc 
          AND id_sede = p_id_sede 
          AND id_proveedor <> p_id_proveedor 
          AND estado_registro = 1;

        IF FOUND THEN
            RAISE EXCEPTION 'El RUC % ya pertenece a otro proveedor (%) en esta sede.', p_ruc, v_existente.razon_social;
        END IF;

        UPDATE proveedores
        SET id_sede = p_id_sede,
            ruc = p_ruc,
            razon_social = p_razon_social,
            nombre_contacto = p_nombre_contacto,
            telefono = p_telefono,
            correo = p_correo,
            direccion = p_direccion,
            condiciones_pago = COALESCE(p_condiciones_pago, 'Contado')
        WHERE id_proveedor = p_id_proveedor;

        o_id_proveedor := p_id_proveedor;
        o_mensaje := 'Proveedor actualizado correctamente.';
    ELSE
        SELECT id_proveedor, estado_registro, razon_social INTO v_existente
        FROM proveedores
        WHERE ruc = p_ruc AND id_sede = p_id_sede;

        IF FOUND THEN
            IF v_existente.estado_registro = 1 THEN
                RAISE EXCEPTION 'El RUC % ya se encuentra registrado para "%" en esta sede.', p_ruc, v_existente.razon_social;
            ELSE
                UPDATE proveedores
                SET razon_social = p_razon_social,
                    nombre_contacto = p_nombre_contacto,
                    telefono = p_telefono,
                    correo = p_correo,
                    direccion = p_direccion,
                    condiciones_pago = COALESCE(p_condiciones_pago, 'Contado'),
                    estado_registro = 1
                WHERE id_proveedor = v_existente.id_proveedor;

                o_id_proveedor := v_existente.id_proveedor;
                o_mensaje := 'Proveedor reactivado y actualizado con éxito.';
            END IF;
        ELSE
            INSERT INTO proveedores (
                id_sede, ruc, razon_social, nombre_contacto, telefono, correo, direccion, condiciones_pago, estado_registro, fecha_registro
            ) VALUES (
                COALESCE(p_id_sede, 1), p_ruc, p_razon_social, p_nombre_contacto, p_telefono, p_correo, p_direccion, COALESCE(p_condiciones_pago, 'Contado'), 1, NOW()
            ) RETURNING id_proveedor INTO o_id_proveedor;

            o_mensaje := 'Proveedor registrado con éxito.';
        END IF;
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS sp_eliminar_proveedor;
CREATE OR REPLACE PROCEDURE sp_eliminar_proveedor(
    p_id_proveedor INT,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_prov RECORD;
    v_compras INT;
BEGIN
    SELECT * INTO v_prov FROM proveedores WHERE id_proveedor = p_id_proveedor AND estado_registro = 1;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Proveedor ID % no encontrado.', p_id_proveedor;
    END IF;

    SELECT COUNT(*) INTO v_compras 
    FROM ordenes_compra 
    WHERE id_proveedor = p_id_proveedor AND estado_registro = 1;

    IF v_compras > 0 THEN
        RAISE EXCEPTION 'No se puede eliminar a "%" porque tiene % orden(es) de compra registrada(s). Por integridad contable y de auditoría la acción fue rechazada.', v_prov.razon_social, v_compras;
    END IF;

    UPDATE proveedores SET estado_registro = 0 WHERE id_proveedor = p_id_proveedor;
    o_mensaje := CONCAT('Proveedor "', v_prov.razon_social, '" eliminado con éxito.');
END;
$$;

-- -----------------------------------------------------------------------------
-- 6. CATEGORÍAS Y SUBCATEGORÍAS
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_guardar_categoria;
CREATE OR REPLACE PROCEDURE sp_guardar_categoria(
    p_id_categoria INT,
    p_nombre VARCHAR,
    p_descripcion VARCHAR,
    p_id_padre INT,
    INOUT o_id_categoria INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existente RECORD;
BEGIN
    IF p_id_categoria IS NOT NULL AND p_id_categoria > 0 THEN
        SELECT id_categoria, nombre INTO v_existente 
        FROM categorias 
        WHERE LOWER(nombre) = LOWER(p_nombre) 
          AND id_categoria <> p_id_categoria 
          AND estado_registro = 1;

        IF FOUND THEN
            RAISE EXCEPTION 'La categoría "%" ya existe.', p_nombre;
        END IF;

        UPDATE categorias
        SET nombre = p_nombre,
            descripcion = COALESCE(p_descripcion, descripcion),
            id_padre = p_id_padre
        WHERE id_categoria = p_id_categoria;

        o_id_categoria := p_id_categoria;
        o_mensaje := 'Categoría actualizada exitosamente';
    ELSE
        SELECT id_categoria, estado_registro INTO v_existente 
        FROM categorias 
        WHERE LOWER(nombre) = LOWER(p_nombre);

        IF FOUND THEN
            IF v_existente.estado_registro = 1 THEN
                RAISE EXCEPTION 'La categoría "%" ya existe.', p_nombre;
            ELSE
                UPDATE categorias
                SET descripcion = p_descripcion,
                    id_padre = p_id_padre,
                    estado_registro = 1
                WHERE id_categoria = v_existente.id_categoria;
                o_id_categoria := v_existente.id_categoria;
                o_mensaje := 'Categoría reactivada exitosamente';
            END IF;
        ELSE
            INSERT INTO categorias (nombre, descripcion, id_padre, estado_registro)
            VALUES (p_nombre, p_descripcion, p_id_padre, 1)
            RETURNING id_categoria INTO o_id_categoria;
            o_mensaje := 'Categoría creada exitosamente';
        END IF;
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS sp_guardar_subcategoria;
CREATE OR REPLACE PROCEDURE sp_guardar_subcategoria(
    p_id_subcategoria INT,
    p_nombre VARCHAR,
    p_descripcion VARCHAR,
    p_id_categoria INT,
    INOUT o_id_subcategoria INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_id_subcategoria IS NOT NULL AND p_id_subcategoria > 0 THEN
        UPDATE subcategorias
        SET nombre = COALESCE(p_nombre, nombre),
            descripcion = COALESCE(p_descripcion, descripcion),
            id_categoria = COALESCE(p_id_categoria, id_categoria)
        WHERE id_subcategoria = p_id_subcategoria;

        o_id_subcategoria := p_id_subcategoria;
        o_mensaje := 'Subcategoría actualizada exitosamente';
    ELSE
        INSERT INTO subcategorias (nombre, descripcion, id_categoria, estado_registro)
        VALUES (p_nombre, p_descripcion, p_id_categoria, 1)
        RETURNING id_subcategoria INTO o_id_subcategoria;
        o_mensaje := 'Subcategoría creada exitosamente';
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS sp_eliminar_subcategoria;
CREATE OR REPLACE PROCEDURE sp_eliminar_subcategoria(
    p_id_subcategoria INT,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE subcategorias SET estado_registro = 0 WHERE id_subcategoria = p_id_subcategoria;
    o_mensaje := 'Subcategoría eliminada exitosamente';
END;
$$;

-- -----------------------------------------------------------------------------
-- 7. FUNCIONES DE LECTURA (SELECT) - VENTAS
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_listar_ventas(INT, INT, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR);
CREATE OR REPLACE FUNCTION fn_listar_ventas(
    p_id_sede INT DEFAULT NULL,
    p_id_usuario INT DEFAULT NULL,
    p_fecha_inicio TIMESTAMPTZ DEFAULT NULL,
    p_fecha_fin TIMESTAMPTZ DEFAULT NULL,
    p_search VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id_venta INT,
    correlativo VARCHAR,
    total DOUBLE PRECISION,
    descuento_total DOUBLE PRECISION,
    metodo_pago VARCHAR,
    id_usuario INT,
    usuario_nombre VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    id_cliente INT,
    cliente_nombre VARCHAR,
    cliente_doc VARCHAR,
    fecha_venta TIMESTAMPTZ,
    estado_registro INT,
    total_items BIGINT,
    total_unidades BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id_venta,
        v.correlativo,
        v.total,
        COALESCE(v.descuento_total, 0.0),
        v.metodo_pago,
        v.id_usuario,
        CONCAT(u.nombres, ' ', u.apellidos)::VARCHAR AS usuario_nombre,
        v.id_sede,
        s.nombre AS sede_nombre,
        v.id_cliente,
        v.cliente_nombre,
        v.cliente_doc,
        v.fecha_venta,
        v.estado_registro,
        COUNT(d.id_detalle)::BIGINT AS total_items,
        COALESCE(SUM(d.cantidad), 0)::BIGINT AS total_unidades
    FROM ventas v
    LEFT JOIN usuarios u ON u.id_usuario = v.id_usuario
    LEFT JOIN sedes s ON s.id_sede = v.id_sede
    LEFT JOIN detalle_ventas d ON d.id_venta = v.id_venta
    WHERE v.estado_registro = 1
      AND (p_id_sede IS NULL OR v.id_sede = p_id_sede)
      AND (p_id_usuario IS NULL OR v.id_usuario = p_id_usuario)
      AND (p_fecha_inicio IS NULL OR v.fecha_venta >= p_fecha_inicio)
      AND (p_fecha_fin IS NULL OR v.fecha_venta <= p_fecha_fin)
      AND (
          p_search IS NULL OR p_search = '' 
          OR v.correlativo ILIKE '%' || p_search || '%'
          OR v.cliente_nombre ILIKE '%' || p_search || '%'
          OR v.cliente_doc ILIKE '%' || p_search || '%'
      )
    GROUP BY v.id_venta, u.nombres, u.apellidos, s.nombre
    ORDER BY v.fecha_venta DESC;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_venta_cabecera(INT);
CREATE OR REPLACE FUNCTION fn_obtener_venta_cabecera(p_id_venta INT)
RETURNS TABLE (
    id_venta INT,
    correlativo VARCHAR,
    total DOUBLE PRECISION,
    descuento_total DOUBLE PRECISION,
    metodo_pago VARCHAR,
    id_usuario INT,
    usuario_nombre VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    sede_direccion VARCHAR,
    id_cliente INT,
    cliente_nombre VARCHAR,
    cliente_doc VARCHAR,
    fecha_venta TIMESTAMPTZ,
    estado_registro INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id_venta,
        v.correlativo,
        v.total,
        COALESCE(v.descuento_total, 0.0),
        v.metodo_pago,
        v.id_usuario,
        CONCAT(u.nombres, ' ', u.apellidos)::VARCHAR AS usuario_nombre,
        v.id_sede,
        s.nombre AS sede_nombre,
        COALESCE(s.direccion, '')::VARCHAR AS sede_direccion,
        v.id_cliente,
        v.cliente_nombre,
        v.cliente_doc,
        v.fecha_venta,
        v.estado_registro
    FROM ventas v
    LEFT JOIN usuarios u ON u.id_usuario = v.id_usuario
    LEFT JOIN sedes s ON s.id_sede = v.id_sede
    WHERE v.id_venta = p_id_venta;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_venta_detalle(INT);
CREATE OR REPLACE FUNCTION fn_obtener_venta_detalle(p_id_venta INT)
RETURNS TABLE (
    id_detalle INT,
    id_producto INT,
    codigo_producto VARCHAR,
    producto_nombre VARCHAR,
    cantidad INT,
    precio_unitario DOUBLE PRECISION,
    descuento_unitario DOUBLE PRECISION,
    subtotal DOUBLE PRECISION
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id_detalle,
        d.id_producto,
        p.codigo_producto,
        p.nombre AS producto_nombre,
        d.cantidad,
        d.precio_unitario,
        COALESCE(d.descuento_unitario, 0.0),
        d.subtotal
    FROM detalle_ventas d
    LEFT JOIN productos p ON p.id_producto = d.id_producto
    WHERE d.id_venta = p_id_venta;
END;
$$;

-- -----------------------------------------------------------------------------
-- 8. FUNCIONES DE LECTURA (SELECT) - COMPRAS
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_listar_compras(INT, VARCHAR, VARCHAR);
CREATE OR REPLACE FUNCTION fn_listar_compras(
    p_id_sede INT DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_search VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id_orden_compra INT,
    correlativo VARCHAR,
    id_proveedor INT,
    proveedor_nombre VARCHAR,
    proveedor_ruc VARCHAR,
    proveedor_telefono VARCHAR,
    proveedor_contacto VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    id_usuario INT,
    usuario_nombre VARCHAR,
    fecha_emision TIMESTAMPTZ,
    fecha_esperada VARCHAR,
    fecha_recepcion TIMESTAMPTZ,
    estado VARCHAR,
    total DOUBLE PRECISION,
    observacion TEXT,
    total_items BIGINT,
    total_unidades BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.id_orden_compra,
        o.correlativo,
        o.id_proveedor,
        pr.razon_social AS proveedor_nombre,
        pr.ruc AS proveedor_ruc,
        pr.telefono AS proveedor_telefono,
        pr.nombre_contacto AS proveedor_contacto,
        o.id_sede,
        s.nombre AS sede_nombre,
        o.id_usuario,
        CONCAT(u.nombres, ' ', u.apellidos)::VARCHAR AS usuario_nombre,
        o.fecha_emision,
        o.fecha_esperada,
        o.fecha_recepcion,
        o.estado,
        o.total,
        o.observacion,
        COUNT(d.id_detalle_oc)::BIGINT AS total_items,
        COALESCE(SUM(d.cantidad_solicitada), 0)::BIGINT AS total_unidades
    FROM ordenes_compra o
    LEFT JOIN proveedores pr ON pr.id_proveedor = o.id_proveedor
    LEFT JOIN sedes s ON s.id_sede = o.id_sede
    LEFT JOIN usuarios u ON u.id_usuario = o.id_usuario
    LEFT JOIN detalle_ordenes_compra d ON d.id_orden_compra = o.id_orden_compra
    WHERE o.estado_registro = 1
      AND (p_id_sede IS NULL OR o.id_sede = p_id_sede)
      AND (p_estado IS NULL OR p_estado = '' OR o.estado = p_estado)
      AND (
          p_search IS NULL OR p_search = ''
          OR o.correlativo ILIKE '%' || p_search || '%'
          OR pr.razon_social ILIKE '%' || p_search || '%'
          OR pr.ruc ILIKE '%' || p_search || '%'
      )
    GROUP BY o.id_orden_compra, pr.razon_social, pr.ruc, pr.telefono, pr.nombre_contacto, s.nombre, u.nombres, u.apellidos
    ORDER BY o.id_orden_compra DESC;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_compra_cabecera(INT);
CREATE OR REPLACE FUNCTION fn_obtener_compra_cabecera(p_id_orden INT)
RETURNS TABLE (
    id_orden_compra INT,
    correlativo VARCHAR,
    id_proveedor INT,
    proveedor_nombre VARCHAR,
    proveedor_ruc VARCHAR,
    proveedor_telefono VARCHAR,
    proveedor_correo VARCHAR,
    proveedor_contacto VARCHAR,
    proveedor_direccion VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    sede_direccion VARCHAR,
    id_usuario INT,
    usuario_nombre VARCHAR,
    fecha_emision TIMESTAMPTZ,
    fecha_esperada VARCHAR,
    fecha_recepcion TIMESTAMPTZ,
    estado VARCHAR,
    total DOUBLE PRECISION,
    observacion TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.id_orden_compra,
        o.correlativo,
        o.id_proveedor,
        pr.razon_social AS proveedor_nombre,
        pr.ruc AS proveedor_ruc,
        pr.telefono AS proveedor_telefono,
        pr.correo AS proveedor_correo,
        pr.nombre_contacto AS proveedor_contacto,
        pr.direccion AS proveedor_direccion,
        o.id_sede,
        s.nombre AS sede_nombre,
        COALESCE(s.direccion, '')::VARCHAR AS sede_direccion,
        o.id_usuario,
        CONCAT(u.nombres, ' ', u.apellidos)::VARCHAR AS usuario_nombre,
        o.fecha_emision,
        o.fecha_esperada,
        o.fecha_recepcion,
        o.estado,
        o.total,
        o.observacion
    FROM ordenes_compra o
    LEFT JOIN proveedores pr ON pr.id_proveedor = o.id_proveedor
    LEFT JOIN sedes s ON s.id_sede = o.id_sede
    LEFT JOIN usuarios u ON u.id_usuario = o.id_usuario
    WHERE o.id_orden_compra = p_id_orden AND o.estado_registro = 1;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_compra_detalle(INT);
CREATE OR REPLACE FUNCTION fn_obtener_compra_detalle(p_id_orden INT)
RETURNS TABLE (
    id_detalle_oc INT,
    id_producto INT,
    codigo_producto VARCHAR,
    nombre_producto VARCHAR,
    cantidad_solicitada INT,
    cantidad_recibida INT,
    precio_unitario DOUBLE PRECISION,
    subtotal DOUBLE PRECISION
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id_detalle_oc,
        d.id_producto,
        p.codigo_producto,
        p.nombre AS nombre_producto,
        d.cantidad_solicitada,
        COALESCE(d.cantidad_recibida, 0),
        d.precio_unitario,
        d.subtotal
    FROM detalle_ordenes_compra d
    LEFT JOIN productos p ON p.id_producto = d.id_producto
    WHERE d.id_orden_compra = p_id_orden;
END;
$$;

-- -----------------------------------------------------------------------------
-- 9. FUNCIONES DE LECTURA (SELECT) - PROVEEDORES
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_listar_proveedores(INT);
CREATE OR REPLACE FUNCTION fn_listar_proveedores(p_id_sede INT DEFAULT NULL)
RETURNS TABLE (
    id_proveedor INT,
    id_sede INT,
    sede_nombre VARCHAR,
    ruc VARCHAR,
    razon_social VARCHAR,
    nombre_contacto VARCHAR,
    telefono VARCHAR,
    correo VARCHAR,
    direccion VARCHAR,
    condiciones_pago VARCHAR,
    total_productos BIGINT,
    total_ordenes BIGINT,
    calificacion_promedio NUMERIC,
    fecha_registro TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.id_proveedor,
        pr.id_sede,
        s.nombre AS sede_nombre,
        pr.ruc,
        pr.razon_social,
        pr.nombre_contacto,
        pr.telefono,
        pr.correo,
        pr.direccion,
        pr.condiciones_pago,
        (SELECT COUNT(*) FROM proveedor_productos pp WHERE pp.id_proveedor = pr.id_proveedor AND pp.estado_registro = 1)::BIGINT,
        (SELECT COUNT(*) FROM ordenes_compra oc WHERE oc.id_proveedor = pr.id_proveedor AND oc.estado_registro = 1)::BIGINT,
        (SELECT ROUND(AVG(calificacion)::numeric, 1) FROM evaluaciones_proveedores ep WHERE ep.id_proveedor = pr.id_proveedor AND ep.estado_registro = 1),
        pr.fecha_registro
    FROM proveedores pr
    LEFT JOIN sedes s ON s.id_sede = pr.id_sede
    WHERE pr.estado_registro = 1
      AND (p_id_sede IS NULL OR pr.id_sede = p_id_sede)
    ORDER BY pr.razon_social ASC;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_proveedor(INT);
CREATE OR REPLACE FUNCTION fn_obtener_proveedor(p_id_proveedor INT)
RETURNS TABLE (
    id_proveedor INT,
    id_sede INT,
    sede_nombre VARCHAR,
    ruc VARCHAR,
    razon_social VARCHAR,
    nombre_contacto VARCHAR,
    telefono VARCHAR,
    correo VARCHAR,
    direccion VARCHAR,
    condiciones_pago VARCHAR,
    total_productos BIGINT,
    total_ordenes BIGINT,
    fecha_registro TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.id_proveedor,
        pr.id_sede,
        COALESCE(s.nombre, 'Sin sede')::VARCHAR AS sede_nombre,
        pr.ruc,
        pr.razon_social,
        pr.nombre_contacto,
        pr.telefono,
        pr.correo,
        pr.direccion,
        pr.condiciones_pago,
        (SELECT COUNT(*) FROM proveedor_productos pp WHERE pp.id_proveedor = pr.id_proveedor AND pp.estado_registro = 1)::BIGINT,
        (SELECT COUNT(*) FROM ordenes_compra oc WHERE oc.id_proveedor = pr.id_proveedor AND oc.estado_registro = 1)::BIGINT,
        pr.fecha_registro
    FROM proveedores pr
    LEFT JOIN sedes s ON s.id_sede = pr.id_sede
    WHERE pr.id_proveedor = p_id_proveedor AND pr.estado_registro = 1;
END;
$$;

DROP FUNCTION IF EXISTS fn_catalogo_proveedor(INT);
CREATE OR REPLACE FUNCTION fn_catalogo_proveedor(p_id_proveedor INT)
RETURNS TABLE (
    id_proveedor_producto INT,
    id_producto INT,
    codigo_producto VARCHAR,
    nombre_producto VARCHAR,
    precio_pactado DOUBLE PRECISION,
    plazo_entrega_dias INT,
    es_principal BOOLEAN
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pp.id_proveedor_producto,
        pp.id_producto,
        p.codigo_producto,
        p.nombre AS nombre_producto,
        COALESCE(pp.precio_compra, 0.0)::DOUBLE PRECISION AS precio_pactado,
        1 AS plazo_entrega_dias,
        FALSE AS es_principal
    FROM proveedor_productos pp
    JOIN productos p ON p.id_producto = pp.id_producto
    WHERE pp.id_proveedor = p_id_proveedor AND pp.estado_registro = 1;
END;
$$;

-- -----------------------------------------------------------------------------
-- 10. FUNCIONES DE LECTURA (SELECT) - CLIENTES, ALMACÉN Y CATEGORÍAS
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_listar_clientes(VARCHAR);
CREATE OR REPLACE FUNCTION fn_listar_clientes(p_search VARCHAR DEFAULT NULL)
RETURNS TABLE (
    id_cliente INT,
    tipo_documento VARCHAR,
    numero_documento VARCHAR,
    nombre VARCHAR,
    telefono VARCHAR,
    fecha_registro TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_cliente,
        c.tipo_documento,
        c.numero_documento,
        c.nombre,
        c.telefono,
        c.fecha_registro
    FROM clientes c
    WHERE c.estado_registro = 1
      AND (
          p_search IS NULL OR p_search = ''
          OR c.numero_documento ILIKE '%' || p_search || '%'
          OR c.nombre ILIKE '%' || p_search || '%'
          OR c.telefono ILIKE '%' || p_search || '%'
      )
    ORDER BY c.id_cliente DESC;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_cliente(INT);
CREATE OR REPLACE FUNCTION fn_obtener_cliente(p_id_cliente INT)
RETURNS TABLE (
    id_cliente INT,
    tipo_documento VARCHAR,
    numero_documento VARCHAR,
    nombre VARCHAR,
    telefono VARCHAR,
    fecha_registro TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_cliente,
        c.tipo_documento,
        c.numero_documento,
        c.nombre,
        c.telefono,
        c.fecha_registro
    FROM clientes c
    WHERE c.id_cliente = p_id_cliente AND c.estado_registro = 1;
END;
$$;

DROP FUNCTION IF EXISTS fn_buscar_cliente(VARCHAR);
CREATE OR REPLACE FUNCTION fn_buscar_cliente(p_criterio VARCHAR)
RETURNS TABLE (
    id_cliente INT,
    tipo_documento VARCHAR,
    numero_documento VARCHAR,
    nombre VARCHAR,
    telefono VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_cliente,
        c.tipo_documento,
        c.numero_documento,
        c.nombre,
        c.telefono
    FROM clientes c
    WHERE c.estado_registro = 1 
      AND (c.numero_documento = p_criterio OR c.nombre ILIKE '%' || p_criterio || '%')
    LIMIT 10;
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_productos_sede(INT);
CREATE OR REPLACE FUNCTION fn_listar_productos_sede(p_id_sede INT)
RETURNS TABLE (
    id_producto INT,
    codigo_producto VARCHAR,
    nombre VARCHAR,
    descripcion VARCHAR,
    precio_venta DOUBLE PRECISION,
    precio_compra DOUBLE PRECISION,
    stock_actual INT,
    stock_minimo INT,
    categoria VARCHAR,
    id_categoria INT,
    id_subcategoria INT,
    sede_id INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id_producto,
        p.codigo_producto,
        p.nombre,
        p.descripcion,
        COALESCE(i.precio_venta, 0.0),
        COALESCE(i.precio_compra, 0.0),
        COALESCE(i.stock_actual, 0),
        COALESCE(i.stock_minimo, 0),
        COALESCE(c.nombre, 'Sin categoría'),
        p.id_categoria,
        p.id_subcategoria,
        p_id_sede
    FROM productos p
    LEFT JOIN categorias c ON c.id_categoria = p.id_categoria
    LEFT JOIN inventario_sedes i ON i.id_producto = p.id_producto AND i.id_sede = p_id_sede
    WHERE p.estado_registro = 1
    ORDER BY p.nombre ASC;
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_categorias();
CREATE OR REPLACE FUNCTION fn_listar_categorias()
RETURNS TABLE (
    id_categoria INT,
    nombre VARCHAR,
    descripcion VARCHAR,
    id_padre INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT c.id_categoria, c.nombre, c.descripcion, c.id_padre
    FROM categorias c
    WHERE c.estado_registro = 1
    ORDER BY c.nombre ASC;
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_subcategorias(INT);
CREATE OR REPLACE FUNCTION fn_listar_subcategorias(p_id_categoria INT DEFAULT NULL)
RETURNS TABLE (
    id_subcategoria INT,
    nombre VARCHAR,
    descripcion VARCHAR,
    id_categoria INT,
    categoria_nombre VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id_subcategoria,
        s.nombre,
        s.descripcion,
        s.id_categoria,
        COALESCE(c.nombre, 'General')::VARCHAR AS categoria_nombre
    FROM subcategorias s
    LEFT JOIN categorias c ON c.id_categoria = s.id_categoria
    WHERE s.estado_registro = 1
      AND (p_id_categoria IS NULL OR s.id_categoria = p_id_categoria)
    ORDER BY s.nombre ASC;
END;
$$;

-- -----------------------------------------------------------------------------
-- 11. FUNCIONES Y PROCEDIMIENTOS - AUTENTICACIÓN Y USUARIOS
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_autenticar_usuario(VARCHAR);
CREATE OR REPLACE FUNCTION fn_autenticar_usuario(p_username VARCHAR)
RETURNS TABLE (
    id_usuario INT,
    nombre_usuario VARCHAR,
    clave VARCHAR,
    nombres VARCHAR,
    apellidos VARCHAR,
    dni VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    estado_registro INT,
    roles TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_usuario,
        u.nombre_usuario,
        u.clave,
        u.nombres,
        u.apellidos,
        u.dni,
        u.id_sede,
        COALESCE(s.nombre, 'Sede Central')::VARCHAR AS sede_nombre,
        u.estado_registro,
        ARRAY(
            SELECT p.nombre 
            FROM usuario_perfiles up 
            JOIN perfiles p ON p.id_perfil = up.id_perfil 
            WHERE up.id_usuario = u.id_usuario AND up.estado_registro = 1
        )::TEXT[] AS roles
    FROM usuarios u
    LEFT JOIN sedes s ON s.id_sede = u.id_sede
    WHERE (LOWER(u.nombre_usuario) = LOWER(p_username) OR LOWER(u.correo_electronico) = LOWER(p_username) OR u.dni = p_username)
      AND u.estado_registro = 1;
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_usuarios();
CREATE OR REPLACE FUNCTION fn_listar_usuarios()
RETURNS TABLE (
    id_usuario INT,
    nombre_usuario VARCHAR,
    nombres VARCHAR,
    apellidos VARCHAR,
    correo_electronico VARCHAR,
    celular VARCHAR,
    dni VARCHAR,
    genero VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    ultimo_acceso VARCHAR,
    estado_registro INT,
    roles TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_usuario,
        u.nombre_usuario,
        u.nombres,
        u.apellidos,
        u.correo_electronico,
        u.celular,
        u.dni,
        u.genero,
        u.id_sede,
        COALESCE(s.nombre, 'Sede Central')::VARCHAR AS sede_nombre,
        u.ultimo_acceso,
        u.estado_registro,
        ARRAY(
            SELECT p.nombre 
            FROM usuario_perfiles up 
            JOIN perfiles p ON p.id_perfil = up.id_perfil 
            WHERE up.id_usuario = u.id_usuario AND up.estado_registro = 1
        )::TEXT[] AS roles
    FROM usuarios u
    LEFT JOIN sedes s ON s.id_sede = u.id_sede
    WHERE u.estado_registro = 1
    ORDER BY u.id_usuario ASC;
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_sedes();
CREATE OR REPLACE FUNCTION fn_listar_sedes()
RETURNS TABLE (
    id_sede INT,
    nombre VARCHAR,
    direccion VARCHAR,
    telefono VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT s.id_sede, s.nombre, s.direccion, s.telefono
    FROM sedes s
    WHERE s.estado_registro = 1
    ORDER BY s.id_sede ASC;
END;
$$;

-- -----------------------------------------------------------------------------
-- 12. USUARIOS: sp_guardar_usuario y sp_eliminar_usuario
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_guardar_usuario;
CREATE OR REPLACE PROCEDURE sp_guardar_usuario(
    p_id_usuario INT,
    p_nombres VARCHAR,
    p_apellidos VARCHAR,
    p_username VARCHAR,
    p_email VARCHAR,
    p_phone VARCHAR,
    p_dni VARCHAR,
    p_gender VARCHAR,
    p_id_sede INT,
    p_roles TEXT[],
    INOUT o_id_usuario INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_role_name TEXT;
    v_id_perfil INT;
BEGIN
    IF p_id_usuario IS NOT NULL AND p_id_usuario > 0 THEN
        UPDATE usuarios
        SET nombres = COALESCE(p_nombres, nombres),
            apellidos = COALESCE(p_apellidos, apellidos),
            nombre_usuario = COALESCE(p_username, nombre_usuario),
            correo_electronico = COALESCE(p_email, correo_electronico),
            celular = COALESCE(p_phone, celular),
            dni = COALESCE(p_dni, dni),
            genero = COALESCE(p_gender, genero),
            id_sede = COALESCE(p_id_sede, id_sede)
        WHERE id_usuario = p_id_usuario;

        o_id_usuario := p_id_usuario;

        IF p_roles IS NOT NULL AND array_length(p_roles, 1) > 0 THEN
            DELETE FROM usuario_perfiles WHERE id_usuario = p_id_usuario;
            FOREACH v_role_name IN ARRAY p_roles
            LOOP
                SELECT id_perfil INTO v_id_perfil FROM perfiles WHERE LOWER(nombre) = LOWER(v_role_name);
                IF v_id_perfil IS NOT NULL THEN
                    INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro)
                    VALUES (p_id_usuario, v_id_perfil, 1)
                    ON CONFLICT DO NOTHING;
                END IF;
            END LOOP;
        END IF;

        o_mensaje := 'Usuario actualizado exitosamente';
    ELSE
        INSERT INTO usuarios (
            nombres, apellidos, nombre_usuario, correo_electronico,
            celular, dni, genero, id_sede, clave, estado_registro
        ) VALUES (
            p_nombres, p_apellidos, p_username, p_email,
            p_phone, p_dni, p_gender, COALESCE(p_id_sede, 1), 'admin1234', 1
        ) RETURNING id_usuario INTO o_id_usuario;

        IF p_roles IS NOT NULL AND array_length(p_roles, 1) > 0 THEN
            FOREACH v_role_name IN ARRAY p_roles
            LOOP
                SELECT id_perfil INTO v_id_perfil FROM perfiles WHERE LOWER(nombre) = LOWER(v_role_name);
                IF v_id_perfil IS NOT NULL THEN
                    INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro)
                    VALUES (o_id_usuario, v_id_perfil, 1)
                    ON CONFLICT DO NOTHING;
                END IF;
            END LOOP;
        ELSE
            SELECT id_perfil INTO v_id_perfil FROM perfiles WHERE LOWER(nombre) = 'vendedor';
            IF v_id_perfil IS NOT NULL THEN
                INSERT INTO usuario_perfiles (id_usuario, id_perfil, estado_registro)
                VALUES (o_id_usuario, v_id_perfil, 1);
            END IF;
        END IF;

        o_mensaje := 'Usuario registrado exitosamente';
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS sp_eliminar_usuario;
CREATE OR REPLACE PROCEDURE sp_eliminar_usuario(
    p_id_usuario INT,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE usuarios SET estado_registro = 0 WHERE id_usuario = p_id_usuario;
    o_mensaje := 'Usuario desactivado exitosamente';
END;
$$;

-- -----------------------------------------------------------------------------
-- 13. PROFORMAS
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_procesar_proforma;
CREATE OR REPLACE PROCEDURE sp_procesar_proforma(
    p_id_usuario INT,
    p_id_sede INT,
    p_cliente_nombre VARCHAR,
    p_cliente_doc VARCHAR,
    p_validez_dias INT,
    p_total DOUBLE PRECISION,
    p_detalles JSONB,
    INOUT o_id_proforma INT DEFAULT NULL,
    INOUT o_correlativo VARCHAR DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_item JSONB;
    v_id_cliente INT;
    v_tipo_doc VARCHAR;
BEGIN
    o_correlativo := CONCAT('P-', TO_CHAR(NOW(), 'YYYYMMDDHH24MISS'));

    IF p_cliente_doc IS NOT NULL AND p_cliente_doc <> '' THEN
        v_tipo_doc := CASE WHEN LENGTH(p_cliente_doc) = 11 THEN 'RUC' ELSE 'DNI' END;
        CALL sp_guardar_cliente(NULL, v_tipo_doc, p_cliente_doc, p_cliente_nombre, '', v_id_cliente, o_mensaje);
    END IF;

    INSERT INTO proformas (
        correlativo, cliente_nombre, cliente_doc, id_cliente,
        validez_dias, total, id_usuario, id_sede, fecha_emision, estado_registro
    ) VALUES (
        o_correlativo, COALESCE(p_cliente_nombre, 'Cliente General'), COALESCE(p_cliente_doc, ''), v_id_cliente,
        COALESCE(p_validez_dias, 7), p_total, p_id_usuario, p_id_sede, NOW(), 1
    ) RETURNING id_proforma INTO o_id_proforma;

    FOR v_item IN SELECT * FROM jsonb_array_elements(p_detalles)
    LOOP
        INSERT INTO detalle_proformas (
            id_proforma, id_producto, cantidad, precio_unitario, subtotal
        ) VALUES (
            o_id_proforma,
            (v_item->>'id_producto')::INT,
            (v_item->>'cantidad')::INT,
            (v_item->>'precio_unitario')::DOUBLE PRECISION,
            (v_item->>'subtotal')::DOUBLE PRECISION
        );
    END LOOP;

    o_mensaje := 'Proforma registrada con éxito';
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_proformas(INT, VARCHAR);
CREATE OR REPLACE FUNCTION fn_listar_proformas(p_id_sede INT DEFAULT NULL, p_search VARCHAR DEFAULT NULL)
RETURNS TABLE (
    id_proforma INT,
    correlativo VARCHAR,
    fecha_emision TIMESTAMP WITH TIME ZONE,
    validez_dias INT,
    cliente_nombre VARCHAR,
    cliente_doc VARCHAR,
    total DOUBLE PRECISION,
    id_usuario INT,
    usuario_nombre VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    id_cliente INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.id_proforma,
        pr.correlativo,
        pr.fecha_emision,
        pr.validez_dias,
        pr.cliente_nombre,
        pr.cliente_doc,
        pr.total,
        pr.id_usuario,
        CONCAT(u.nombres, ' ', u.apellidos)::VARCHAR AS usuario_nombre,
        pr.id_sede,
        s.nombre AS sede_nombre,
        pr.id_cliente
    FROM proformas pr
    LEFT JOIN usuarios u ON u.id_usuario = pr.id_usuario
    LEFT JOIN sedes s ON s.id_sede = pr.id_sede
    WHERE pr.estado_registro = 1
      AND (p_id_sede IS NULL OR pr.id_sede = p_id_sede)
      AND (
          p_search IS NULL OR p_search = ''
          OR pr.correlativo ILIKE '%' || p_search || '%'
          OR pr.cliente_nombre ILIKE '%' || p_search || '%'
          OR pr.cliente_doc ILIKE '%' || p_search || '%'
      )
    ORDER BY pr.id_proforma DESC;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_proforma_cabecera(INT);
CREATE OR REPLACE FUNCTION fn_obtener_proforma_cabecera(p_id_proforma INT)
RETURNS TABLE (
    id_proforma INT,
    correlativo VARCHAR,
    fecha_emision TIMESTAMP WITH TIME ZONE,
    validez_dias INT,
    cliente_nombre VARCHAR,
    cliente_doc VARCHAR,
    total DOUBLE PRECISION,
    id_usuario INT,
    usuario_nombre VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    sede_direccion VARCHAR,
    id_cliente INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.id_proforma,
        pr.correlativo,
        pr.fecha_emision,
        pr.validez_dias,
        pr.cliente_nombre,
        pr.cliente_doc,
        pr.total,
        pr.id_usuario,
        CONCAT(u.nombres, ' ', u.apellidos)::VARCHAR AS usuario_nombre,
        pr.id_sede,
        s.nombre AS sede_nombre,
        COALESCE(s.direccion, '')::VARCHAR AS sede_direccion,
        pr.id_cliente
    FROM proformas pr
    LEFT JOIN usuarios u ON u.id_usuario = pr.id_usuario
    LEFT JOIN sedes s ON s.id_sede = pr.id_sede
    WHERE pr.id_proforma = p_id_proforma AND pr.estado_registro = 1;
END;
$$;

DROP FUNCTION IF EXISTS fn_obtener_proforma_detalle(INT);
CREATE OR REPLACE FUNCTION fn_obtener_proforma_detalle(p_id_proforma INT)
RETURNS TABLE (
    id_detalle_proforma INT,
    id_producto INT,
    codigo_producto VARCHAR,
    nombre_producto VARCHAR,
    cantidad INT,
    precio_unitario DOUBLE PRECISION,
    subtotal DOUBLE PRECISION
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dp.id_detalle_proforma,
        dp.id_producto,
        p.codigo_producto,
        p.nombre AS nombre_producto,
        dp.cantidad,
        dp.precio_unitario,
        dp.subtotal
    FROM detalle_proformas dp
    JOIN productos p ON p.id_producto = dp.id_producto
    WHERE dp.id_proforma = p_id_proforma;
END;
$$;

-- -----------------------------------------------------------------------------
-- 14. PROMOCIONES
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_listar_promociones(INT);
CREATE OR REPLACE FUNCTION fn_listar_promociones(p_id_sede INT DEFAULT NULL)
RETURNS TABLE (
    id_promocion INT,
    nombre VARCHAR,
    tipo_descuento VARCHAR,
    valor DOUBLE PRECISION,
    aplica_a VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    id_categoria INT,
    categoria_nombre VARCHAR,
    id_producto INT,
    producto_nombre VARCHAR,
    fecha_inicio VARCHAR,
    fecha_fin VARCHAR,
    estado_registro INT,
    creador VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pm.id_promocion,
        pm.nombre,
        pm.tipo_descuento,
        pm.valor,
        pm.aplica_a,
        pm.id_sede,
        COALESCE(s.nombre, 'Todas las Sedes')::VARCHAR AS sede_nombre,
        pm.id_categoria,
        c.nombre AS categoria_nombre,
        pm.id_producto,
        p.nombre AS producto_nombre,
        pm.fecha_inicio,
        pm.fecha_fin,
        pm.estado_registro,
        COALESCE(u.nombre_usuario, 'Sistema')::VARCHAR AS creador
    FROM promociones pm
    LEFT JOIN sedes s ON s.id_sede = pm.id_sede
    LEFT JOIN categorias c ON c.id_categoria = pm.id_categoria
    LEFT JOIN productos p ON p.id_producto = pm.id_producto
    LEFT JOIN usuarios u ON u.id_usuario = pm.id_usuario_creador
    WHERE pm.estado_registro = 1
      AND (p_id_sede IS NULL OR pm.id_sede IS NULL OR pm.id_sede = p_id_sede)
    ORDER BY pm.id_promocion DESC;
END;
$$;

DROP FUNCTION IF EXISTS fn_listar_promociones_activas(INT, VARCHAR);
CREATE OR REPLACE FUNCTION fn_listar_promociones_activas(p_id_sede INT, p_fecha VARCHAR)
RETURNS TABLE (
    id_promocion INT,
    nombre VARCHAR,
    tipo_descuento VARCHAR,
    valor DOUBLE PRECISION,
    aplica_a VARCHAR,
    id_sede INT,
    sede_nombre VARCHAR,
    id_categoria INT,
    categoria_nombre VARCHAR,
    id_producto INT,
    producto_nombre VARCHAR,
    fecha_inicio VARCHAR,
    fecha_fin VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pm.id_promocion,
        pm.nombre,
        pm.tipo_descuento,
        pm.valor,
        pm.aplica_a,
        pm.id_sede,
        COALESCE(s.nombre, 'Todas las Sedes')::VARCHAR AS sede_nombre,
        pm.id_categoria,
        c.nombre AS categoria_nombre,
        pm.id_producto,
        p.nombre AS producto_nombre,
        pm.fecha_inicio,
        pm.fecha_fin
    FROM promociones pm
    LEFT JOIN sedes s ON s.id_sede = pm.id_sede
    LEFT JOIN categorias c ON c.id_categoria = pm.id_categoria
    LEFT JOIN productos p ON p.id_producto = pm.id_producto
    WHERE pm.estado_registro = 1
      AND pm.fecha_inicio <= p_fecha
      AND pm.fecha_fin >= p_fecha
      AND (pm.id_sede IS NULL OR pm.id_sede = p_id_sede);
END;
$$;

DROP PROCEDURE IF EXISTS sp_guardar_promocion;
CREATE OR REPLACE PROCEDURE sp_guardar_promocion(
    p_nombre VARCHAR,
    p_tipo_descuento VARCHAR,
    p_valor DOUBLE PRECISION,
    p_aplica_a VARCHAR,
    p_id_sede INT,
    p_id_categoria INT,
    p_id_producto INT,
    p_fecha_inicio VARCHAR,
    p_fecha_fin VARCHAR,
    p_id_usuario INT,
    INOUT o_id_promocion INT DEFAULT NULL,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO promociones (
        nombre, tipo_descuento, valor, aplica_a, id_sede,
        id_categoria, id_producto, fecha_inicio, fecha_fin,
        id_usuario_creador, fecha_creacion, estado_registro
    ) VALUES (
        p_nombre, COALESCE(p_tipo_descuento, 'PORCENTAJE'), p_valor, COALESCE(p_aplica_a, 'TODOS'),
        p_id_sede, p_id_categoria, p_id_producto, p_fecha_inicio, p_fecha_fin,
        p_id_usuario, NOW(), 1
    ) RETURNING id_promocion INTO o_id_promocion;

    o_mensaje := 'Promoción creada exitosamente';
END;
$$;

DROP PROCEDURE IF EXISTS sp_eliminar_promocion;
CREATE OR REPLACE PROCEDURE sp_eliminar_promocion(
    p_id_promocion INT,
    INOUT o_mensaje VARCHAR DEFAULT 'OK'
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE promociones SET estado_registro = 0 WHERE id_promocion = p_id_promocion;
    o_mensaje := 'Promoción eliminada exitosamente';
END;
$$;

-- -----------------------------------------------------------------------------
-- 15. CORRELATIVOS: fn_siguiente_codigo_producto y fn_siguiente_correlativo_oc
-- -----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_siguiente_codigo_producto();
CREATE OR REPLACE FUNCTION fn_siguiente_codigo_producto()
RETURNS VARCHAR
LANGUAGE plpgsql
AS $$
DECLARE
    v_ultimo VARCHAR;
    v_num INT := 1;
    v_cod VARCHAR;
BEGIN
    SELECT codigo_producto INTO v_ultimo 
    FROM productos 
    WHERE codigo_producto LIKE 'PROD-%' 
    ORDER BY id_producto DESC 
    LIMIT 1;

    IF v_ultimo IS NOT NULL THEN
        BEGIN
            v_num := SUBSTRING(v_ultimo FROM 6)::INT + 1;
        EXCEPTION WHEN OTHERS THEN
            SELECT COALESCE(MAX(id_producto), 0) + 1 INTO v_num FROM productos;
        END;
    ELSE
        SELECT COALESCE(MAX(id_producto), 0) + 1 INTO v_num FROM productos;
    END IF;

    v_cod := CONCAT('PROD-', LPAD(v_num::TEXT, 5, '0'));
    WHILE EXISTS (SELECT 1 FROM productos WHERE codigo_producto = v_cod) LOOP
        v_num := v_num + 1;
        v_cod := CONCAT('PROD-', LPAD(v_num::TEXT, 5, '0'));
    END LOOP;

    RETURN v_cod;
END;
$$;

DROP FUNCTION IF EXISTS fn_siguiente_correlativo_oc();
CREATE OR REPLACE FUNCTION fn_siguiente_correlativo_oc()
RETURNS VARCHAR
LANGUAGE plpgsql
AS $$
DECLARE
    v_year TEXT := TO_CHAR(NOW(), 'YYYY');
    v_prefix TEXT;
    v_ultimo VARCHAR;
    v_num INT := 1;
    v_correlativo VARCHAR;
BEGIN
    v_prefix := CONCAT('OC-', v_year, '-');
    SELECT correlativo INTO v_ultimo 
    FROM ordenes_compra 
    WHERE correlativo LIKE v_prefix || '%' 
    ORDER BY id_orden_compra DESC 
    LIMIT 1;

    IF v_ultimo IS NOT NULL THEN
        BEGIN
            v_num := SUBSTRING(v_ultimo FROM LENGTH(v_prefix) + 1)::INT + 1;
        EXCEPTION WHEN OTHERS THEN
            v_num := 1;
        END;
    ELSE
        v_num := 1;
    END IF;

    v_correlativo := CONCAT(v_prefix, LPAD(v_num::TEXT, 4, '0'));
    WHILE EXISTS (SELECT 1 FROM ordenes_compra WHERE correlativo = v_correlativo) LOOP
        v_num := v_num + 1;
        v_correlativo := CONCAT(v_prefix, LPAD(v_num::TEXT, 4, '0'));
    END LOOP;

    RETURN v_correlativo;
END;
$$;






-- -----------------------------------------------------------------------------
-- 13. RESTRICCIONES DE INTEGRIDAD REFERENCIAL (FOREIGN KEYS)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_ventas_cliente') THEN
        ALTER TABLE ventas ADD CONSTRAINT fk_ventas_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_proformas_cliente') THEN
        ALTER TABLE proformas ADD CONSTRAINT fk_proformas_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE SET NULL;
    END IF;
END $$;
