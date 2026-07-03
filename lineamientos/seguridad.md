## Lineamientos de Seguridad

Objetivos:
- Busca proteger la aplicación, los datos y las integraciones.
- Responde a: ¿Cómo evitamos accesos no autorizados, fugas de datos y abuso del sistema?

Lineamientos:
- SEG-01: Toda comunicación entre componentes debe usar cifrado en tránsito.
- SEG-02: La información sensible debe almacenarse con cifrado en reposo.
- SEG-03: La autenticación debe centralizarse usando un mecanismo estándar como OAuth2 u OpenID Connect.
- SEG-04: La autorización debe aplicarse bajo el principio de mínimo privilegio.
- SEG-05: No se deben almacenar secretos en código fuente ni en archivos de configuración planos.
- SEG-06: Todas las operaciones críticas deben dejar registro de auditoría.
- SEG-07: Las APIs públicas deben protegerse con controles como rate limiting, validación de entrada y WAF.
- SEG-08: Deben aplicarse prácticas de desarrollo seguro y análisis de vulnerabilidades sobre dependencias e imágenes.
