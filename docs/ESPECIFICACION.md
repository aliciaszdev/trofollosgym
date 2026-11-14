Eres Codex, trabajando desde la extensión de Visual Studio Code en mi ordenador Windows. Ese mismo ordenador será después el servidor de TrofollosGym. Actúa como desarrollador full stack y construye en la carpeta de trabajo abierta una aplicación real para gestionar entrenamientos en el gimnasio REVENGE de Colmenar Viejo.

Construye un MVP funcional por fases, con persistencia real, instalación en un servidor doméstico Windows y acceso por internet. El resultado debe permitir que varias personas utilicen sus propias cuentas desde el navegador del móvil. No te limites a una maqueta.

## 1. Forma de trabajar y decisiones de alcance

### Entorno de trabajo: Codex en Visual Studio Code sobre Windows

- Trabaja directamente con los archivos de la carpeta abierta en Visual Studio Code. Inspecciona primero su contenido, las instrucciones AGENTS.md aplicables y el estado del repositorio. Conserva el trabajo existente; si ya hay una implementación, adáptala antes de crear otra.
- Crea y modifica los archivos reales, ejecuta los comandos de desarrollo que tengas disponibles y comprueba el resultado. No te limites a responder con bloques de código para que yo los copie.
- Comprueba Windows, arquitectura, terminal, herramientas y versiones instaladas antes de elegir dependencias. Utiliza comandos adecuados para PowerShell en el equipo Windows.
- Si Codex está ejecutándose mediante WSL, identifica esa diferencia expresamente: el entorno del agente no debe confundirse con el destino final. Mantén el despliegue compatible con Windows nativo y documenta cualquier paso que deba ejecutarse desde PowerShell.
- Prioriza una instalación nativa en Windows. No conviertas Docker, WSL o una máquina virtual en requisitos obligatorios sin justificar una necesidad concreta.
- El funcionamiento habitual del servidor será independiente de Visual Studio Code y de la sesión de Codex. Cerrar el editor no debe detener la aplicación instalada como servicio.
- Prepara scripts reproducibles de PowerShell para las tareas necesarias de desarrollo, instalación y operación. Documenta qué tareas requieren privilegios de administrador y por qué; el servicio de entrenamiento debe funcionar con los permisos mínimos necesarios.
- La base de datos, las copias y la configuración de producción se guardarán en ubicaciones persistentes, separadas de carpetas temporales, compilaciones y datos de prueba. Una actualización de código no debe borrar información.
- Distingue configuración de desarrollo y producción, aunque ambas estén en el mismo ordenador. Los tests no deben utilizar ni reiniciar la base de datos real.
- No presupongas dominio, dirección pública, acceso al router ni una topología de red concreta. Avanza en todo lo local y documenta de forma concreta los datos o pasos externos que falten para el acceso por internet.
- TrofollosGym no necesita integrar modelos de IA ni una API de OpenAI para cumplir esta especificación. Codex es la herramienta de desarrollo.
- Guarda la especificación, la arquitectura y el estado de las fases en documentación del proyecto para poder continuar en otra sesión. Actualiza lo completado, los resultados de comprobación y lo pendiente.
- Al terminar cada fase, resume qué archivos cambiaste, cómo arrancar y probar el resultado, qué pruebas ejecutaste y qué falta. Si no puedes ejecutar una comprobación, indícalo claramente.


- Utiliza esta especificación como fuente de requisitos.
- Antes de programar, revisa el entorno y presenta brevemente la arquitectura, el modelo de datos, las fases y los supuestos.
- Elige una solución mantenible y sencilla de instalar en Windows. Justifica las decisiones técnicas y utiliza documentación oficial vigente para verificar dependencias y compatibilidad.
- No impongas servicios de pago, alojamiento externo ni una aplicación de tienda.
- Resuelve decisiones menores con criterios razonables y documenta los supuestos. Pregunta solo por bloqueos reales.
- Desarrolla por fases comprobables y conserva el trabajo entre fases.
- No sustituyas funciones por botones decorativos ni declares funcionalidades terminadas sin probarlas.
- Los datos de ejemplo estarán separados de los datos reales. No inventes el catálogo real de REVENGE.
- La primera versión es para un único gimnasio. No incluye gestión comercial de centros, pagos, alimentación, red social ni generación de rutinas con IA.

