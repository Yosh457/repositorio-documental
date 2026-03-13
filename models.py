# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

def obtener_hora_chile():
    cl_tz = pytz.timezone('America/Santiago')
    return datetime.now(cl_tz)

# ==============================================================================
# TABLAS PUENTE (MANY-TO-MANY)
# ==============================================================================

usuario_buscadores = db.Table('usuario_buscadores',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), primary_key=True),
    db.Column('buscador_id', db.Integer, db.ForeignKey('buscadores.id', ondelete='CASCADE'), primary_key=True)
)

# ==============================================================================
# CATÁLOGOS Y CONFIGURACIÓN
# ==============================================================================

class RolAplicacion(db.Model):
    __tablename__ = 'roles_aplicacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    
    usuarios = db.relationship('Usuario', back_populates='rol')

class Profesion(db.Model):
    __tablename__ = 'profesiones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    usuarios = db.relationship('Usuario', back_populates='profesion')

class Buscador(db.Model):
    __tablename__ = 'buscadores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    ruta_carpeta = db.Column(db.String(255), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)

    documentos = db.relationship('Documento', back_populates='buscador', cascade="all, delete-orphan")
    usuarios = db.relationship('Usuario', secondary=usuario_buscadores, back_populates='buscadores_permitidos')

# ==============================================================================
# TABLAS PRINCIPALES
# ==============================================================================

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=obtener_hora_chile)
    cambio_clave_requerido = db.Column(db.Boolean, default=False, nullable=False)
    
    # Token de 32 chars con unicidad optimizada
    reset_token = db.Column(db.String(32), unique=True, nullable=True)
    reset_token_expiracion = db.Column(db.DateTime, nullable=True)

    rol_id = db.Column(db.Integer, db.ForeignKey('roles_aplicacion.id'), nullable=False, index=True)
    rol = db.relationship('RolAplicacion', back_populates='usuarios')

    profesion_id = db.Column(db.Integer, db.ForeignKey('profesiones.id'), nullable=True, index=True)
    profesion = db.relationship('Profesion', back_populates='usuarios')

    buscadores_permitidos = db.relationship('Buscador', secondary=usuario_buscadores, back_populates='usuarios')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Documento(db.Model):
    __tablename__ = 'documentos'
    id = db.Column(db.Integer, primary_key=True)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_relativa = db.Column(db.String(1024), nullable=False)
    ruta_hash = db.Column(db.String(64), nullable=False, comment='SHA-256 de ruta_relativa para unicidad')
    fecha_indexado = db.Column(db.DateTime, default=obtener_hora_chile)
    ultima_verificacion = db.Column(db.DateTime, default=obtener_hora_chile, onupdate=obtener_hora_chile)
    activo = db.Column(db.Boolean, default=True)

    buscador_id = db.Column(db.Integer, db.ForeignKey('buscadores.id', ondelete='CASCADE'), nullable=False, index=True)
    buscador = db.relationship('Buscador', back_populates='documentos')

    __table_args__ = (
        db.UniqueConstraint('buscador_id', 'ruta_hash', name='uk_documentos_buscador_hash'),
        db.Index('idx_documentos_buscador_nombre', 'buscador_id', 'nombre_archivo'),
    )

# ==============================================================================
# AUDITORÍA Y LOGS
# ==============================================================================

class LogSistema(db.Model):
    __tablename__ = 'log_sistema'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=obtener_hora_chile, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True, index=True)
    usuario_nombre = db.Column(db.String(255), nullable=True)
    accion = db.Column(db.String(255), nullable=False)
    detalles = db.Column(db.Text)

    usuario = db.relationship('Usuario')

class LogAuditoriaDocumental(db.Model):
    __tablename__ = 'log_auditoria_documental'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=obtener_hora_chile, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    buscador_id = db.Column(db.Integer, db.ForeignKey('buscadores.id', ondelete='SET NULL'), nullable=True)
    tipo_evento = db.Column(db.Enum('BUSQUEDA', 'VISUALIZACION', name='tipo_evento_enum'), nullable=False)
    termino_busqueda = db.Column(db.String(255), nullable=True)
    motivo = db.Column(db.Text)
    cantidad_resultados = db.Column(db.Integer, nullable=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id', ondelete='SET NULL'), nullable=True, index=True)

    usuario = db.relationship('Usuario')
    buscador = db.relationship('Buscador')
    documento = db.relationship('Documento')

    __table_args__ = (
        db.Index('idx_logaud_usuario_fecha', 'usuario_id', 'timestamp'),
        db.Index('idx_logaud_buscador_fecha', 'buscador_id', 'timestamp'),
    )