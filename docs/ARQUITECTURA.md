# Arquitectura y decisiones

## Estado actual de los módulos

Las fases 1 y 2 están implementadas. `catalog.py` y `routines.py` se registran como Blueprints sobre cada proceso Flask, compartiendo identidad y la base SQLite. La migración 002 crea catálogo, solicitudes/resoluciones, notas privadas, rutinas/versiones/días/elementos, asignaciones y planificación. Los endpoints HTML y API tienen identificadores distintos para que `url_for` no genere direcciones JSON en la navegación del usuario. Las pruebas verifican tanto los permisos de la API como el destino y formato final de las redirecciones de formularios. Consultar ESTADO.md para resultados y límites actuales; las secciones de diseño incremental siguientes conservan la intención de las fases futuras.

## Entorno inspeccionado

Windows 10 build 19045, x64, PowerShell 5.1, Python 3.11.2, Node 18.14.2. No WSL, Docker ni SDK .NET. Carpeta inicialmente vacía y sin Git. No se encontraron AGENTS.md en el proyecto ni en los antecesores consultados mediante sus rutas concretas.

## Fase 1

Python 3.11 + Flask 3.1.2 + Waitress 3.0.2: servidor nativo Windows sin compilador ni frontend dependiente de Node. SQLite con claves foráneas, WAL, timeout y migración versionada: adecuado para un único servidor y pocos usuarios concurrentes. Cada petición tiene su conexión; las operaciones sensibles usan transacciones. Waitress ejecuta un proceso de entrenamiento (8080) y uno de consola (8081), ambos en loopback, con el mismo almacén de identidad. Detener entrenamiento no detiene la consola. El controlador HTTP para operar servicios no está implementado en esta fase.

Identidad: UUID estable de usuario, perfil TOP/normal, estado y revisión; hashes Argon2id; sesiones aleatorias de 384 bits guardadas por hash, CSRF independiente por sesión, caducidad absoluta de 12 h. Invitaciones de 256 bits, hash, 24 h, un solo uso. Bloqueo de login después de cinco fallos por cuenta o IP durante 15 minutos, persistido y compartido entre procesos. CSRF también protege acceso y activación. Cookies HttpOnly, SameSite Strict y Secure en producción; CSP, no-store, sin cargas multimedia ni scripts externos. No se acepta un rol o ID de usuario del navegador para decidir permisos. La cuenta activa se consulta en cada petición. Desactivar, restablecer o cambiar perfil revoca sesiones. Se protege el último TOP con transacción de escritura.

La auditoría solo contiene actor, acción, identificador objetivo y fecha; no cuerpos de peticiones, claves, invitaciones ni mediciones. Las pantallas se generan con escape de Jinja. No hay registro público, correo automático, shell remota ni carga de ficheros.

## Modelo incremental previsto (no tablas implementadas aún)

- Catálogo: machines (UUID, pegatina única entre activas, estado, creador), exercises, exercise_equipment, machine_requests, request_resolutions y aliases de máquina. Vincular referencias en transacción conservando resolución y contexto histórico.
- Notas privadas: owner_id y objeto, repositorio separado sin endpoints administrativos.
- Rutinas: routines, routine_versions inmutables, weekdays, prescribed_sets, assignments y planning_intervals. Validación de intervalos inclusivos, elección explícita ante solapamiento. Copia personal con UUID y versión independientes.
- Entrenamiento: sessions (owner, fecha real, rutina/día origen, estado, revisión), session_exercises con snapshot y contexto de equipo/carga, sets con previsto y realizado por separado, substitutions, activities y rest_events independientes. Finalizar no exige completar todo.
- Privacidad: body_measurements separado, solo propietario; altura en perfil privado, nunca en DTO administrativos. No hay endpoints de estos datos en fase 1: su ausencia no sustituye las pruebas de privacidad cuando se implementen.
- Preferencias: timezone Europe/Madrid, recordatorios, permisos push, suscripciones.
- Offline: UUID generado en cliente, operation_id único por usuario, payload/version, resultado confirmado por servidor. IndexedDB por cuenta. Conflicto de revisión devuelve 409 y requiere resolución explícita; no implementar last-write-wins silencioso. Snapshots de rutinas/sesiones desde el principio de su fase. No caché de respuestas autenticadas en un service worker hasta tener aislamiento de cuentas probado.

## Orden y límites

1. Identidad, migración, TOP y administración mínima (esta entrega).
2. Catálogo real vacío; propuestas privadas, aprobación/vinculación; rutinas/versiones, asignación/copia y planificación.
3. Hoy, sesiones editables, actividad libre, series confirmadas, historial por ejercicio/equipo y temporizador con marcas temporales.
4. Calendario, estadísticas, medidas privadas y notificaciones opcionales.
5. PWA/offline, sincronización idempotente, controlador de servicios con operaciones fijas, copias automáticas, restauración y recuperación.

La primera prueba completa TOP → máquina → rutina → usuario → sesión se realizará tras la fase 3. No se considera satisfecha ahora. El servidor de consola no deberá dar acceso a comandos genéricos; un componente de privilegios mínimos solo podrá operar los servicios Trofollos concretos. Restauración con confirmación, entrenamiento detenido y copia previa.

## Fuentes oficiales verificadas

- https://flask.palletsprojects.com/en/stable/installation/ (Python >=3.9)
- https://flask.palletsprojects.com/en/stable/deploying/waitress/ (Windows nativo)
- https://argon2-cffi.readthedocs.io/en/stable/api.html (Argon2id y actualización de hash)

Supuestos: un solo servidor, un gimnasio, pocos usuarios, sin dominio/red públicos disponibles. No se inventan datos del gimnasio. Producción fuera de OneDrive y de la carpeta de código. No se integra ninguna API de IA.
