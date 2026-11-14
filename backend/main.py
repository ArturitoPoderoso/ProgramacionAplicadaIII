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
    compras_bp
)

# 1. Verificación y sincronización de base de datos
try:
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS descuento_total DOUBLE PRECISION DEFAULT 0.0;"))
        conn.execute(text("ALTER TABLE detalle_ventas ADD COLUMN IF NOT EXISTS descuento_unitario DOUBLE PRECISION DEFAULT 0.0;"))
        conn.commit()
except Exception as e:
    print(f"Error conectando o sincronizando BD: {e}")

# 2. Inicialización de la aplicación Flask
app = Flask(__name__)
CORS(app)

# 3. Middleware de compresión GZIP de alto rendimiento (Escalamiento de tráfico y ancho de banda)
@app.after_request
def compress_response(response):
    """Comprime automáticamente respuestas > 512 bytes si el cliente soporta GZIP"""
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

# 4. Gestión del ciclo de vida de la conexión a la base de datos
app.teardown_appcontext(teardown_db)

# 5. Manejadores globales de errores centralizados
@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Error interno del servidor", "status": 500}), 500

@app.errorhandler(404)
def not_found_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint de API no encontrado", "status": 404}), 404
    return jsonify({"error": "Recurso no encontrado"}), 404

# 6. Registro de Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(almacen_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(proformas_bp)
app.register_blueprint(promociones_bp)
app.register_blueprint(proveedores_bp)
app.register_blueprint(compras_bp)

# 7. Ruta base y servicio de archivos frontend para desarrollo local
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.route("/")
def read_root():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({
        "message": "Bienvenido a la API del Sistema Jesmi",
        "status": "online",
        "version": "2.0.0"
    })

@app.route("/<path:path>")
def serve_frontend(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": "Recurso no encontrado"}), 404

# 8. Arranque del servidor con Waitress (Multi-hilo)
if __name__ == "__main__":
    try:
        from waitress import serve
        print("[OK] Servidor backend escalado y optimizado arrancado en http://localhost:8000 (8 hilos)...")
        serve(app, host="0.0.0.0", port=8000, threads=8)
    except ImportError:
        app.run(port=8000, debug=True)
