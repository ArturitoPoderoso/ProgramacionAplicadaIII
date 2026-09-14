from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Perfil(Base):
    __tablename__ = "perfiles"
    id_perfil = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    descripcion = Column(String)
    estado_registro = Column(Integer, default=1)

class UsuarioPerfil(Base):
    __tablename__ = "usuario_perfiles"
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario', ondelete="CASCADE"), primary_key=True)
    id_perfil = Column(Integer, ForeignKey('perfiles.id_perfil', ondelete="CASCADE"), primary_key=True)
    estado_registro = Column(Integer, default=1)

class OpcionMenu(Base):
    __tablename__ = "opciones_menu"
    id_opcion_menu = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    url_menu = Column(String)
    descripcion = Column(String)
    id_padre = Column(Integer, ForeignKey('opciones_menu.id_opcion_menu', ondelete="CASCADE"))
    estado_registro = Column(Integer, default=1)

class OpcionMenuPerfil(Base):
    __tablename__ = "opciones_menu_perfiles"
    id_opcion_menu = Column(Integer, ForeignKey('opciones_menu.id_opcion_menu', ondelete="CASCADE"), primary_key=True)
    id_perfil = Column(Integer, ForeignKey('perfiles.id_perfil', ondelete="CASCADE"), primary_key=True)
    orden = Column(Integer, default=0)
    estado_registro = Column(Integer, default=1)

class User(Base):
    __tablename__ = "usuarios"

    id = Column("id_usuario", Integer, primary_key=True, index=True)
    first_name = Column("nombres", String, default="")
    last_name = Column("apellidos", String, default="")
    username = Column("nombre_usuario", String, index=True)
    email = Column("correo_electronico", String, default="")
    phone = Column("celular", String, default="")
    dni = Column("dni", String, default="")
    gender = Column("genero", String, default="")
    location = Column("sede", String)
    last_access = Column("ultimo_acceso", String, default="Nunca")
    is_active = Column("estado_registro", Integer, default=1)
    password = Column("clave", String, default="admin1234")

    # Relationship to Perfiles
    perfiles = relationship("Perfil", secondary="usuario_perfiles", lazy="joined")

    @property
    def roles(self):
        if self.perfiles:
            return [perfil.nombre for perfil in self.perfiles]
        return ["Vendedor"]

    @property
    def role(self):
        if self.perfiles and len(self.perfiles) > 0:
            return self.perfiles[0].nombre
        return "Vendedor"