## 2. Arquitectura y alojamiento

Habrá dos áreas: la aplicación de entrenamiento y una consola de administración. Ambas serán accesibles por internet mediante HTTPS y compartirán el sistema de identidad.

El servidor de casa utiliza Windows. Los datos definitivos se guardarán en su base de datos y persistirán tras reinicios. La instalación tendrá arranque automático y configuración mediante variables o archivos externos al código.

El control del servicio de entrenamiento debe funcionar como un servicio independiente: detener la aplicación de gimnasio no puede impedir acceder a la consola para volver a iniciarla. El controlador expondrá únicamente operaciones concretas sobre los servicios de TrofollosGym; nunca una terminal o ejecución arbitraria de comandos.

Si el ordenador se apaga o pierde internet, la consola remota no estará disponible. La app podrá mantener las funciones offline previamente descargadas.

Documenta la configuración necesaria de acceso exterior, dominio o dirección pública y HTTPS. No supongas que el entorno de desarrollo ya equivale al despliegue en casa.

## 3. Usuarios y permisos

Solo existen dos perfiles: TOP y normal. Una cuenta TOP también funciona como una cuenta de entrenamiento normal. Dentro de su sesión puede alternar entre «Mi entrenamiento» y «Administración».

No habrá registro público. El TOP creará las cuentas desde la consola, asignará el perfil, podrá desactivarlas sin borrar su historial y restablecer su acceso. Utiliza un procedimiento seguro para que el usuario establezca o cambie su contraseña inicial. Documenta cómo crear el primer TOP.

Usuarios normales:
- Acceder a sus rutinas, sesiones, calendario y progreso.
- Consultar el catálogo aprobado.
- Proponer máquinas y utilizarlas provisionalmente.
- Crear y editar sus propias rutinas privadas.
- Seguir las rutinas del TOP que tengan disponibles y copiarlas como propias.
- Registrar sus propios datos corporales.

TOP:
- Todas las funciones de usuario normal.
- Gestionar cuentas y permisos.
- Crear y mantener máquinas y ejercicios del catálogo.
- Revisar solicitudes de máquinas.
- Crear, publicar y asignar rutinas.
- Consultar el historial y rendimiento de entrenamiento de los usuarios.
- Gestionar el estado del servidor y las copias de seguridad.

El TOP no puede modificar los registros de entrenamiento ajenos por el mero hecho de poder consultarlos.

## 4. Privacidad y seguridad del MVP

Los pesos corporales, las medidas y sus gráficas son privados de cada usuario. El TOP no podrá consultarlos desde la app, la consola, las exportaciones administrativas ni las API. Estas restricciones se aplicarán en el servidor, no solo ocultando elementos de la interfaz.

El TOP sí puede consultar sesiones, ejercicios, series, repeticiones, cargas, fechas, notas de sesión y evolución del rendimiento. Distingue siempre «peso corporal» de «peso utilizado en un ejercicio».

Las notas personales permanentes sobre ajustes de una máquina son privadas. Las notas del entrenamiento son visibles para el TOP.

El MVP utiliza usuario y contraseña, sin verificación en dos pasos. Incluye HTTPS, contraseñas con hash adecuado, sesiones protegidas, validación de entradas, autorización por objeto y protección frente a intentos repetidos de acceso. No incluyas contraseñas ni datos corporales en los logs.

Los backups tendrán acceso restringido. Documenta que la privacidad por permisos de la aplicación no equivale a ocultar los datos frente al propietario técnico de la base de datos o sus copias.

