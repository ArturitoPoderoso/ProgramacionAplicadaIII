import os
import json
import urllib.request
import urllib.error
from datetime import datetime

SUNAT_API_URL = os.getenv("SUNAT_API_URL", "https://jesmi-facturacion-sunat.onrender.com").rstrip("/")
SUNAT_API_TOKEN = os.getenv("SUNAT_API_TOKEN", "1|sunat_SUivPi7dYAtEO2rHO8WUOJwyGsqKg3ueY13aYwru4a64dff3")

def emitir_comprobante_sunat(venta_data):
    """
    Envía una venta procesada al microservicio SUNAT Facturación.
    Genera Boleta (B001) o Factura (F001) y la envía a SUNAT.
    """
    try:
        cliente_doc = str(venta_data.get("cliente_doc") or "").strip()
        cliente_nombre = str(venta_data.get("cliente_nombre") or "Cliente General").strip()
        cliente_tel = str(venta_data.get("cliente_telefono") or "").strip()
        detalles = venta_data.get("detalles", [])
        
        # Determinar tipo de comprobante: Si tiene RUC (11 dígitos) es Factura, sino Boleta
        es_factura = len(cliente_doc) == 11
        tipo_cpe = "01" if es_factura else "03"
        serie = "F001" if es_factura else "B001"
        endpoint_store = "/api/v1/invoices" if es_factura else "/api/v1/boletas"
        
        # Tipo documento cliente: 6=RUC, 1=DNI, 0=Sin documento
        if len(cliente_doc) == 11:
            tipo_doc_cli = "6"
        elif len(cliente_doc) == 8:
            tipo_doc_cli = "1"
        else:
            tipo_doc_cli = "0"
            cliente_doc = "00000000" if not cliente_doc else cliente_doc

        items_cpe = []
        for det in detalles:
            # Los precios en el sistema Jesmi son precios finales de venta
            # Para SUNAT calculamos el valor unitario sin IGV (P / 1.18)
            precio_final = float(det.get("precio_unitario", 0.0)) - float(det.get("descuento_unitario", 0.0))
            valor_unitario = round(precio_final / 1.18, 2)
            cantidad = float(det.get("cantidad", 1))
            
            items_cpe.append({
                "codigo": f"PROD-{det.get('id_producto', 1)}",
                "descripcion": str(det.get("nombre") or det.get("descripcion") or f"Producto {det.get('id_producto')}").strip(),
                "unidad": "NIU",
                "cantidad": cantidad,
                "mto_valor_unitario": valor_unitario,
                "porcentaje_igv": 18,
                "tip_afe_igv": "10"
            })

        payload = {
            "company_id": 1,
            "branch_id": 1,
            "serie": serie,
            "fecha_emision": datetime.now().strftime("%Y-%m-%d"),
            "metodo_envio": "individual",
            "forma_pago_tipo": venta_data.get("metodo_pago", "Contado"),
            "client": {
                "tipo_documento": tipo_doc_cli,
                "numero_documento": cliente_doc,
                "razon_social": cliente_nombre,
                "direccion": "AV. PRINCIPAL 123",
                "telefono": cliente_tel
            },
            "detalles": items_cpe
        }

        # 1. Crear documento en la API
        req_store = urllib.request.Request(
            f"{SUNAT_API_URL}{endpoint_store}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {SUNAT_API_TOKEN}"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req_store, timeout=12) as resp_store:
            res_json = json.loads(resp_store.read().decode("utf-8"))
            cpe_data = res_json.get("data", {})
            cpe_id = cpe_data.get("id")
            num_completo = cpe_data.get("numero_completo") or f"{serie}-000000"

        # 2. Enviar a SUNAT para obtener firma, Hash y estado
        try:
            req_send = urllib.request.Request(
                f"{SUNAT_API_URL}{endpoint_store}/{cpe_id}/send-sunat",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {SUNAT_API_TOKEN}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req_send, timeout=15) as resp_send:
                res_send_json = json.loads(resp_send.read().decode("utf-8"))
                send_data = res_send_json.get("data", {})
                
                return {
                    "success": True,
                    "cpe_id": cpe_id,
                    "tipo_comprobante": "FACTURA ELECTRÓNICA" if es_factura else "BOLETA ELECTRÓNICA",
                    "serie_numero": send_data.get("numero_completo") or num_completo,
                    "estado_sunat": send_data.get("estado_sunat") or "ACEPTADO",
                    "codigo_hash": send_data.get("codigo_hash"),
                    "xml_path": send_data.get("xml_path"),
                    "cdr_path": send_data.get("cdr_path")
                }
        except Exception as e_send:
            # Si el envío a SUNAT tarda o falla, el comprobante ya quedó creado en la API
            return {
                "success": True,
                "cpe_id": cpe_id,
                "tipo_comprobante": "FACTURA ELECTRÓNICA" if es_factura else "BOLETA ELECTRÓNICA",
                "serie_numero": num_completo,
                "estado_sunat": "PENDIENTE_ENVIO",
                "codigo_hash": None,
                "error_sunat": str(e_send)
            }

    except Exception as e:
        print(f"[SUNAT Service Error]: {e}")
        return {
            "success": False,
            "error": str(e)
        }
