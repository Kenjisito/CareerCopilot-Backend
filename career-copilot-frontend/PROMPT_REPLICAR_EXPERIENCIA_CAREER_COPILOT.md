# Prompt para replicar la experiencia de Career Copilot

## Contexto de la referencia

La referencia es una aplicación de orientación laboral con este recorrido principal:

1. Landing pública con propuesta de valor y acceso a registro o inicio de sesión.
2. Alta o autenticación.
3. Onboarding para crear o completar un perfil profesional.
4. Dashboard con herramientas de carrera y una mascota/asistente llamada Astro.

La aplicación de referencia está construida con React, TypeScript y Vite. **Astro no es el framework**: es el nombre de la mascota y guía visual. Usa esta descripción para trasladar la experiencia a la arquitectura y tecnología que ya tenga el proyecto destino; no migres ni sustituyas su stack por esta referencia.

## Prompt listo para copiar

```text
Actúa como diseñador/a UX/UI y desarrollador/a frontend senior. Trabaja sobre el proyecto existente, que ya funciona y ofrece servicios de orientación laboral. Quiero que mejores su experiencia para que tenga una estructura, un flujo de onboarding, una jerarquía visual y una facilidad de uso comparables con la siguiente referencia, permitiendo mejoras de diseño cuando aporten claridad o calidad.

REGLAS DE ADAPTACIÓN
- Antes de modificar, inspecciona el stack, rutas, componentes, estilos, autenticación, datos y convenciones existentes. Conserva la arquitectura y las tecnologías del proyecto; adapta la propuesta a ellas.
- No reconstruyas la aplicación desde cero ni reemplaces servicios, contratos de API, autenticación, funcionalidades o contenido que ya esté funcionando. Reutiliza componentes y patrones existentes; integra los cambios quirúrgicamente.
- No copies ni redefinas la paleta cromática de la referencia. Conserva la paleta que ya usa el proyecto destino y aplícala consistentemente a los nuevos componentes. No hardcodees valores cromáticos ni introduzcas una paleta nueva.
- “Astro” en la referencia es una mascota/asistente, no una tecnología. Conserva el nombre, personaje o identidad de asistente que ya tenga el proyecto destino. Si no tiene uno, propón una figura propia y coherente con su marca; no copies literalmente la ilustración original.
- Puedes proponer mejoras de composición, tipografía, espaciado, iconografía, microinteracciones, responsive o accesibilidad. Mantén el propósito de cada paso y la navegación reconocible; no añadas fricción ni pasos sin justificación.
- Todo el texto visible debe seguir el idioma y el tono del producto existente.

EXPERIENCIA Y ESTRUCTURA A REPLICAR

1. Landing pública
- Barra superior compacta: marca, enlaces a secciones informativas y acciones diferenciadas para iniciar sesión y registrarse.
- Hero con una propuesta de valor fácil de entender, titular prominente, breve explicación y CTA principal de registro. Añade una acción secundaria solo si lleva a contenido real.
- Acompaña el hero con una composición visual del asistente/personaje. Puede incluir tarjetas pequeñas flotantes con ejemplos del valor del producto (por ejemplo, una recomendación o un indicador de compatibilidad), sin tapar el mensaje principal.
- Incluye una señal de confianza solo si el proyecto dispone de datos reales; no inventes cifras, testimonios ni resultados.
- Explica el producto con una sección breve de pasos numerados y conectados visualmente.
- Presenta las funciones principales en tarjetas con icono, título, descripción y una ilustración esquemática o preview cuando ayude a entenderlas.
- Cierra con un pie de página sencillo con marca, enlaces útiles y legal/ayuda existente.

2. Registro e inicio de sesión
- Mantén pantallas diferenciadas para registrarse e iniciar sesión, con marca, título claro, formulario corto y enlace para cambiar de modo.
- Muestra etiquetas y errores junto a los campos, conserva validación y autocompletado semántico, y ofrece un estado visible durante el envío.
- No alteres los mecanismos de autenticación ni la redirección después del acceso. Protege las rutas privadas y devuelve a la persona al destino solicitado cuando corresponda.

3. Onboarding del perfil
- Diseña un flujo guiado de seis etapas, con progreso visible, encabezado contextual, título y explicación breve. Mantén acciones “Volver” y “Continuar/Guardar” consistentes, etiquetas de avance y un mensaje claro al guardar.
- Permite dos formas de empezar:
  a. Ruta recomendada: asistencia de IA para importar datos desde el CV.
  b. Ruta manual: continuar directamente a la edición de experiencia, sin obligar a cargar un archivo.
- Orden de referencia:
  1. Elegir entre importación asistida y carga manual.
  2. Cargar CV mediante arrastrar/soltar o selector de archivos.
  3. Confirmar el archivo y ofrecer reemplazarlo.
  4. Revisar, añadir o eliminar experiencias laborales.
  5. Editar el resumen profesional.
  6. Completar datos personales y ubicación antes de guardar el perfil.
- En la carga, muestra formatos y límites realmente soportados por el proyecto, progreso mientras se procesa, restricciones, confirmación y un mensaje breve de privacidad. Mantén los límites de validación existentes; no los inventes ni los cambies.
- Las experiencias se editan en tarjetas repetibles: número o marcador de orden, cargo, empresa, periodo, descripción, contador si existe un límite y acción accesible para eliminar. Incluye un CTA para añadir otra experiencia y un estado vacío útil cuando no haya ninguna.
- Para el resumen, usa una caja de edición amplia, contador de caracteres si hay un máximo definido y un consejo contextual del asistente. Las acciones de IA deben estar conectadas a una funcionalidad existente o identificarse claramente como pendientes; no simules que funcionan.
- En datos personales, prioriza un formulario legible; acompaña la ubicación con una vista o resumen visual solo si aporta valor. No muestres un mapa decorativo que implique geolocalización real si no existe.
- Conserva los borradores y la reanudación del flujo según las capacidades existentes. Evita perder cambios al retroceder o al fallar una petición.
- Prevén doble envío. Permite cancelar operaciones largas cuando el stack lo soporte y limpia sus recursos al abandonar la pantalla.

4. Mascota/asistente de carrera
- Usa el personaje como apoyo y no como adorno dominante: bienvenida, explicación de una tarea, consejo contextual, procesamiento, confirmación y ayuda dentro de las herramientas.
- Mantén lenguaje breve, alentador, profesional y no invasivo. El asistente debe acompañar las decisiones sin ocultar información ni sustituir controles de usuario.
- Si la marca destino tiene mascota propia, reutilízala. Si no, define una identidad original y reutilizable con variantes de pose/expresión para bienvenida, pensamiento, celebración, lectura/entrenamiento y apoyo.
- La ilustración puede tener animaciones sutiles (por ejemplo, flotación, parpadeo o gesto), con uso moderado, rendimiento adecuado y respeto por `prefers-reduced-motion`.
- Ofrece una versión compacta para navegación o chat y una composición mayor para bienvenida o espacios promocionales. Usa texto alternativo o marcado decorativo correcto según el contexto.

5. Dashboard y herramientas
- Usa un shell consistente: navegación lateral con secciones, marca, estado resumido del asistente y perfil; una barra superior con contexto/breadcrumb, acciones existentes y salida; y una zona principal con ancho legible.
- En móvil, transforma la navegación lateral en un menú que se abre y cierra claramente, permite cerrar al elegir una sección y no cubre permanentemente el contenido.
- Mantén las secciones que ya ofrece el producto. En la referencia son: resumen, CV, comparación de ofertas, cartas/correos, coach de entrevistas y tracker/historial. No elimines módulos existentes.
- Abre cada módulo con un encabezado consistente (título, descripción y acciones relevantes).
- El resumen prioriza métricas comprensibles, distribución por estados y actividad reciente; cada bloque debe enlazar a la acción o sección correspondiente.
- Para herramientas de análisis, generación y chat, utiliza áreas de trabajo con controles a un lado y resultado/detalle al otro cuando el ancho lo permita. En pantallas estrechas, apílalos en un orden natural.
- Mantén tarjetas, tablas/listas, etiquetas, iconos, formularios y acciones con patrones compartidos. Usa indicadores numéricos y estados con texto para que el significado no dependa únicamente de la presentación visual.

6. Estados y comportamiento visual
- Diseña estados de carga con skeletons que respeten las proporciones y la estructura del contenido real.
- En errores, usa un mensaje comprensible y una acción “Reintentar” cuando tenga sentido; conserva el tratamiento de errores y la telemetría segura del proyecto.
- En colecciones vacías, explica qué falta y ofrece una acción útil para empezar.
- En acciones largas o de IA, deshabilita temporalmente el envío duplicado y muestra actividad/progreso y qué está haciendo el sistema. No presentes una operación fallida como exitosa.
- En éxito, confirma el resultado y deja claro el siguiente paso.
- Añade estados hover, focus-visible, activo, deshabilitado y validación de campos. Asegura que la interacción funciona con teclado y lectores de pantalla.

7. Dirección visual y responsive (sin cambiar la identidad cromática del proyecto destino)
- Conserva una sans serif legible, una jerarquía tipográfica marcada, títulos expresivos, descripciones breves y textos secundarios fáciles de escanear.
- Usa composiciones con aire, contenedores de ancho controlado, tarjetas de bordes suaves, separación coherente, iconos consistentes y sombras discretas solo donde comuniquen elevación.
- En landing, prioriza una composición de dos columnas en pantallas amplias y una secuencia vertical centrada en móvil.
- En onboarding, centra el contenido, limita el ancho de formularios y adapta tarjetas y rejillas a una sola columna en móviles pequeños.
- En dashboard, conserva la navegación persistente en escritorio y optimiza densidad, controles y tablas/listas para móvil.
- Ajusta puntos de quiebre al diseño real del proyecto. Evita desbordamiento horizontal, controles diminutos y contenido importante oculto.
- Usa animaciones breves y funcionales; desactívalas o redúcelas cuando la persona prefiera movimiento reducido.

ACCESIBILIDAD, CALIDAD Y ENTREGA
- Usa HTML semántico, etiquetas asociadas a controles, nombres accesibles en botones de icono, mensajes de error enlazados a campos y foco visible.
- No sacrifiques contraste, legibilidad, navegación por teclado ni escalado de texto.
- Conserva los límites, validaciones, rutas, contratos y comportamientos funcionales existentes.
- Añade o actualiza solo pruebas relacionadas con el comportamiento nuevo o corregido. Ejecuta las validaciones disponibles más acotadas (tests, lint y/o build) y corrige los errores causados por tus cambios.
- Al terminar, resume qué pantallas/componentes modificaste, qué decisiones visuales mejoraste, qué validaciones ejecutaste y cualquier limitación pendiente. No afirmes que una funcionalidad quedó conectada si no lo está.
```

