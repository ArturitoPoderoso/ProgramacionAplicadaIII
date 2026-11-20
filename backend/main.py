import os
import gzip
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import text
from database import engine, teardown_db
import models

# Importar Blueprints modulares
from routes import (
    auth_bp,
    users_bp,
    almacen_bp,
    ventas_bp,
    proformas_bp,
    promociones_bp,
    proveedores_bp,
    compras_bp,
    clientes_bp
)

# Creamos las tablas o columnas faltantes si no existen
try:
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS descuento_total DOUBLE PRECISION DEFAULT 0.0;"))
        conn.execute(text("ALTER TABLE detalle_ventas ADD COLUMN IF NOT EXISTS descuento_unitario DOUBLE PRECISION DEFAULT 0.0;"))
        conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS id_cliente INTEGER;"))
        conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS cliente_nombre VARCHAR(150) DEFAULT 'Cliente General';"))
        conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS cliente_doc VARCHAR(30) DEFAULT '';"))
        conn.execute(text("ALTER TABLE proformas ADD COLUMN IF NOT EXISTS id_cliente INTEGER;"))
        conn.execute(text("ALTER TABLE clientes DROP COLUMN IF EXISTS correo;"))
        conn.execute(text("ALTER TABLE clientes DROP COLUMN IF EXISTS direccion;"))
        conn.commit()
except Exception as e:
    print(f"Error conectando o sincronizando BD: {e}")

# Configuracion de Flask y CORS
app = Flask(__name__)
CORS(app)

# Comprime respuestas grandes con gzip para que cargue mas rapido
@app.after_request
def compress_response(response):
    try:
        accept_encoding = request.headers.get("Accept-Encoding", "").lower()
        if (
            response.status_code < 300
            and "gzip" in accept_encoding
            and "Content-Encoding" not in response.headers
            and not response.direct_passthrough
        ):
            content_type = response.headers.get("Content-Type", "")
            if any(t in content_type for t in ["application/json", "text/html", "text/css", "application/javascript"]):
                data = response.get_data()
                if len(data) > 512:
                    compressed_data = gzip.compress(data, compresslevel=6)
                    response.set_data(compressed_data)
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = len(compressed_data)
    except Exception:
        pass
    return response

# Cierra la conexion a la BD al terminar cada request
app.teardown_appcontext(teardown_db)

# Manejo de errores 500 y 404 en formato JSON
@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Error interno del servidor", "status": 500}), 500

@app.errorhandler(404)
def not_found_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint de API no encontrado", "status": 404}), 404
    return jsonify({"error": "Recurso no encontrado"}), 404

# Registro de las rutas modulares
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(almacen_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(proformas_bp)
app.register_blueprint(promociones_bp)
app.register_blueprint(proveedores_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(clientes_bp)

# Servir los archivos estaticos del frontend solo en desarrollo local si existe la carpeta
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.route("/")
def read_root():
    return jsonify({
        "message": "Bienvenido a la API del Sistema Jesmi",
        "status": "online",
        "version": "2.0.0",
        "api_docs": {
            "clientes": "/api/clientes",
            "buscar_cliente": "/api/clientes/buscar/<doc>"
        }
    })

@app.route("/<path:path>")
def serve_fallback(path):
    if not path.startswith("api/"):
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.exists(file_path):
            return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": "Recurso no encontrado"}), 404

# Iniciar servidor con Waitress en el puerto 8000
if __name__ == "__main__":
    try:
        from waitress import serve
        print("[OK] Servidor backend corriendo en http://localhost:8000")
        serve(app, host="0.0.0.0", port=8000, threads=8)
    except ImportError:
        app.run(port=8000, debug=True)
