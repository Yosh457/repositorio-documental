# 📁 Repositorio Documental - Búsqueda y Visualización Centralizada de Documentos

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)
![Database](https://img.shields.io/badge/Database-MySQL_8+-blue.svg)
![ORM](https://img.shields.io/badge/ORM-SQLAlchemy-red.svg)

Plataforma web desarrollada para la **Red de Atención Primaria de Salud Municipal de Alto Hospicio**. Su objetivo es centralizar la búsqueda, visualización y auditoría de documentos físicos alojados en recursos compartidos de red, garantizando trazabilidad clínica/legal y evitando la exposición de rutas sensibles.

## 📌 Estado Actual del Proyecto

- **Estado actual:** sistema funcional y validado en entorno local.
- **Cobertura actual:** autenticación, administración, gestión de buscadores, búsqueda documental, visor seguro, auditoría documental e indexación batch.
- **Próxima etapa:** documentación operativa de despliegue y posterior preparación para ejecución en servidor Windows.

## 🧩 Módulos Actualmente Operativos

El sistema cuenta actualmente con los siguientes módulos construidos y funcionales:

1. **Autenticación:** login, cambio obligatorio de clave, reseteo vía token de correo y control de sesión con timeout por inactividad (lado cliente).
2. **Administración de Usuarios:** creación, edición, activación/desactivación y asignación granular de permisos por buscador.
3. **Gestión de Buscadores:** creación, edición, activación/desactivación y administración de rutas físicas de red.
4. **Búsqueda Documental:** motor de búsqueda con ingreso obligatorio de motivo de auditoría.
5. **Visor Seguro:** entrega protegida de archivos PDF sin exponer la ruta física real.
6. **Auditoría Documental:** registro y visualización administrativa de búsquedas y visualizaciones.
7. **Indexador Batch:** proceso de sincronización entre almacenamiento físico y base de datos con soft-delete y reactivación.

## 🔄 Flujo General del Sistema

1. El usuario accede al sistema mediante autenticación.
2. El sistema carga dinámicamente los buscadores según los permisos asignados al usuario.
3. El usuario realiza una búsqueda ingresando término y motivo.
4. El backend valida permisos y consulta los documentos indexados en base de datos.
5. Se registra la búsqueda en la auditoría documental.
6. El usuario selecciona un documento para visualizar.
7. El sistema valida acceso y entrega el archivo mediante un visor seguro sin exponer la ruta física.
8. Se registra el evento de visualización en la auditoría documental.

## 🚀 Características Principales

### 🔍 Motor de búsqueda documental

- **Búsqueda por formulario:** los términos de búsqueda y su motivo se envían mediante formulario, evitando exponerlos innecesariamente en la URL y en flujos visibles del navegador.
- **Menú dinámico por permisos:** cada usuario solo visualiza los buscadores que tiene asignados.
- **Visor enmascarado:** los PDFs se sirven mediante `send_file`, evitando exponer directamente rutas UNC o rutas físicas del storage.
- **Control de acceso real:** antes de servir cualquier documento, el backend valida que el usuario tenga permisos sobre el buscador correspondiente.

### 🔄 Indexación inteligente

- **Procesamiento batch independiente:** script que recorre carpetas físicas y sincroniza el estado de los documentos con la base de datos.
- **Comparación por hash:** uso de SHA-256 calculado sobre rutas relativas normalizadas.
- **Case-insensitive para entornos Windows/SMB:** se evita generar duplicados por cambios de mayúsculas/minúsculas en nombres o rutas.
- **Soft-delete:** si un archivo desaparece del storage, no se elimina de la base de datos; se marca como inactivo.
- **Reactivación automática:** si un archivo previamente inactivo reaparece en la carpeta, vuelve a activarse.
- **Actualización de verificación:** en cada corrida se actualiza `ultima_verificacion` para reflejar sincronización real.

### 🧾 Auditoría y trazabilidad

- **Auditoría de búsqueda:** registra usuario, buscador, término buscado, motivo y cantidad de resultados.
- **Auditoría de visualización:** registra usuario, buscador y documento exacto visualizado.
- **Logs del sistema:** registra eventos administrativos y operacionales como login, edición de usuarios, cambios de estado, creación de buscadores e indexación.

## 🛠️ Stack Tecnológico

- **Backend:** Python 3, Flask, Blueprints.
- **Base de Datos:** MySQL 8+, SQLAlchemy ORM, PyMySQL.
- **Frontend:** HTML5, Jinja2, TailwindCSS, JavaScript.
- **Autenticación y seguridad:** Flask-Login, Flask-WTF (CSRF), Werkzeug (hash de contraseñas).
- **Correo:** SMTP mediante utilidades internas del proyecto.

## 📂 Estructura del Proyecto

El proyecto sigue una arquitectura modular basada en **Blueprints**:

```text
RepositorioDocumental/
├── blueprints/          # Lógica de enrutamiento y controladores
│   ├── admin.py         # Gestión de usuarios, buscadores y paneles de auditoría
│   ├── auth.py          # Autenticación, reseteo y cambio de clave
│   └── buscadores.py    # Motor de búsqueda y endpoint del visor seguro PDF
├── static/              # Archivos estáticos
│   ├── css/             # Estilos personalizados (Tailwind base, style.css)
│   ├── docs/            # Documentación
│   ├── img/             # Assets gráficos (Logos, favicon)
│   └── js/              # Scripts de UX (flash_messages, modal_handler, session_timeout, validation)
├── templates/           # Vistas HTML (Jinja2)
│   ├── admin/           # Formularios y tablas de gestión (CRUD) y logs
│   ├── auth/            # Vistas de acceso y seguridad
│   ├── buscadores/      # Menú dinámico y motor de búsqueda
│   ├── errors/          # Páginas de error personalizadas (403, 404, 500)
│   ├── _macros.html
│   └── base.html
├── utils/               # Módulos transversales y scripts Batch
│   ├── __init__.py      # Exportación centralizada de utilidades
│   ├── decorators.py    # Filtros de roles (Admin) y cambio de clave
│   ├── email.py         # Lógica de envío de correos institucionales
│   ├── helpers.py       # Funciones auxiliares (validaciones, hora local)
│   └── indexador.py     # Script core de escaneo e indexación física
├── venv/                # Entorno virtual
├── .env                 # Variables de entorno (Local)
├── .gitignore
├── app.py               # Fábrica de la aplicación (create_app) y auto-creación de tablas
├── crear_superadmin.py  # Script para crear administrador inicial
├── extensions.py        # Inicialización de extensiones
├── models.py            # Modelos de Base de Datos y relaciones (SQLAlchemy)
└── requirements.txt     # Dependencias del proyecto
```
## ⚡ Instalación Rápida

1. Clonar el repositorio:
   
   ```bash
   git clone https://github.com/Yosh457/repositorio-documental.git
   cd RepositorioDocumental
   ```
2. Crear y activar entorno virtual:
   
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```
3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```
4. Configurar archivo `.env`
5. Crear la base de datos en MySQL
   *(Para más detalle, ver sección **Preparación de Base de Datos**).*
6. Inicializar tablas con Flask/SQLAlchemy
   *(Para más detalle, ver sección **Preparación de Base de Datos**).*
7. Crear el superadmin:

   ```bash
   python crear_superadmin.py
   ```
8. Ejecutar la aplicación:

   ```bash
   python app.py
   ```
9. Acceder desde el navegador a: `http://127.0.0.1:5000`

## ⚙️ Variables de Entorno

El proyecto utiliza un archivo `.env` en la raíz. Variables mínimas esperadas:

```env
SECRET_KEY=tu_clave_secreta
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=tu_password
MYSQL_DB=repositorio_docs_db
EMAIL_USUARIO=tu_correo@saludmaho.cl
EMAIL_CONTRASENA=tu_app_password
```
## 🗄️ Preparación de Base de Datos

1. Crear manualmente la base de datos en MySQL:
   
   ```sql
    CREATE DATABASE repositorio_docs_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    ```
  
2. Luego inicializar las tablas del proyecto con Flask/SQLAlchemy.
    ```bash
    flask shell
    ```
    Dentro de la shell interactiva de Flask ejecuta línea por línea lo siguiente:
    
    ```python
    from models import db
    db.create_all()
    exit()
    ```
    Aunque la aplicación puede crear tablas en ciertos flujos de ejecución, para fines técnicos y de instalación se recomienda usar explícitamente `db.create_all()`.

## 👤 Creación de Superadmin

Una vez creada la base de datos y generadas las tablas, ejecutar:

```bash
python crear_superadmin.py
```

Este script crea el primer usuario administrador del sistema usando el modelo actual del proyecto.

## 📥 Uso del Indexador

El indexador batch sincroniza los documentos físicos con la tabla `documentos`.

Se recomienda haber creado al menos un buscador antes de ejecutar la primera indexación.

Ejecutar desde la raíz del proyecto:

```bash
python -m utils.indexador
```

Comportamientos validados del indexador:

* Indexación inicial de archivos PDFs
* Verificación sin duplicados en reindexaciones posteriores
* Desactivación lógica de archivos retirados físicamente
* Reactivación automática al reaparecer
* Tolerancia a diferencias de mayúsculas/minúsculas en rutas dentro del contexto definido

## 💻 Ejecución en Entorno Local

Con entorno virtual activado:

```bash
python app.py
```

Luego acceder desde el navegador a: `http://127.0.0.1:5000`

## 🔐 Consideraciones de Seguridad Implementadas

* Hash seguro de contraseñas mediante Werkzeug
* Protección CSRF en formularios POST gestionados por Flask-WTF
* Validación de permisos antes de acceder a buscadores o visualizar documentos
* Visor seguro que entrega archivos por ID interno en vez de exponer rutas físicas
* Auditoría documental separada de logs administrativos
* Reseteo de contraseña mediante token y expiración
* Ocultamiento práctico de rutas sensibles hacia el cliente final

## ✨ Mejoras de UX Implementadas

* Prevención de doble envío en formularios con estado visual `Procesando...`
* Autofocus en el campo principal de búsqueda documental
* Descarga de PDFs con el nombre real del archivo usando `download_name`
* Retención de datos previos en formularios con errores de validación
* Indicadores visuales de estado en tablas administrativas
* Menús y vistas consistentes según permisos del usuario

## ⚠️ Consideraciones Operativas

* El sistema depende de rutas de red accesibles, ya sea por UNC o mecanismos equivalentes disponibles en el servidor
* El usuario o servicio que ejecute la aplicación debe tener permisos de lectura sobre las rutas configuradas
* El proceso de indexación debe ejecutarse periódicamente para mantener consistencia entre la base de datos y el almacenamiento físico
* La etapa de despliegue en servidor Windows aún no forma parte de este README y será documentada posteriormente

## 📋 Backlog / Pendientes

* **Módulo de carga documental**: actualmente en standby, pendiente de definición funcional con usuarios reales y flujo de proceso
* Definir si un mismo usuario podrá buscar y cargar desde una misma cuenta
* Definir si carga y búsqueda vivirán en el mismo contexto o en módulos separados
* Definir política de duplicados, nomenclatura, validación real de PDF, estrategia de indexación y auditoría de carga
* Documentar despliegue productivo en servidor Windows
* Documentar estrategia de ejecución con Waitress en fase posterior
---
Desarrollado por **Josting Silva**  
Analista Programador – Unidad de TICs  
Departamento de Salud, Municipalidad de Alto Hospicio
