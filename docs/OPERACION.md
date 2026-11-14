# Operación Windows

## Desarrollo y producción

Desarrollo: datos en `.runtime/development`, puertos loopback 8080/8081. Cerrar el proceso de desarrollo lo detiene. Producción: dos servicios automáticos independientes y datos fuera del código, por ejemplo `C:\ProgramData\TrofollosGym`. Los tests nunca usan ese directorio. No copiar la base de desarrollo a producción por defecto.

Configurar `TROF_ENV=production`, `TROF_DATABASE` absoluto, `TROF_TRAINING_URL` y `TROF_ADMIN_URL`. No hay archivo de secretos necesario: sesiones e invitaciones se validan contra sus hashes en SQLite. Cada entorno debe tener su propia base. No almacenar en red/OneDrive la base SQLite activa. No ejecutar el servidor Flask de desarrollo para producción.

El Windows detectado y Python 3.11.2 son antiguos: antes de exponer este ordenador, verificar soporte y actualizaciones de seguridad de Windows y actualizar Python a una versión de mantenimiento compatible. No se ha alterado el sistema operativo.

## Servicios (preparado, instalación no ejecutada)

Requiere administrador para registrar servicios, asignar ACL y configurar proxy/firewall. La aplicación debe ejecutarse como LocalService, nunca como administrador.

1. Preparar una ubicación estable de código fuera de OneDrive y de carpetas de usuario privadas; instalar Python para todos los usuarios, crear allí `.venv` e instalar el lock. LocalService necesita lectura/ejecución de Python, entorno virtual, código y migraciones. No conceder escritura sobre el código a la cuenta de servicio.
2. Obtener WinSW 2.x x64 de sus releases oficiales, revisar procedencia y hash. No está incluido ni descargado: https://github.com/winsw/winsw/releases . El script usa el formato oficial https://github.com/winsw/winsw/blob/v2.12.0/doc/xmlConfigFile.md . No usar `sc.exe create` directamente sobre python.exe: Python no implementa el protocolo del Service Control Manager.
3. Desde PowerShell elevado, ejecutar el script real (sustituir todas las rutas y nombres de host):

```powershell
.\scripts\Install-Services.ps1 -WinSW C:\Herramientas\WinSW-x64.exe -DataDirectory C:\ProgramData\TrofollosGym -TrainingUrl https://entreno.TU-DOMINIO/ -AdminUrl https://consola.TU-DOMINIO/
```

El instalador genera dos XML externos y registra servicios con inicio automático; no los arranca. Restringe datos a LocalService, SYSTEM y administradores. Al compartir LocalService con otros servicios, esta cuenta no ofrece aislamiento frente a otros procesos bajo esa misma identidad; valorar cuentas virtuales dedicadas antes de endurecer producción.

4. Conceder lectura/ejecución de la instalación a LocalService. El Python situado actualmente en el perfil de Alicja puede ser inaccesible a esta cuenta; el script no cambia permisos de tu perfil. Para primer TOP de producción, abrir terminal elevada SIN transcripción:

```powershell
$env:TROF_ENV='production'
$env:TROF_DATABASE='C:\ProgramData\TrofollosGym\identity.sqlite3'
.\.venv\Scripts\python.exe -m trofollos.app bootstrap --username top
```

5. Configurar HTTPS y comprobar permisos; iniciar `Start-Service TrofollosAdmin` y `Start-Service TrofollosTraining`. Activar el TOP a través de HTTPS. `Get-Service Trofollos*` y `scripts/Status.ps1` comprueban servicios y HTTP. Reiniciar Windows y comprobar de nuevo antes de dar el despliegue por aceptado. No se ha realizado este reinicio ni instalado servicios en esta entrega.

Los códigos bootstrap caducan a las 24 h. Si caduca el único TOP antes de activarlo, un operador local autorizado deberá emitir una nueva invitación desde una herramienta de recuperación que se añadirá; no borrar una base con datos reales. En la fase actual, activar inmediatamente después de crear el TOP.

## Internet y HTTPS (pendiente de datos externos)

Se necesitan nombres de host controlados por el usuario, DNS, acceso de entrada o una alternativa de túnel, y certificados. No se conocen la IP pública, CGNAT ni permisos del router. No abrir 8080/8081 al exterior. Configurar un proxy HTTPS, por ejemplo Caddy nativo Windows, con dos hosts: entrenamiento → 127.0.0.1:8080 y consola → 127.0.0.1:8081. Ambos deben conservar la raíz `/`, sin prefijos. Usar URLs configuradas en los XML. Dos hosts usan la misma identidad pero requieren inicio de sesión separado (cookies host-only). El proxy también debe tener arranque independiente y automático.

Con dominio público y acceso al router: comprobar si existe IP pública utilizable, apuntar DNS a ella, redirigir 80/443 al proxy y permitir solo esos puertos en firewall. Con CGNAT o sin control del router: elegir y configurar un túnel compatible con HTTPS; no se presupone un proveedor o plan de pago. Los certificados locales autofirmados no equivalen a HTTPS confiable para móviles. La prueba móvil debe hacerse tras configurar el proxy y comprobar certificado y permisos desde una red externa.

El código ignora cabeceras X-Forwarded-* y no permite suplantar IP mediante ellas. Detrás del proxy, el limitador por IP verá loopback: el bloqueo por IP puede afectar a varios usuarios tras cinco fallos. Antes de exposición general, configurar y probar confianza estricta en el proxy y límites por IP real; no aceptar cabeceras arbitrarias desde internet. Deshabilitar registros de cuerpos y cabeceras sensibles en el proxy. Los códigos se envían por POST, nunca por URL.

## Actualización

1. Anunciar mantenimiento. Detener entrenamiento y consola (se evita que la consola escriba durante una actualización de esquema).
2. Hacer backup consistente con SQLite Backup API, no copiar solo `.sqlite3` mientras hay WAL activo.
3. Conservar íntegra la carpeta externa de datos/configuración. Reemplazar código y entorno virtual, manteniendo las rutas de los XML o actualizándolas de manera revisada.
4. Con las variables de producción, ejecutar `python -m trofollos.app migrate` con el Python instalado. Actualmente existen las migraciones 001 (identidad) y 002 (catálogo/rutinas); se aplican las pendientes conservando los datos existentes.
5. Arrancar consola y entrenamiento; revisar `/health`, login y cuentas. No volver a una versión de esquema incompatible sin restauración comprobada.

## Copias y recuperación

La copia automática, retención, interfaz y restauración desde la consola son **fase 5 pendiente**. No hay botones simulados. Por ahora se entrega herramienta local `scripts/Database.ps1`, que usa SQLite Backup API e integrity_check. Requiere seleccionar explícitamente origen y destino. Backups fuera de OneDrive y con ACL restringidas como la base; copia externa cifrada recomendada. Política objetivo: diario, 14 diarios y 8 semanales, aún sin programar.

Para restaurar: detener AMBOS procesos/servicios, comprobar copia, crear respaldo previo con nombre nuevo, restaurar en base nueva y cambiar configuración solo después de comprobar integridad. La herramienta exige `-ConfirmRestore RESTAURAR` y destino inexistente; nunca pisa una base. Arrancar contra el destino restaurado y comprobar cuenta/filas conocidas. No se ha restaurado una base de producción ni hay datos reales.

La privacidad de la aplicación no oculta información al administrador técnico con acceso a SQLite, memoria o copias. Los futuros datos corporales y notas privadas deberán excluirse de cada consulta y exportación administrativa, con pruebas específicas. Una base o backup completo contiene esos datos.
