# TrofollosGym

> Solo para Trofollos con mucho IMC

MVP para REVENGE, Colmenar Viejo. **Fases 1 y 2 implementadas**: identidad, administración de usuarios, catálogo, solicitudes de máquinas, notas privadas, rutinas versionadas, publicación/asignación y planificación personal. El registro de sesiones y series aún no está disponible (fase 3). Especificación completa: [docs/ESPECIFICACION.md](docs/ESPECIFICACION.md).

Repositorio: https://github.com/aliciaszdev/trofollosgym · rama `main`. Se conservó el commit inicial existente como base. Git solo incluye código, migraciones, pruebas y documentación; las cuentas, sesiones, datos de gimnasio y copias locales están excluidos.

## Arranque local en PowerShell

En este equipo la política de PowerShell bloquea los archivos `.ps1`. Sin cambiar esa política, utiliza estos comandos directos (las dependencias ya están instaladas):

```powershell
.\.venv\Scripts\python.exe -m trofollos.app bootstrap --username top
.\.venv\Scripts\python.exe -m trofollos.app serve --area training --port 8080
```

En otra terminal: `.\.venv\Scripts\python.exe -m trofollos.app serve --area admin --port 8081`. Para probar: `.\.venv\Scripts\python.exe -m pytest -q`. Ambos servidores se han dejado arrancados en esta entrega; no los dupliques en los mismos puertos. Para una instalación limpia: `python -m venv .venv` seguido de `.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`. El comando bootstrap solo se utiliza en instalaciones sin cuentas; en este ordenador el usuario TOP ya existe.

Los scripts equivalentes están preparados para un entorno que permita ejecutar `.ps1`:

```powershell
.\scripts\Setup.ps1
.\scripts\First-Top.ps1 -Username top
.\scripts\Start-Dev.ps1 -Area training
```

En otra terminal:

```powershell
.\scripts\Start-Dev.ps1 -Area admin
```

- Entrenamiento: http://127.0.0.1:8080
- Consola: http://127.0.0.1:8081
- Establecer contraseña: http://127.0.0.1:8080/activate

El comando First-Top muestra un código de un solo uso de 24 horas. Introducirlo en «Establecer contraseña» y elegir una contraseña propia de al menos 12 caracteres. No hay credenciales predeterminadas. No ejecutar con transcripción de terminal ni compartir el código públicamente. Las dos áreas locales comparten sesión mediante la cookie del mismo host; usar siempre `127.0.0.1`, sin mezclarlo con `localhost`.

La ejecución local escucha solo en loopback y usa HTTP, exclusivamente para desarrollo. No permite todavía entrar desde el móvil por la red. No abrir estos puertos al router. Ver [operación Windows y HTTPS](docs/OPERACION.md).

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\scripts\Test.ps1
.\scripts\Status.ps1
```

Las pruebas usan bases temporales independientes. Setup instala solo dependencias de ejecución; el lock incluye también pytest y las dependencias transitivas verificadas. Si PowerShell bloquea scripts, revisar la política de la organización; se pueden ejecutar directamente los comandos Python equivalentes de los scripts, sin cambiar políticas globales.

Código: `trofollos/app.py` (identidad), `trofollos/catalog.py`, `trofollos/routines.py`, plantillas y CSS en `trofollos/`; migraciones 001 y 002 en `migrations/`; automatización en `scripts/`; pruebas en `tests/`. Datos de desarrollo en `.runtime/development/identity.sqlite3`, ignorados por Git.

## Catálogo y rutinas

Con tu cuenta TOP, abre **Catálogo** para añadir las máquinas y los ejercicios reales. Son entidades distintas: se crea el ejercicio y se selecciona su equipamiento concreto al añadirlo a una rutina. Una rutina comienza con siete días de descanso; en cada día se pueden añadir ejercicios, configurar series, repeticiones por serie y descansos.

En la ficha de una rutina TOP puedes publicarla para todos o asignarla a usuarios concretos. Eso no cambia su planificación: cada usuario elige fechas en **Mi plan**. La pantalla **Hoy** muestra lo previsto en Europe/Madrid; todavía no permite registrar entrenamiento.

Los usuarios normales pueden proponer máquinas privadas y usarlas en sus propias rutinas, seguir rutinas compartidas y crear copias independientes. El TOP resuelve las propuestas desde **Solicitudes de máquinas**. Los ajustes personales de una máquina solo los consulta su propietario.

Las páginas del navegador usan `/catalog`, `/machines/...`, `/routines/...`, `/planning` y `/today`. Las direcciones `/api/...` son técnicas y muestran JSON. Se corrigieron los enlaces y redirecciones que confundían ambos destinos; las pruebas siguen ahora la redirección completa de los formularios y comprueban que termina en HTML.

Resultado actual: **32 pruebas superadas**. Si tienes abierta una respuesta JSON de una versión anterior, abre http://127.0.0.1:8080/routines o http://127.0.0.1:8080/catalog. Los datos previamente guardados se conservan.

Consultar [arquitectura y fases](docs/ARQUITECTURA.md), [estado verificado](docs/ESTADO.md) y [especificación](docs/ESPECIFICACION.md) para continuar en otra sesión.
