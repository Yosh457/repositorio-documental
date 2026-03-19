# serve.py
import os
import logging
from logging.handlers import RotatingFileHandler

from waitress import serve

from app import create_app
from models import db


# ============================================================
# CONFIGURACIÓN BASE
# ============================================================

# Ruta base del proyecto (directorio donde vive este archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carpeta física de logs del servidor
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Archivo principal de log del arranque/servidor
LOG_FILE = os.path.join(LOG_DIR, 'repositorio_documental.log')


# ============================================================
# LOGGER DEL SERVICIO
# ============================================================

def configurar_logger():
    """
    Configura el logger principal del servicio de producción.

    - Usa RotatingFileHandler para evitar crecimiento infinito del log.
    - Agrega salida a consola para facilitar pruebas manuales.
    - Evita duplicar handlers si el módulo se carga más de una vez.
    """
    logger = logging.getLogger('repositorio_documental')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Evita agregar handlers duplicados si el proceso o módulo
    # se inicializa más de una vez.
    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,   # 5 MB por archivo
        backupCount=3,              # conserva hasta 3 respaldos
        encoding='utf-8'
    )

    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = configurar_logger()


# ============================================================
# APP FLASK
# ============================================================

# La factory create_app() ya carga la configuración general del proyecto
# y las variables necesarias desde el .env según tu implementación actual.
app = create_app()


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_puerto_waitress():
    """
    Lee el puerto desde la variable de entorno WAITRESS_PORT.

    Si no existe, usa 8080 por defecto.
    Si existe pero no es un entero válido, registra advertencia y usa 8080.
    """
    port_raw = os.environ.get('WAITRESS_PORT', '8080')

    try:
        return int(port_raw)
    except ValueError:
        logger.warning(
            "WAITRESS_PORT inválido ('%s'). Se utilizará el puerto 8080.",
            port_raw
        )
        return 8080


def verificar_base_de_datos():
    """
    Verifica conectividad básica a la base de datos y asegura la estructura
    mínima usando SQLAlchemy.

    Se ejecuta antes de levantar Waitress para no arrancar el servicio
    'a ciegas' si existe un problema grave con MySQL o con el modelo.
    """
    try:
        with app.app_context():
            db.create_all()
        logger.info("Verificación de base de datos completada correctamente.")
        return True

    except Exception as exc:
        logger.exception(
            "Error al verificar la base de datos antes de iniciar el servicio: %s",
            exc
        )
        return False


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == '__main__':
    puerto = obtener_puerto_waitress()

    logger.info("=" * 70)
    logger.info("Iniciando Repositorio Documental en modo producción")
    logger.info("Motor WSGI: Waitress")
    logger.info("Binding interno: http://127.0.0.1:%s", puerto)
    logger.info("Exposición externa esperada: a través de proxy inverso")
    logger.info("Archivo de log: %s", LOG_FILE)
    logger.info("=" * 70)

    # Si falla la verificación de BD, no levantamos el servidor.
    if not verificar_base_de_datos():
        logger.error("El servicio no se iniciará debido a errores de base de datos.")
        raise SystemExit(1)

    # Waitress escucha solo en localhost para obligar el paso por Nginx.
    serve(
        app,
        host='127.0.0.1',
        port=puerto,
        threads=6
    )