from database import engine, Base
import models
from models import User, Perfil, UsuarioPerfil, OpcionMenu, OpcionMenuPerfil
from sqlalchemy.orm import Session

print("Creando base de datos local jesmi.db...")
Base.metadata.create_all(bind=engine)

print("Insertando datos...")
with Session(engine) as session:
    # Perfiles
    session.add(Perfil(id_perfil=1, nombre="Administrador", descripcion="Control total del sistema", estado_registro=1))
    session.add(Perfil(id_perfil=2, nombre="Supervisor", descripcion="Supervisión de vendedores", estado_registro=1))
    session.add(Perfil(id_perfil=3, nombre="Vendedor", descripcion="Acceso limitado a ventas", estado_registro=1))
    
    # Usuarios
    session.add(User(id=3, first_name="Denzel Leyton", last_name="Ccoyllo Siguenza", username="DenzelC", email="2024002231@unfv.edu.pe", phone="999888111", dni="71528801", gender="Masculino", location="OLIVOS", password="123456", last_access="Nunca", is_active=1))
    session.add(User(id=5, first_name="Luis Arturo", last_name="Alvarado Puyen", username="ArturoAP", email="2024023935@unfv.edu.pe", phone="977748394", dni="74915722", gender="Masculino", location="SJL", password="admin1234", last_access="Nunca", is_active=1))
    session.add(User(id=1, first_name="Lenin Allister", last_name="Alvarez Jara", username="Lenin", email="2024023953@untv.edu.pe", phone="+51 939 949 438", dni="72644473-6", gender="Masculino", location="OLIVOS", password="123456", last_access="Nunca", is_active=1))
    session.add(User(id=2, first_name="Juan David", last_name="Enriquez Coronel", username="JuanD", email="juandavid@gmail.com", phone="999888777", dni="9876543", gender="Masculino", location="SJL", password="admin1234", last_access="Nunca", is_active=1))

    # UsuarioPerfil
    session.add(UsuarioPerfil(id_usuario=2, id_perfil=3, estado_registro=1))
    session.add(UsuarioPerfil(id_usuario=5, id_perfil=1, estado_registro=1))
    session.add(UsuarioPerfil(id_usuario=5, id_perfil=3, estado_registro=1))
    session.add(UsuarioPerfil(id_usuario=1, id_perfil=1, estado_registro=1))
    session.add(UsuarioPerfil(id_usuario=1, id_perfil=3, estado_registro=1))
    session.add(UsuarioPerfil(id_usuario=3, id_perfil=2, estado_registro=1))
    session.add(UsuarioPerfil(id_usuario=3, id_perfil=3, estado_registro=1))

    # Opciones menu
    session.add(OpcionMenu(id_opcion_menu=1, nombre="Seguridad", url_menu="#", descripcion="Módulo de administración", id_padre=None, estado_registro=1))
    session.add(OpcionMenu(id_opcion_menu=2, nombre="Usuarios", url_menu="dashboard.html", descripcion="Gestión de usuarios", id_padre=1, estado_registro=1))
    session.add(OpcionMenu(id_opcion_menu=3, nombre="Mi Perfil", url_menu="perfil.html", descripcion="Perfil del usuario actual", id_padre=1, estado_registro=1))

    # OpcionMenuPerfil
    session.add(OpcionMenuPerfil(id_opcion_menu=1, id_perfil=1, orden=0, estado_registro=1))
    session.add(OpcionMenuPerfil(id_opcion_menu=2, id_perfil=1, orden=0, estado_registro=1))
    session.add(OpcionMenuPerfil(id_opcion_menu=3, id_perfil=1, orden=0, estado_registro=1))
    
    session.commit()
    print("Base de datos local inicializada correctamente!")
