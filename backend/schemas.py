from pydantic import BaseModel
from typing import List, Optional

class UserBase(BaseModel):
    username: str
    role: str
    roles: Optional[List[str]] = None
    location: str

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    last_access: str

    class Config:
        from_attributes = True

# --- Esquemas de Almacén ---

class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id_categoria: int
    estado_registro: int

    class Config:
        from_attributes = True

class ProductoBase(BaseModel):
    codigo_producto: str
    nombre: str
    descripcion: Optional[str] = None
    precio_compra: float
    precio_venta: float
    stock_actual: int = 0
    stock_minimo: int = 0
    id_categoria: Optional[int] = None

class ProductoCreate(ProductoBase):
    pass

class ProductoResponse(ProductoBase):
    id_producto: int
    estado_registro: int
    categoria: Optional[CategoriaResponse] = None

    class Config:
        from_attributes = True

class MovimientoAlmacenCreate(BaseModel):
    id_producto: int
    tipo: str # 'ENTRADA', 'SALIDA', 'AJUSTE'
    cantidad: int
    observacion: Optional[str] = None

# --- Esquemas de Ventas ---

class DetalleVentaCreate(BaseModel):
    id_producto: int
    cantidad: int
    precio_unitario: float

class VentaCreate(BaseModel):
    metodo_pago: str
    detalles: List[DetalleVentaCreate]

class DetalleVentaResponse(DetalleVentaCreate):
    id_detalle: int
    subtotal: float
    producto: Optional[ProductoResponse] = None

    class Config:
        from_attributes = True

class VentaResponse(BaseModel):
    id_venta: int
    correlativo: str
    fecha_venta: str # Lo parsearemos como string para el front
    total: float
    metodo_pago: str
    id_usuario: int
    detalles: List[DetalleVentaResponse]

    class Config:
        from_attributes = True