## 5. Catálogo de máquinas y ejercicios

Toda la aplicación utiliza un catálogo de REVENGE de Colmenar Viejo.

Las fichas son exclusivamente de texto. No incluir fotos, vídeos ni cargas de contenido multimedia.

Campos de máquina:
- Identificador interno estable.
- Nombre.
- Número de la pegatina del gimnasio, opcional y único entre máquinas activas cuando exista.
- Ubicación o zona, opcional.
- Marca y modelo, opcionales.
- Descripción e instrucciones breves.
- Estado: provisional, aprobada o archivada.

Los ejercicios tendrán nombre, descripción, músculos trabajados y tipo de material: máquina, polea, barra, mancuernas, peso corporal u otro.

Separa máquina física de ejercicio: una máquina puede admitir varios ejercicios y un ejercicio puede realizarse con distinto equipamiento. Guarda el contexto concreto utilizado para comparar resultados correctamente.

Permite buscar por nombre y número. Muestra el número de pegatina de forma destacada en las rutinas y sesiones. Los ejercicios sin máquina no necesitan número.

Cada usuario puede guardar ajustes personales asociados a una máquina, como «asiento en posición 4».

## 6. Solicitudes y validación de máquinas

Antes de proponer una máquina, muestra coincidencias por número y nombre.

Si el usuario no encuentra la máquina:
1. Envía una propuesta con los campos de texto disponibles.
2. La solicitud queda pendiente.
3. La máquina provisional es visible para su creador y el TOP.
4. El creador puede incorporarla inmediatamente a sus rutinas y entrenamientos.

El TOP puede:
- Aprobar: incorporar la máquina al catálogo común.
- Vincular con una existente: resolver un duplicado.
- Rechazar: indicar el motivo.
- Solicitar información adicional.

El usuario ve el estado y la resolución en la app. Si tiene notificaciones habilitadas, avísale mediante los canales compatibles.

Una aprobación conservará todos los registros. Una vinculación actualizará las referencias sin borrar ni duplicar las rutinas o sesiones y conservará la trazabilidad. Una resolución nunca destruye entrenamientos ya registrados.

Como criterio del MVP, una propuesta rechazada queda fuera del catálogo común, conservando su historial y su referencia privada; el usuario puede corregirla o sustituirla. Las máquinas creadas directamente por el TOP quedan aprobadas.

## 7. Rutinas y planificación

Una rutina tendrá:
- Nombre, por ejemplo «Rutina noviembre».
- Propietario.
- Fecha desde.
- Fecha hasta opcional, interpretada como vigencia indefinida si está vacía.
- Plan por días de la semana.
- Días de entrenamiento y días de descanso.
- Ejercicios, series, repeticiones previstas y descanso configurable por ejercicio.

Ejemplo: lunes pierna, martes espalda, miércoles pecho, jueves descanso y viernes cuerpo completo.

Utiliza Europe/Madrid como zona horaria inicial para el check-in, el calendario y la planificación. Las fechas de vigencia son inclusivas. El número de series es configurable y las repeticiones previstas se pueden definir por serie, con una acción para aplicar el mismo valor a todas.

Las rutinas del TOP pueden publicarse para todos o asignarse a usuarios concretos. Publicar una rutina no la activa automáticamente en la planificación personal de todos.

Para evitar ambigüedades, permite seleccionar una planificación activa por usuario para cada fecha y resuelve explícitamente los solapamientos, sin elegir una rutina de forma silenciosa.

## 8. Rutinas del TOP y copias personales

El usuario puede seguir una rutina del TOP, pero no editar su estructura original.

Incluye «Copiar a mis rutinas»: crea una copia personal editable e independiente. Los cambios posteriores del TOP no se aplican a esa copia.

La modificación de una rutina nunca reescribe sesiones históricas. Guarda una instantánea de lo previsto al iniciar cada sesión o un mecanismo equivalente de versionado.

