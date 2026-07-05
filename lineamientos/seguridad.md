## Lineamientos de Seguridad

Objetivos:
- Busca proteger la aplicación, los datos y las integraciones.
- Responde a: ¿Cómo evitamos accesos no autorizados, fugas de datos y abuso del sistema?

Lineamientos:
- SEG-01: Toda comunicación entre componentes debe usar cifrado en tránsito.
- SEG-02: La información sensible debe almacenarse con cifrado en reposo.
- SEG-03: La autenticación debe centralizarse usando un mecanismo estándar como OAuth2 u OpenID Connect.
- SEG-04: Autenticación multifactor (MFA) obligatoria para operaciones sensibles: cambio de contraseña, actualización de datos de pago y solicitud de reprogramación o cancelación del servicio.
- SEG-05: Tokens de sesión con tiempo de expiración máximo de 30 minutos de inactividad.
- SEG-06: Cifrado TLS 1.2 o superior en todas las comunicaciones entre el cliente y el portal o la app.
- SEG-07: La autorización debe aplicarse bajo el principio de mínimo privilegio.
- SEG-08: No se deben almacenar secretos en código fuente ni en archivos de configuración planos.
- SEG-09: Almacenamiento de contraseñas con algoritmos de hash seguros (bcrypt, Argon2). Prohibido almacenar contraseñas en texto plano.
- SEG-10: Todas las operaciones críticas deben dejar registro de auditoría.
- SEG-11: Las APIs públicas deben protegerse con controles como rate limiting, validación de entrada y WAF.
- SEG-12: Deben aplicarse prácticas de desarrollo seguro y análisis de vulnerabilidades sobre dependencias e imágenes.