## Lectura del flujo de referencia

- **Entrada:** la landing lleva a registro o inicio de sesión. El registro conduce al onboarding; las rutas privadas requieren sesión. Si el perfil ya existe, se accede al dashboard; si no, se deriva al onboarding.
- **Inicio de onboarding:** la primera pantalla recomienda importar el CV con IA, pero ofrece carga manual. La ruta manual salta la carga y llega a experiencia laboral.
- **Importación:** selección o arrastre del archivo, validación, estado de lectura, confirmación del archivo, opción de reemplazo y revisión de los datos extraídos.
- **Edición:** experiencias repetibles, resumen profesional y datos personales/ubicación. El borrador puede conservarse en almacenamiento de sesión; el perfil se guarda al confirmar.
- **Finalización:** el guardado confirma el éxito y conduce al dashboard.
- **Después del onboarding:** el dashboard ofrece resumen, CV, análisis de ofertas, cartas y correos, coach y tracker; el asistente aparece como apoyo contextual.

## Referencias inspeccionadas

- [Rutas y guards](./src/app/routes.tsx), [router](./src/app/router.tsx) y [providers](./src/app/providers.tsx).
- [Landing](./src/features/landing/index.tsx), [autenticación](./src/features/auth/pages/AuthPage.tsx) y [onboarding](./src/features/onboarding/pages/OnboardingPage.tsx).
- [Dashboard](./src/features/dashboard/index.tsx), [componentes compartidos](./src/shared/ui.tsx) y [estilos responsive](./src/index.css).
- [Borrador del perfil](./src/features/profile/store.ts) y [estados de carga](./src/shared/components/Skeleton.tsx).