Las rutinas de un usuario normal son privadas en el MVP. Cambiar una sesión concreta no modifica la rutina base. En una rutina propia, ofrece guardar explícitamente un cambio para futuras sesiones, separándolo de los cambios de hoy.

## 9. Check-in diario

La pantalla «Hoy» siempre permite decidir qué hacer:

Si toca entrenar:
- Opción principal: iniciar el entrenamiento previsto.
- Alternativas: entrenamiento libre, entrenamiento de otro día o marcar descanso.

Si toca descanso:
- Opción principal: iniciar entrenamiento libre.
- Alternativas: elegir entrenamiento de otro día o confirmar descanso.

Si no hay rutina vigente:
- Ofrecer entrenamiento libre o seleccionar una rutina disponible para planificar.

La app detecta la fecha y propone lo correspondiente, sin imponerlo. Si el usuario adelantó ayer la sesión de hoy, muestra ese antecedente, pero sigue permitiendo elegir libremente. Nunca cambies automáticamente los días futuros.

Las sesiones se registran en la fecha real y mantienen la referencia a la rutina y al día de origen. Se pueden realizar varias sesiones en una misma fecha.

## 10. Registro y adaptación de una sesión

Al iniciar una sesión de rutina, crea una instancia personal con los ejercicios y valores previstos.

No hay un orden obligatorio. El usuario puede elegir cualquier ejercicio, dejarlo a medias y volver después.

Durante cualquier sesión, incluso procedente del TOP, permite:
- Añadir ejercicios o actividades extra.
- Sustituir un ejercicio, por ejemplo por avería.
- Modificar las series, repeticiones y cargas de esa sesión.
- Añadir series.
- Omitir ejercicios o series por falta de tiempo.
- Anotar opcionalmente el motivo de una sustitución u omisión.
- Finalizar una sesión aunque no haya completado todos los ejercicios previstos.

Conserva las series ya registradas. Distingue previsto, realizado, añadido, sustituido y omitido. Adaptar el entrenamiento del día no modifica la rutina del TOP.

Cada serie registra número, repeticiones previstas, repeticiones realizadas, peso utilizado y estado. Las repeticiones previstas aparecen por defecto y se pueden corregir para reflejar lo realizado. Una serie no se considera completada hasta que el usuario la confirme.

Usa kg, cm, km y minutos como unidades iniciales. Admite ejercicios de peso corporal sin obligar a introducir una carga ficticia.

Autoguarda el trabajo y permite retomar la sesión después de bloquear el móvil, cerrar la ventana o recargar la página.

## 11. Última sesión y evolución de cargas

Al abrir un ejercicio, muestra la fecha y las series realizadas por ese usuario la última vez que completó ese mismo ejercicio con ese equipamiento, aunque perteneciera a otra rutina.

Ejemplo:
- Serie 1: 12 repeticiones con 20 kg.
- Serie 2: 10 repeticiones con 25 kg.
- Serie 3: 8 repeticiones con 25 kg.

Debajo aparecen las series de hoy.

Incluye «Copiar valores de la última sesión». La copia solo rellena valores: nunca marca las series como completadas. Trata correctamente cantidades de series diferentes y no mezcles ejercicios distintos que usen la misma máquina.

Si no hay historial, muestra un mensaje claro y los valores previstos de la rutina.

Incluye historial y gráficas sencillas de cargas y repeticiones por ejercicio, frecuencia y sesiones realizadas. Evita confundir cargas asistidas o equipamientos diferentes.

## 12. Descansos y notas

Temporizador opcional, activable y desactivable durante la sesión.

Cada ejercicio puede tener un descanso previsto. Si está habilitado, empieza al completar una serie. Permite cancelarlo, pausarlo, reanudarlo y sumar tiempo. Llegar a cero avisa, pero no inicia ni completa otra serie.

