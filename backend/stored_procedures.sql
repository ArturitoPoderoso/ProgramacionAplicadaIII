-- =============================================================================
-- PROCEDIMIENTOS ALMACENADOS Y FUNCIONES PL/pgSQL - SISTEMA JESMI
-- Tablas: productos, inventario_sedes, ventas, detalle_ventas, 
--         movimientos_almacen, clientes, ordenes_compra, detalle_ordenes_compra, proveedores
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. VENTAS: sp_procesar_venta
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

-- -----------------------------------------------------------------------------
-- 2. VENTAS: sp_anular_venta
-- -----------------------------------------------------------------------------
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
-- 3. CLIENTES: sp_guardar_cliente y sp_eliminar_cliente
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
        -- Validación de colisión de documento con otro cliente
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
        -- Buscar si ya existe por documento
        SELECT id_cliente, estado_registro, nombre INTO v_existente
        FROM clientes
        WHERE numero_documento = p_numero_documento;

        IF FOUND THEN
            IF v_existente.estado_registro = 1 THEN
                RAISE EXCEPTION 'El documento % ya está registrado a nombre de "%".', p_numero_documento, v_existente.nombre;
            ELSE
                -- Reactivar cliente previamente eliminado
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
            -- Insertar nuevo cliente
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
-- 4. ALMACÉN: sp_guardar_producto
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
    v_inv RECORD;
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
        -- Validar si existe por código
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

        -- Inicializar inventario en todas las sedes
        FOR v_sede IN SELECT id_sede FROM sedes
        LOOP
            INSERT INTO inventario_sedes (
                id_producto, id_sede, stock_actual, stock_minimo, precio_compra, precio_venta, estado_registro
            ) VALUES (
                o_id_producto, v_sede.id_sede, 0, COALESCE(p_stock_minimo, 5), COALESCE(p_precio_compra, 0.0), COALESCE(p_precio_venta, 0.0), 1
            ) ON CONFLICT DO NOTHING;
        END LOOP;

        -- En la sede especificada, actualizar stock y precios
        IF p_id_sede IS NOT NULL THEN
            UPDATE inventario_sedes
            SET stock_actual = COALESCE(p_stock_actual, 0),
                precio_compra = COALESCE(p_precio_compra, 0.0),
                precio_venta = COALESCE(p_precio_venta, 0.0),
                stock_minimo = COALESCE(p_stock_minimo, 5)
            WHERE id_producto = o_id_producto AND id_sede = p_id_sede;

            -- Si hay stock inicial mayor a 0, registrar en Kardex
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
-- 5. COMPRAS: sp_procesar_compra, sp_recibir_compra y sp_anular_compra
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

    -- Insertar cabecera de orden de compra en estado PENDIENTE
    INSERT INTO ordenes_compra (
        correlativo, id_proveedor, id_sede, id_usuario,
        fecha_emision, fecha_esperada, estado, total, observacion, estado_registro
    ) VALUES (
        p_correlativo, p_id_proveedor, p_id_sede, p_id_usuario,
        NOW(), p_fecha_esperada, 'PENDIENTE', p_total, p_observacion, 1
    ) RETURNING id_orden_compra INTO o_id_compra;

    -- Insertar detalles de la orden
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

    -- Incrementar stock en almacén, registrar Kardex y actualizar detalle
    FOR v_det IN SELECT * FROM detalle_ordenes_compra WHERE id_orden_compra = p_id_orden
    LOOP
        UPDATE detalle_ordenes_compra
        SET cantidad_recibida = v_det.cantidad_solicitada
        WHERE id_detalle_oc = v_det.id_detalle_oc;

        -- Actualizar o inicializar inventario en la sede de la orden
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

    -- Si estaba RECIBIDA, validar que haya stock suficiente para revertir
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

        -- Descontar stock y registrar salida en Kardex
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
-- 6. PROVEEDORES: sp_guardar_proveedor y sp_eliminar_proveedor
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
        -- Validar colisión de RUC en la misma sede
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
        -- Buscar si ya existe por RUC y Sede
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
-- 7. FUNCIONES DE LECTURA (SELECT)
-- -----------------------------------------------------------------------------

-- Productos por Sede
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

-- Búsqueda de cliente
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
