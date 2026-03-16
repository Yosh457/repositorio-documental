# utils/indexador.py
import os
import hashlib
from app import create_app
from models import db, Buscador, Documento
from utils.helpers import registrar_log_sistema, obtener_hora_chile

def normalizar_ruta(ruta):
    """
    Convierte la ruta a un estándar consistente (siempre usa '/')
    sin importar si el script corre en Windows o Linux.
    Conserva las mayúsculas/minúsculas originales para visualización.
    """
    return str(ruta).replace('\\', '/').strip('/')

def calcular_hash(ruta_normalizada):
    """
    Genera un identificador único (SHA-256).
    Aplica .lower() internamente para garantizar que cambios de 
    mayúsculas/minúsculas en Windows no generen documentos duplicados.
    """
    return hashlib.sha256(ruta_normalizada.lower().encode('utf-8')).hexdigest()

def indexar_buscador(buscador):
    """Ejecuta la indexación en memoria para un catálogo específico."""
    print(f"\n[>] Indexando catálogo: {buscador.nombre}...")
    ruta_base = buscador.ruta_carpeta

    if not os.path.exists(ruta_base):
        msg = f"Ruta inaccesible o inexistente: {ruta_base}"
        print(f"  [!] Error: {msg}")
        registrar_log_sistema("Error de Indexación", f"Catálogo '{buscador.nombre}': {msg}", usuario=None)
        return False

    # 1. Cargar estado actual de la BD en memoria (Hash -> Objeto Documento)
    docs_db = Documento.query.filter_by(buscador_id=buscador.id).all()
    memoria_docs = {doc.ruta_hash: doc for doc in docs_db}
    hashes_encontrados_en_disco = set()

    # Cambiamos 'omitidos' por 'verificados'
    contadores = {'nuevos': 0, 'reactivados': 0, 'desactivados': 0, 'verificados': 0}

    # 2. Recorrer el directorio físico
    for root, dirs, files in os.walk(ruta_base):
        for file in files:
            # Regla 1: Solo procesar archivos PDF
            if file.lower().endswith('.pdf'):
                ruta_absoluta = os.path.join(root, file)
                
                # Regla 2: Extraer y normalizar la ruta relativa
                ruta_relativa_raw = os.path.relpath(ruta_absoluta, ruta_base)
                ruta_relativa = normalizar_ruta(ruta_relativa_raw)
                ruta_hash = calcular_hash(ruta_relativa)

                hashes_encontrados_en_disco.add(ruta_hash)

                if ruta_hash in memoria_docs:
                    doc = memoria_docs[ruta_hash]
                    
                    # Refresco constante de metadata y fecha de verificación
                    doc.nombre_archivo = file
                    doc.ruta_relativa = ruta_relativa
                    doc.ultima_verificacion = obtener_hora_chile()

                    if not doc.activo:
                        # Regla 3: Reactivación de documentos inactivos
                        doc.activo = True
                        contadores['reactivados'] += 1
                    else:
                        contadores['verificados'] += 1
                else:
                    # Documento nuevo, lo preparamos para inserción
                    nuevo_doc = Documento(
                        nombre_archivo=file,
                        ruta_relativa=ruta_relativa,
                        ruta_hash=ruta_hash,
                        activo=True,
                        buscador_id=buscador.id,
                        fecha_indexado=obtener_hora_chile(),
                        ultima_verificacion=obtener_hora_chile()
                    )
                    db.session.add(nuevo_doc)
                    contadores['nuevos'] += 1

    # 3. Soft-Delete (Desactivar lo que ya no está físicamente)
    for ruta_hash, doc in memoria_docs.items():
        if ruta_hash not in hashes_encontrados_en_disco:
            if doc.activo:
                doc.activo = False
                doc.ultima_verificacion = obtener_hora_chile() # Registramos cuándo nos dimos cuenta que desapareció
                contadores['desactivados'] += 1

    # 4. Guardar la transacción y registrar auditoría
    try:
        db.session.commit()
        total_activos = len(hashes_encontrados_en_disco)
        resumen = (f"Catálogo '{buscador.nombre}': "
                   f"Nuevos: {contadores['nuevos']} | "
                   f"Reactivados: {contadores['reactivados']} | "
                   f"Desactivados: {contadores['desactivados']} | "
                   f"Verificados: {contadores['verificados']} | "
                   f"Total Activos: {total_activos}")
        print(f"  [+] {resumen}")
        
        # Regla 4: Registro en log_sistema (usuario=None porque es tarea de sistema)
        registrar_log_sistema("Indexación Completada", resumen, usuario=None)
        return True
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Fallo al hacer commit en BD para '{buscador.nombre}': {str(e)}"
        print(f"  [!] {error_msg}")
        registrar_log_sistema("Error de Indexación Crítico", error_msg, usuario=None)
        return False

def ejecutar_indexacion_completa():
    """Punto de entrada para ejecutar el script desde consola."""
    app = create_app()
    with app.app_context():
        print("=== INICIANDO PROCESO DE INDEXACIÓN DOCUMENTAL ===")
        buscadores_activos = Buscador.query.filter_by(activo=True).all()
        
        if not buscadores_activos:
            print("No hay catálogos activos configurados en la base de datos.")
            return

        for buscador in buscadores_activos:
            indexar_buscador(buscador)
            
        print("\n=== PROCESO DE INDEXACIÓN FINALIZADO ===")

if __name__ == '__main__':
    ejecutar_indexacion_completa()