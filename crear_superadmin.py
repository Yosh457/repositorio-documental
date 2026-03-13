# crear_superadmin.py
from app import create_app
from models import db, Usuario, RolAplicacion

app = create_app()

def crear_admin():
    with app.app_context():
        print("\n--- CREACIÓN DE SUPER ADMINISTRADOR ---")
        
        # 1. Verificar que el rol 'Admin' exista (validación de catálogos base)
        rol_admin = RolAplicacion.query.filter_by(nombre='Admin').first()
        if not rol_admin:
            print("❌ Error: El rol 'Admin' no existe en la tabla roles_aplicacion.")
            print("Asegúrate de haber ejecutado los INSERTS iniciales en el script SQL.")
            return

        email = input("Ingresa el email del nuevo Admin: ").strip()
        
        # 2. Verificar si el usuario ya existe para evitar duplicidad
        if Usuario.query.filter_by(email=email).first():
            print(f"❌ Error: El email {email} ya está registrado en el sistema.")
            return
        
        password = input("Ingresa la contraseña temporal: ").strip()
        nombre = input("Ingresa el nombre completo (Ej: Super Administrador): ").strip()

        # 3. Crear el usuario con el nuevo modelo de datos
        nuevo_admin = Usuario(
            nombre_completo=nombre or "Super Administrador",
            email=email,
            rol_id=rol_admin.id,
            activo=True,
            cambio_clave_requerido=False, # Es el Admin raíz, asumimos que su clave inicial es segura
            profesion_id=None # El admin general no necesita una profesión asignada para operar
        )
        
        # Hasheo de contraseña utilizando el método del modelo
        nuevo_admin.set_password(password)
        
        try:
            db.session.add(nuevo_admin)
            db.session.commit()
            print(f"✅ ¡Éxito! Usuario {email} creado correctamente con rol de Administrador.")
        except Exception as e:
            print(f"❌ Error al guardar en la base de datos: {e}")
            db.session.rollback()

if __name__ == '__main__':
    crear_admin()