Calcula el tiempo con marcas temporales para recuperarlo al volver de un bloqueo o de una pestaña en segundo plano. Explica los límites de avisos y sonidos en cada plataforma.

Notas:
- Personales permanentes de máquina o ejercicio: privadas.
- De sesión o ejercicio en una fecha: visibles también para el TOP.

## 13. Entrenamiento libre y otras actividades

Permite iniciar una sesión libre cualquier día y añadir actividades sobre la marcha.

Incluye máquinas, peso libre, peso corporal, paseo, carrera, bicicleta y una actividad genérica.

Utiliza campos apropiados: series, repeticiones y carga para fuerza; duración y distancia opcional para caminar, correr o bicicleta. No obligues a registrar series para una actividad de paseo.

Todo queda guardado en el historial y en el calendario. Un extra dentro de una sesión de rutina se refleja como extra; una sesión libre independiente se muestra como tal.

## 14. Calendario

Incluye vista mensual y semanal, navegación entre fechas, hoy resaltado y leyenda.

Representa claramente:
- Verde: sesión de rutina finalizada.
- Azul: sesión libre finalizada.
- Naranja: sesión iniciada que sigue abierta.
- Gris: descanso confirmado.
- Sin relleno: sin registros.

Diferencia planificación de resultados: los días futuros y los descansos previstos llevan indicadores discretos, nunca apariencia de actividad realizada.

Si no hay registros, no afirmes que el usuario faltó o no hizo actividad. Si finaliza un entrenamiento con ejercicios omitidos, cuenta como sesión realizada. El naranja indica una sesión abierta, no un entrenamiento imperfecto.

Si coinciden varios estados o sesiones, muestra varios indicadores sin ocultar actividad ni depender exclusivamente del color. Conserva el descanso confirmado como evento independiente si después se añade actividad, mostrando lo ocurrido.

Al tocar una fecha, muestra lo previsto y lo realizado, con detalles de sesiones, series, cargas, notas y modificaciones. Permite añadir y corregir registros propios de fechas anteriores y actualiza las estadísticas.

## 15. Peso corporal y medidas

Registro libre, sin frecuencia obligatoria.

Cada entrada tiene fecha editable y campos opcionales:
- Peso corporal.
- Cintura y abdomen.
- Cadera.
- Pecho.
- Brazo.
- Muslo.
- Pantorrilla.

La altura se guarda en el perfil. No es obligatorio completar todas las medidas. Permite editar y eliminar registros propios, introducir mediciones anteriores, consultar el historial y ver gráficas y comparaciones entre fechas.

Mantén estos datos separados del historial de entrenamiento y excluidos de todas las vistas administrativas del TOP.

## 16. Notificaciones

Cada usuario puede activar o desactivar recordatorios de peso, medidas o ambos, eligiendo días y hora. No hay recordatorios obligatorios.

Las notificaciones del navegador requieren su autorización correspondiente. Las preferencias internas no sustituyen ese permiso.

Ofrece avisos internos y notificaciones push donde sean compatibles. Documenta requisitos y limitaciones reales según navegador y sistema, incluyendo cualquier necesidad de instalación en pantalla de inicio. No prometas avisos con la app cerrada si la plataforma no los admite.

Distingue recordatorios, resolución de solicitudes y avisos de funcionamiento. Si el usuario rechaza permisos, el resto de la app sigue funcionando.

## 17. PWA y funcionamiento sin conexión

App responsive, priorizada para móvil, utilizable también en ordenador y añadible a la pantalla de inicio como PWA en dispositivos compatibles.

Al conectarse, guarda lo necesario para entrenar sin conexión: estructura de la app, rutinas disponibles descargadas, catálogo necesario y últimos resultados personales.

Sin conexión, permite consultar lo descargado, iniciar o continuar sesiones, registrar series, notas, extras y actividades. Los elementos nuevos se guardan localmente y se envían después con las restricciones de validación y permisos habituales.

