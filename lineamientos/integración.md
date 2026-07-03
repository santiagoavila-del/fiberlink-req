## Lineamientos de Integración

Objetivos:
- Busca que la aplicación se conecte correctamente con otros sistemas.
- Responde a: ¿Cómo se comunica la aplicación con otros sistemas de forma confiable?

Lineamientos:
- INT-01: Las integraciones síncronas deben exponerse mediante APIs versionadas y documentadas.
- INT-02: Las integraciones asíncronas deben desacoplarse mediante colas, eventos o mensajería.
- INT-03: Deben manejarse timeouts, reintentos y circuit breaker en llamadas remotas.
- INT-04: Toda API debe tener contratos claros de entrada, salida y errores.
- INT-05: Los cambios incompatibles deben publicarse como nuevas versiones.
- INT-06: Las integraciones críticas deben ser idempotentes cuando aplique.
- INT-07: Debe minimizarse el acoplamiento directo entre sistemas.
- INT-08: Deben registrarse evidencias de intercambio para trazabilidad y soporte.