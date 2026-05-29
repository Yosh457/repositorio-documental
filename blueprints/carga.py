# blueprints/carga.py
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user

from models import db, Buscador, Documento, LogAuditoriaDocumental
from utils.helpers import obtener_ip_cliente, obtener_hora_chile
from utils.indexador import calcular_hash, normalizar_ruta

carga_bp = Blueprint('carga', __name__, template_folder='../templates', url_prefix='/carga')

@carga_bp.before_request
@login_required
def before_request():
    """Protección global: Solo usuarios autenticados pueden acceder."""
    pass

@carga_bp.route('/menu')
def menu_carga():
    """
    Muestra los catálogos donde el usuario tiene permiso de CARGAR.
    """
    # Filtramos solo los permisos donde puede_cargar es True y el buscador está activo
    permisos_carga = [
        p.buscador for p in current_user.permisos_buscadores 
        if p.puede_cargar and p.buscador.activo
    ]
    
    return render_template('carga/menu.html', permisos=permisos_carga)

@carga_bp.route('/api/carpetas/<int:buscador_id>', methods=['GET'])
def api_carpetas(buscador_id):
    """
    API (AJAX): Devuelve las subcarpetas de un nivel específico.
    Protegido matemáticamente contra Path Traversal usando pathlib.
    """
    # 1. Validar permisos de CARGA estrictos
    permiso = next((p for p in current_user.permisos_buscadores if p.buscador_id == buscador_id and p.puede_cargar), None)
    if not permiso or not permiso.buscador.activo:
        abort(403, description="No tienes permisos de carga para este catálogo.")

    # Capturar la subcarpeta solicitada (si viene vacía, es la raíz del buscador)
    sub_ruta = request.args.get('ruta', '').strip('\\/')
    
    # 2. Ensamblar y resolver la ruta objetivo (Escudo Path Traversal)
    try:
        # resolve() evalúa la ruta real y elimina cualquier '../'
        ruta_base = Path(permiso.buscador.ruta_carpeta).resolve()
        ruta_objetivo = (ruta_base / sub_ruta).resolve()
    except Exception as e:
        abort(400, description="Error procesando la ruta solicitada.")

    # Verificación Estricta: La ruta objetivo DEBE ser hija de la ruta base (o ser exactamente la misma)
    if ruta_base not in ruta_objetivo.parents and ruta_objetivo != ruta_base:
        abort(403, description="Acceso denegado: Intento de salto de directorio detectado.")

    # 3. Leer el directorio físico SIN recursividad (solo el primer nivel)
    carpetas = []
    
    # Convertimos Path de vuelta a string para mantener compatibilidad con os.scandir y manejo de red
    ruta_objetivo_str = str(ruta_objetivo)
    
    if os.path.exists(ruta_objetivo_str) and os.path.isdir(ruta_objetivo_str):
        try:
            # os.scandir es óptimo para lectura rápida por red (SMB)
            with os.scandir(ruta_objetivo_str) as entradas:
                for entrada in entradas:
                    if entrada.is_dir():
                        carpetas.append(entrada.name)
        except PermissionError:
            abort(403, description="El sistema no tiene permisos de lectura sobre esta carpeta física.")
        except Exception as e:
            abort(500, description=f"Error leyendo el directorio: {str(e)}")
            
    # Ordenar alfabéticamente para mejor UX
    carpetas.sort()
    
    return jsonify({
        'ruta_actual': sub_ruta,
        'carpetas': carpetas
    })
    
@carga_bp.route('/explorador/<int:buscador_id>')
def explorador(buscador_id):
    """
    Renderiza la interfaz de navegación y carga para un catálogo específico.
    """
    # Validamos permisos
    permiso = next((p for p in current_user.permisos_buscadores if p.buscador_id == buscador_id and p.puede_cargar), None)
    if not permiso or not permiso.buscador.activo:
        abort(403, description="No tienes permisos de carga para este catálogo.")
        
    return render_template('carga/subir.html', buscador=permiso.buscador)