Incluye:
- Guardado local automático.
- Indicador «Sin conexión · cambios pendientes», «Sincronizando» y «Todo sincronizado».
- Identificadores estables y operaciones idempotentes para evitar duplicados.
- Reintentos y confirmación del servidor antes de dar un dato por sincronizado.
- Política explícita de conflictos; no sobrescribir silenciosamente registros ni cambios de rutinas.
- Aislamiento local entre usuarios y limpieza o bloqueo de datos al cambiar de cuenta.
- Advertencia y opciones seguras si se intenta cerrar sesión con cambios pendientes.
- Recuperación de sesiones interrumpidas.

La primera entrada y la descarga de contenido nuevo necesitan conexión. El guardado normal del navegador no requiere acceso a carpetas del dispositivo. Solicita almacenamiento persistente cuando sea compatible y útil.

No garantices conservación absoluta: borrar los datos del sitio o el almacenamiento del navegador puede eliminar lo pendiente. No dependas de sincronización en segundo plano; garantiza reintento con la app abierta o al volver a abrirla con conexión y aprovecha funciones de segundo plano solo cuando estén disponibles.

Las operaciones administrativas y el acceso a datos nuevos del servidor requieren conexión.

## 18. Consola de administración

Área exclusiva del TOP, accesible desde casa y desde fuera:
- Estado del servicio de entrenamiento y de la base de datos.
- Iniciar, detener y reiniciar el servicio de entrenamiento.
- Errores recientes y logs sin datos privados.
- Usuarios: alta, perfil, desactivación y restablecimiento de acceso.
- Máquinas y solicitudes pendientes.
- Rutinas publicadas y asignadas.
- Consulta del historial de entrenamiento de usuarios.
- Creación, estado y restauración de backups.

Implementa copias automáticas configurables y copia manual, con estado visible y retención documentada. La restauración requiere confirmación explícita y debe poder ejecutarse con la app de gimnasio detenida.

Mantén protegido el acceso administrativo y solicita confirmación para acciones destructivas. Evita borrar definitivamente datos referenciados: prioriza archivado o desactivación. Impide dejar el sistema sin ninguna cuenta TOP activa.

## 19. Diseño de TrofollosGym

Idioma inicial: español de España. Estética Material Design, modo claro, moderna, sencilla, limpia y cómoda de usar durante el ejercicio.

Paleta:
- Azul principal: #1565C0.
- Blanco de tarjetas y formularios: #FFFFFF.
- Fondo general: #F5F8FC.
- Selecciones suaves: #E3F2FD.
- Texto principal: #172B4D.
- Verde para confirmaciones y actividad completada.
- Rojo para errores, rechazo y acciones destructivas.
- Naranja o amarillo para avisos y pendientes.
- Gris para estados neutros y descanso.

Usa colores de estado con contraste suficiente, etiquetas e iconos. El azul identifica acciones principales; en el calendario también identifica sesiones libres, siempre con leyenda.

Botones grandes, tipografía legible, espacios cómodos, bordes redondeados, sombras discretas y animaciones suaves que respeten la preferencia de movimiento reducido. Campos numéricos cómodos, compatibles con coma decimal y teclado móvil apropiado.

Pantallas principales:
- Inicio de sesión.
- Hoy y check-in.
- Entrenamiento en curso.
- Rutinas y planificación.
- Catálogo de máquinas y ejercicios.
- Calendario.
- Progreso de entrenamiento.
- Mi seguimiento corporal.
- Perfil y preferencias.
- Administración TOP.

Navegación inferior propuesta: Hoy, Rutinas, Catálogo y Progreso. Calendario tendrá un acceso directo y visible desde Hoy. Perfil y ajustes estarán accesibles desde la cabecera. Mantén accesibles los estados de carga, vacío, error y conexión.

