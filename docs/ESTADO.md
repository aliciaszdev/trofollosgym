# Estado de entrega · 14 de noviembre de 2026

## Fases 1 y 2 implementadas localmente

Identidad: SQLite, migración 001, UUID, Argon2id, cuentas TOP/normal, activación y restablecimiento mediante códigos de un solo uso, CSRF, sesiones revocables y protección del último TOP. Administración y entrenamiento son procesos independientes. La cuenta TOP inicial ya fue creada por el usuario; no volver a ejecutar bootstrap en esta instalación.

Catálogo: migración 002 con máquinas y ejercicios separados, búsqueda por nombre/pegatina, pegatina única entre máquinas activas, archivo sin borrado, propuestas privadas utilizables por su creador, aprobación, rechazo con motivo, información adicional y vinculación de duplicados. La vinculación conserva trazabilidad, notas privadas y referencias originales; actualiza la identidad canónica en los elementos de las rutinas. Todavía no hay tablas de sesiones, por lo que su conservación durante una vinculación deberá verificarse en la fase 3.

Notas de máquina: repositorio por propietario; ni el TOP puede consultar las de otro usuario mediante las rutas implementadas. Tras vincular dos máquinas se conservan las notas propias de ambos orígenes sin mezclarlas entre usuarios.

Rutinas: privadas por defecto, siete días, descanso/entrenamiento, vigencia inclusiva, ejercicios y equipamiento concretos, series con repeticiones por serie o un valor para todas, descanso en segundos, reordenación y archivo. Cada edición crea una versión; las copias son personales e independientes. Las versiones conservan instantáneas de nombres y referencias originales. Una reparación de identidad por vinculación puede actualizar el machine_id canónico de versiones existentes sin alterar esas instantáneas.

El TOP publica para todos o asigna a usuarios concretos. No puede editar rutinas privadas ajenas. Publicar no activa una planificación. Cambiar un TOP a perfil normal se bloquea mientras tenga rutinas compartidas. Se bloquea retirar la disponibilidad o archivar una rutina mientras haya planificaciones que la necesiten.

Planificación personal: intervalos inclusivos, fecha final opcional, revisiones para detectar cambios en otra ventana, confirmación explícita de solapamientos y sustitución solo del tramo elegido, conservando los intervalos anteriores fuera de él. Hoy muestra la propuesta según fecha/día en Europe/Madrid; no registra actividad ni confirma descanso.

## Incidencia corregida: navegador mostrando JSON

Al guardar una máquina o rutina, o seguir ciertos enlaces, Flask generaba la dirección /api/... porque las rutas HTML y API compartían el mismo identificador de endpoint. La creación se guardaba, pero la redirección terminaba mostrando JSON.

Se asignaron identificadores diferentes a las rutas API de catálogo y rutinas. Los endpoints de las páginas generan exclusivamente sus direcciones HTML. Las URLs API siguen disponibles y mantienen sus permisos y formato JSON. No se cambiaron datos ni esquema para esta corrección.

La incidencia se reprodujo antes de corregirla: siete comprobaciones de navegación fallaban, incluida la creación de la máquina con seguimiento completo de la redirección. Tras corregirla pasan todas.

## Comprobaciones ejecutadas

`python -m pytest -q`: **32 passed in 10.59s**.

- Identidad, permisos, revocación, CSRF, intentos repetidos, persistencia y protección del último TOP.
- Privacidad de propuestas y notas frente a otros usuarios y TOP, revisiones obsoletas, resoluciones y conservación de referencias al vincular.
- Rutinas privadas, asignaciones, publicación, copias independientes, versiones, series, cambios de día y archivo.
- Fechas de Hoy, límites inclusivos, descanso previsto, solapamientos y conservación de tramos, aislamiento de planificación y fecha extrema.
- Formularios HTML de catálogo y rutinas con seguimiento de redirecciones; comprobación de tipo HTML, destino fuera de /api y enlaces/formularios sin direcciones API. Las peticiones técnicas siguen devolviendo JSON.
- Migración de una base de fase 1 con conservación de cuentas, migraciones repetidas, integridad, copia/restauración en bases aisladas y rechazo de sobrescritura.

Las pruebas usan bases temporales independientes. No añaden datos de ejemplo a la base real. `python -m compileall -q trofollos` finalizó correctamente.

Los dos procesos se reiniciaron tras la corrección. `/health` en 8080 y 8081 devuelve `ok`; `/login` devuelve 200. La base local conserva las cuentas y el catálogo que el usuario haya introducido. No se ha reiniciado ni borrado para probar.

Antes de aplicar la fase 2 se creó `.runtime/backups/before-phase2-20261114.sqlite3`; esta copia es anterior a los datos de catálogo introducidos posteriormente. No restaurarla para corregir la navegación.

## Archivos principales

- `trofollos/app.py`: identidad, registro de módulos y migraciones.
- `trofollos/catalog.py`: catálogo, propuestas y notas privadas.
- `trofollos/routines.py`: versiones, publicación/asignación, planificación y Hoy.
- `trofollos/validation.py`: validación, revisiones y transacciones.
- `trofollos/templates/base.html`, `catalog.html`, `routines.html`, `page.html` y `static/app.css`.
- `migrations/001_identity.sql` y `002_catalog_routines.sql`.
- `tests/test_identity.py`, `test_catalog_routines.py` y `test_browser_navigation.py`.
- `README.md`, `docs/ARQUITECTURA.md`, `docs/OPERACION.md` y especificación original.

## Pendientes y límites reales

Fase 3: check-in con inicio de sesión, sesión libre, actividades, snapshots de sesiones, registro/confirmación de series, modificaciones de hoy, sustituciones y omisiones, historial previo por ejercicio/equipamiento, temporizador y guardado recuperable. Ejecutar después el primer flujo completo TOP→máquina→rutina→usuario→entrenamiento. Aún no se puede registrar un entrenamiento.

Fase 4: calendario mensual/semanal, progreso, mediciones privadas, altura en perfil y preferencias/notificaciones. Las medidas corporales todavía no están implementadas: sus rutas inexistentes no sustituyen las futuras pruebas de privacidad.

Fase 5: PWA/offline, aislamiento de almacenamiento por cuenta, sincronización idempotente y conflictos, controlador con operaciones fijas de servicios, copias automáticas con retención y restauración desde consola.

Despliegue pendiente: WinSW/LocalService, permisos efectivos, arranque tras reiniciar Windows, dominio/red/router o túnel, proxy y certificados HTTPS. Hay scripts y guía, pero no se han instalado ni probado los servicios. Los procesos actuales son de desarrollo, escuchando solo en 127.0.0.1. Ajustar y probar el limitador por IP detrás del proxy antes de exponerlo.

La política de PowerShell bloquea archivos .ps1; no se cambió. README ofrece comandos Python directos. La recuperación local de un código inicial caducado antes de activar el primer TOP sigue pendiente de herramienta específica.

No se ha realizado verificación visual en Chrome o móvil. La herramienta de control del navegador no estuvo disponible; la alternativa de control nativo fue detenida por no poder determinar con confianza la URL de Chrome. Los tests de navegación usan el cliente HTTP de Flask y no equivalen a una prueba gráfica en navegador real.