@carga_bp.route('/api/upload', methods=['POST'])
def api_upload():
    """
    API que recibe los archivos, los guarda en disco y los indexa en caliente.
    Rechaza archivos que no sean PDF o que ya existan (política estricta).
    """
    # 1. Validar que la petición traiga archivos
    if 'archivos' not in request.files:
        return jsonify({'error': 'No se enviaron archivos'}), 400

    archivos = request.files.getlist('archivos')
    buscador_id = request.form.get('buscador_id')
    ruta_destino = request.form.get('ruta_destino', '').strip('\\/')

    if not buscador_id or not archivos:
        return jsonify({'error': 'Faltan datos requeridos (archivos o buscador)'}), 400

    # 2. Validar permisos de CARGA
    permiso = next((p for p in current_user.permisos_buscadores if p.buscador_id == int(buscador_id) and p.puede_cargar), None)
    if not permiso or not permiso.buscador.activo:
        return jsonify({'error': 'No tienes permisos de carga para este catálogo'}), 403

    # 3. Validar y ensamblar ruta destino física (Escudo Path Traversal)
    try:
        ruta_base = Path(permiso.buscador.ruta_carpeta).resolve()
        ruta_objetivo = (ruta_base / ruta_destino).resolve()
        
        if ruta_base not in ruta_objetivo.parents and ruta_objetivo != ruta_base:
            return jsonify({'error': 'Salto de directorio no permitido'}), 403
            
        if not ruta_objetivo.exists() or not ruta_objetivo.is_dir():
            return jsonify({'error': 'La carpeta de destino ya no existe'}), 404
    except Exception:
        return jsonify({'error': 'Ruta de destino inválida'}), 400

    resultados = []
    exitosos = 0
    errores = 0
    
    # Límite de 50 MB por archivo (ajustable según necesidades de la clínica)
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

    # 4. Procesar cada archivo individualmente
    for archivo in archivos:
        # Si el usuario mandó un input vacío
        if archivo.filename == '':
            continue

        # A. Validación de Extensión (Fase 1: Solo PDF)
        if not archivo.filename.lower().endswith('.pdf'):
            resultados.append({'archivo': archivo.filename, 'estado': 'error', 'mensaje': 'Solo se permiten archivos PDF'})
            errores += 1
            continue
            
        # B. Validación de Tamaño en Backend ---
        # Leemos el tamaño del archivo moviendo el cursor al final y regresando
        archivo.seek(0, os.SEEK_END)
        file_size = archivo.tell()
        archivo.seek(0, os.SEEK_SET) # Volvemos al inicio para poder guardarlo luego

        if file_size > MAX_FILE_SIZE_BYTES:
            resultados.append({'archivo': archivo.filename, 'estado': 'error', 'mensaje': 'El archivo supera el límite máximo de 50 MB'})
            errores += 1
            continue
        
        # C. Limpieza del nombre de archivo conservando el original
        nombre_limpio = secure_filename(archivo.filename)
        # Si el secure_filename borra todo (ej. si se llamaba "???"), usamos un fallback
        if not nombre_limpio:
            nombre_limpio = f"doc_{obtener_hora_chile().strftime('%Y%m%d%H%M%S')}.pdf"

        # Rutas finales para guardar
        ruta_fisica_archivo = ruta_objetivo / nombre_limpio
        
        # D. Política de Duplicados (Bloqueo Físico)
        if ruta_fisica_archivo.exists():
            resultados.append({'archivo': nombre_limpio, 'estado': 'error', 'mensaje': 'El archivo ya existe en esta carpeta'})
            errores += 1
            continue

        # F. Cálculos para la Base de Datos
        # Necesitamos la ruta relativa desde la raíz del buscador, ej: "DAU\2008\archivo.pdf"
        ruta_relativa = os.path.relpath(str(ruta_fisica_archivo), str(ruta_base))
        ruta_relativa_norm = normalizar_ruta(ruta_relativa)
        ruta_hash = calcular_hash(ruta_relativa_norm)

        # G. Política de Duplicados (Bloqueo Lógico DB)
        if Documento.query.filter_by(buscador_id=permiso.buscador.id, ruta_hash=ruta_hash).first():
            resultados.append({'archivo': nombre_limpio, 'estado': 'error', 'mensaje': 'Ya existe un documento indexado con este nombre en esta ubicación'})
            errores += 1
            continue

        # --- TRANSACCIÓN CRÍTICA (Disco + Base de Datos) ---
        try:
            # Paso 1: Guardar Físicamente
            archivo.save(str(ruta_fisica_archivo))
            
            # Paso 2: Indexar en Caliente
            nuevo_doc = Documento(
                nombre_archivo=nombre_limpio,
                ruta_relativa=ruta_relativa_norm,
                ruta_hash=ruta_hash,
                activo=True,
                buscador_id=permiso.buscador.id,
                fecha_indexado=obtener_hora_chile(),
                ultima_verificacion=obtener_hora_chile()
            )
            db.session.add(nuevo_doc)
            db.session.flush() # Para obtener el ID del documento
            
            # Paso 3: Auditoría Documental
            nuevo_log = LogAuditoriaDocumental(
                usuario_id=current_user.id,
                buscador_id=permiso.buscador.id,
                tipo_evento='CARGA',
                documento_id=nuevo_doc.id,
                ip_origen=obtener_ip_cliente(),
                motivo=f"Carga manual en: {ruta_destino}"
            )
            db.session.add(nuevo_log)
            db.session.commit()
            
            resultados.append({'archivo': nombre_limpio, 'estado': 'success', 'mensaje': 'Subido e indexado'})
            exitosos += 1
            
        except Exception as e:
            db.session.rollback()
            # Si falla la base de datos pero el archivo físico se guardó, lo eliminamos (Rollback físico)
            if ruta_fisica_archivo.exists():
                try: os.remove(str(ruta_fisica_archivo))
                except: pass
            
            resultados.append({'archivo': nombre_limpio, 'estado': 'error', 'mensaje': 'Error interno al guardar'})
            errores += 1

    return jsonify({
        'exitosos': exitosos,
        'errores': errores,
        'detalles': resultados
    })