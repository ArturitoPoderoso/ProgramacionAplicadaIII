"""
Módulo de rutas y Blueprints del Sistema Jesmi
"""
from .auth import auth_bp
from .users import users_bp
from .almacen import almacen_bp
from .ventas import ventas_bp
from .proformas import proformas_bp
from .promociones import promociones_bp
from .proveedores import proveedores_bp
from .compras import compras_bp

__all__ = [
    "auth_bp",
    "users_bp",
    "almacen_bp",
    "ventas_bp",
    "proformas_bp",
    "promociones_bp",
    "proveedores_bp",
    "compras_bp"
]

