# blueprints/buscadores.py
import os
from flask import Blueprint, render_template, request, flash, abort, send_file
from flask_login import login_required, current_user

from models import db, Buscador, Documento, LogAuditoriaDocumental

buscadores_bp = Blueprint('buscadores', __name__, template_folder='../templates')

# --- PROTECCIÓN GLOBAL ---
@buscadores_bp.before_request
@login_required
def before_request():
    """
    Exige que el usuario esté logueado para cualquier ruta de este blueprint.
    """
    pass

# --- RUTAS DE NAVEGACIÓN Y BÚSQUEDA ---

@buscadores_bp.route('/menu')
def index():
    """
    Menú Principal Dinámico.
    Muestra únicamente los botones correspondientes a los buscadores 
    que el administrador le asignó al usuario y que se encuentren activos.
    """
    # Filtramos la relación para asegurar que solo mostramos catálogos activos
    permisos = [b for b in current_user.buscadores_permitidos if b.activo]
    return render_template('buscadores/index.html', permisos=permisos)

@buscadores_bp.route('/buscar/<int:buscador_id>', methods=['GET', 'POST'])
def buscar(buscador_id):
    """
    Motor de Búsqueda Documental.
    Obliga a usar POST para la búsqueda real (evita RUTs y motivos en la URL).
    """
    # 1. Validamos que el buscador exista y esté activo
    buscador = Buscador.query.filter_by(id=buscador_id, activo=True).first_or_404()

    # 2. Validación Estricta de Permisos de Acceso al Buscador
    if buscador not in current_user.buscadores_permitidos:
        abort(403)

    resultados = None
    busqueda_actual = ''
    motivo_actual = ''

    if request.method == 'POST':
        # Capturamos datos del formulario de forma segura
        busqueda_actual = request.form.get('busqueda', '').strip()
        motivo_actual = request.form.get('motivo', '').strip()

        # 3. Validaciones de Negocio
        if not motivo_actual:
            flash('El motivo de la búsqueda es obligatorio para fines de auditoría clínica/legal.', 'warning')
        elif not busqueda_actual:
            flash('Debes ingresar un término de búsqueda (ej. RUT o Apellido).', 'warning')
        else:
            # 4. Consulta a la Base de Datos (Usa ILIKE para ignorar mayúsculas/minúsculas)
            resultados = Documento.query.filter(
                Documento.buscador_id == buscador_id,
                Documento.activo == True,
                Documento.nombre_archivo.ilike(f'%{busqueda_actual}%')
            ).limit(100).all() # Límite por seguridad para evitar saturación de RAM

            # 5. Trazabilidad Estricta: Registro de Búsqueda
            nuevo_log = LogAuditoriaDocumental(
                usuario_id=current_user.id,
                buscador_id=buscador_id,
                tipo_evento='BUSQUEDA',
                termino_busqueda=busqueda_actual,
                motivo=motivo_actual,
                cantidad_resultados=len(resultados)
            )
            db.session.add(nuevo_log)
            db.session.commit()

    # Si es GET, simplemente renderiza el formulario vacío. Si es POST fallido o exitoso, pasa variables.
    return render_template('buscadores/buscar.html',
                           buscador=buscador,
                           resultados=resultados,
                           busqueda_actual=busqueda_actual,
                           motivo_actual=motivo_actual)

# --- VISUALIZADOR SEGURO DE DOCUMENTOS ---

@buscadores_bp.route('/visor/<int:documento_id>')
def visor(documento_id):
    """
    Endpoint intermedio y seguro que entrega el binario PDF.
    Nunca expone la ruta de red real en el navegador.
    """
    # 1. Validamos que el documento exista y esté activo
    documento = Documento.query.filter_by(id=documento_id, activo=True).first_or_404()

    # 2. Validación de Permisos (¿El usuario puede ver ESTE documento?)
    if documento.buscador not in current_user.buscadores_permitidos or not documento.buscador.activo:
        abort(403)

    # 3. Trazabilidad Estricta: Registro de Visualización Exacta
    nuevo_log = LogAuditoriaDocumental(
        usuario_id=current_user.id,
        buscador_id=documento.buscador_id,
        tipo_evento='VISUALIZACION',
        documento_id=documento.id
    )
    db.session.add(nuevo_log)
    db.session.commit()

    # 4. Ensamblaje seguro de la ruta de red
    # ruta_carpeta ej: '\\10.20.10.7\ST-Digitalización CHRG'
    # ruta_relativa ej: '2008\25-11-2008\archivo.pdf'
    ruta_base = documento.buscador.ruta_carpeta
    ruta_relativa = documento.ruta_relativa
    
    # Prevenimos que lstrip destruya la ruta unida en Windows, usando os.path.join
    ruta_fisica = os.path.join(ruta_base, ruta_relativa.lstrip('\\/'))

    # 5. Verificación física antes de enviar
    if not os.path.exists(ruta_fisica):
        # Respuesta limpia de archivo no encontrado en disco
        abort(404)

    # 6. Servir el documento directamente al lector PDF del navegador
    # as_attachment=False obliga al navegador a intentar mostrarlo en vez de descargarlo
    return send_file(ruta_fisica, as_attachment=False)