No incluyas fotos ni vídeos en las fichas ni contenido decorativo que dificulte registrar un entrenamiento.

## 20. Datos, fases y entregables

Modela al menos usuarios, perfiles, máquinas físicas, ejercicios, solicitudes, resoluciones, notas privadas, rutinas y sus versiones, planificación y asignaciones, sesiones, ejercicios de sesión, series, sustituciones, actividades, descansos confirmados, mediciones privadas, preferencias y operaciones de sincronización.

Orden de construcción:
1. Windows, persistencia, identidad, permisos y administración mínima.
2. Catálogo, aprobación de máquinas, rutinas y asignaciones.
3. Check-in y entrenamiento completo con historial previo y temporizador.
4. Calendario, progreso, mediciones y notificaciones.
5. PWA, offline, sincronización, consola operativa y recuperación.

Diseña la identidad de datos, las instantáneas históricas, la separación del controlador y la sincronización desde el principio, aunque completes su interfaz en fases posteriores.

Primera prueba de extremo a extremo: el TOP crea un usuario, añade una máquina y asigna una rutina; el usuario entra desde el móvil, inicia la sesión, registra series y puede consultar esos datos después.

Entrega:
- Código organizado y configuración de ejemplo sin secretos.
- Migraciones de base de datos.
- Instrucciones reproducibles de desarrollo en Visual Studio Code y de instalación, actualización y arranque del servidor en este mismo ordenador Windows.
- Scripts PowerShell para configurar el entorno, iniciar el desarrollo, instalar los servicios y consultar su estado, con las operaciones de backup y restauración documentadas.
- Procedimiento de primer TOP y acceso exterior con HTTPS.
- Guía de backup y restauración.
- Pruebas de los flujos críticos y resumen de resultados.
- Relación honesta de limitaciones o funciones pendientes.

## 21. Criterios de aceptación

Comprueba al menos:
1. Un usuario normal no accede a administración ni a datos de otro usuario.
2. El TOP consulta entrenamientos ajenos, pero no peso corporal, medidas ni notas privadas, tampoco mediante llamadas directas a la API.
3. Una máquina provisional se utiliza y después se aprueba o vincula sin perder sesiones.
4. El usuario no edita la rutina del TOP; una copia personal sí es editable e independiente.
5. Las fechas y días de la planificación determinan la propuesta de Hoy.
6. Se puede elegir rutina de otro día, sesión libre o descanso sin alterar el plan futuro.
7. Cambiar orden, añadir, sustituir u omitir ejercicios afecta solo a la sesión salvo guardado explícito en una rutina propia.
8. El historial previo compara el mismo ejercicio y equipamiento y copiar valores no completa series.
9. El temporizador se cancela, pausa y amplía y recupera correctamente el tiempo transcurrido.
10. El calendario diferencia actividad, sesión abierta, descanso confirmado y ausencia de registros y representa varias sesiones.
11. Las mediciones son opcionales, editables y privadas.
12. Un entrenamiento continúa offline tras haber descargado lo necesario, se recupera al reabrir y se sincroniza sin duplicados.
13. Los datos locales de una cuenta no aparecen al entrar con otra.
14. Una restauración recupera datos reales y el controlador permite arrancar la app detenida.
15. Los datos persisten tras reiniciar Windows.
16. La interfaz funciona en móvil y ordenador y los estados se entienden sin depender solo del color.
17. Rechazar permisos de notificación no bloquea entrenar.
18. Las acciones y botones principales realizan operaciones reales y muestran su resultado.

Empieza inspeccionando la carpeta abierta en Visual Studio Code y las herramientas disponibles. Presenta una arquitectura breve adaptada al Windows de este ordenador y los supuestos, y después implementa y verifica la primera fase con archivos y comandos reales. No termines solo con una propuesta. Deja el proyecto arrancable localmente, informa de la dirección local y documenta los pasos precisos para continuar con las demás fases. Mantén esta especificación como referencia.
