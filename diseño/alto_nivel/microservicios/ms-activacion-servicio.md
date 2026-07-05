# Microservicio: ms-activacion-servicio

## Descripción
Orquesta el proceso de activación del servicio de internet una vez concluida la instalación. Coordina validación de datos del cliente, activación en el OSS on-premises, generación del contrato, inicio de facturación y cierre de orden mediante el patrón Saga con compensación en Step Functions. Cubre Iniciativa 1 (Hub integración) e Iniciativa 2 (automatización).

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate
- **Orquestación:** AWS Step Functions (saga con compensación)
- **Base de datos:** PostgreSQL (Amazon RDS)
- **Mensajería:** EventBridge + SQS
- **Integración:** OSS on-premises vía VPN/PrivateLink, CRM SaaS, ms-facturacion
- **Timeout activación OSS:** 30 segundos (definido en RF04)

---

## Base de datos

```sql
CREATE TABLE activacion (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id            UUID        NOT NULL UNIQUE,
    cliente_id          VARCHAR(50) NOT NULL,
    cliente_documento   VARCHAR(20) NOT NULL,
    tecnico_id          VARCHAR(50) NOT NULL,
    plan_servicio_id    VARCHAR(50) NOT NULL,
    equipo_ont_serie    VARCHAR(50),
    equipo_router_serie VARCHAR(50),
    potencia_optica_db  DECIMAL(5,2),
    estado              VARCHAR(25) NOT NULL DEFAULT 'PENDIENTE',
    numero_contrato     VARCHAR(30),
    fecha_activacion    TIMESTAMPTZ,
    fecha_solicitud     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    step_functions_arn  VARCHAR(500),
    correlation_id      VARCHAR(100),
    CONSTRAINT chk_estado_act CHECK (estado IN (
        'PENDIENTE','VALIDANDO','ACTIVANDO_OSS','GENERANDO_CONTRATO',
        'INICIANDO_FACTURACION','ACTIVO','FALLIDO','REVERTIDO'
    ))
);

CREATE TABLE activacion_paso (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    activacion_id    UUID        NOT NULL REFERENCES activacion(id),
    paso             VARCHAR(50) NOT NULL,
    estado           VARCHAR(15) NOT NULL,
    request_payload  JSONB,
    response_payload JSONB,
    duracion_ms      INTEGER,
    fecha_inicio     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_fin        TIMESTAMPTZ,
    error_detalle    TEXT
);

CREATE TABLE contrato (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    activacion_id       UUID        NOT NULL REFERENCES activacion(id),
    numero_contrato     VARCHAR(30) NOT NULL UNIQUE,
    cliente_id          VARCHAR(50) NOT NULL,
    plan_servicio_id    VARCHAR(50) NOT NULL,
    fecha_inicio        DATE        NOT NULL,
    fecha_generacion    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    url_documento_s3    VARCHAR(500),
    enviado_cliente     BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_activacion_orden ON activacion(orden_id);
CREATE INDEX idx_activacion_estado ON activacion(estado);
CREATE INDEX idx_paso_activacion ON activacion_paso(activacion_id);
```

---

## Funcionalidades

### F01 — Solicitar activación del servicio

**Contrato de entrada:**
```json
POST /v1/activaciones
{ "orden_id": "uuid", "cliente_documento": "12345678", "tecnico_id": "TEC-042",
  "equipo_ont_serie": "HWTC12345678", "equipo_router_serie": "TPLK98765432",
  "potencia_optica_db": -18.5, "correlation_id": "corr-act-001" }
```
**Contrato de salida — aceptado (202):**
```json
{ "activacion_id": "uuid", "orden_id": "uuid", "estado": "PENDIENTE",
  "mensaje": "Solicitud de activación recibida. Procesando..." }
```
**Pseudocódigo:**
```
FUNCIÓN solicitarActivacion(datos):
  orden = LLAMAR ms-orden GET /v1/ordenes/{orden_id}
  SI datos.cliente_documento != orden.cliente_documento:
    REGISTRAR intento fallido en audit_log
    RETORNAR error 422 DATOS_CLIENTE_NO_COINCIDEN
  activacion = CREAR registro estado="PENDIENTE"
  arn = INICIAR Step Functions saga
  ACTUALIZAR activacion.step_functions_arn = arn
```

---

### F02 — Saga de activación (Step Functions)

**Pseudocódigo:**
```
SAGA activarServicio(activacion_id):

  PASO 1 — VALIDAR_ORDEN (solo lectura):
    VERIFICAR orden estado PROGRAMADA/INSTALADA → SI falla: TERMINAR FALLIDO

  PASO 2 — ACTIVAR_OSS (timeout: 30s):
    LLAMAR OSS API: activar ONT y router por serie
    SI timeout/error: REGISTRAR incidente → RETORNAR FALLIDO

  PASO 3 — REGISTRAR_SERVICIO:
    ACTUALIZAR estado = "ACTIVO" en OSS y CRM
    PUBLICAR "SERVICIO_ACTIVADO" en EventBridge
    SI falla: COMPENSAR paso 2

  PASO 4 — GENERAR_CONTRATO:
    GENERAR numero_contrato, PDF, SUBIR a S3 cifrado
    SI falla: COMPENSAR pasos 3 y 2

  PASO 5 — INICIAR_FACTURACION:
    LLAMAR ms-facturacion POST /v1/facturacion/iniciar
    SI falla: COMPENSAR pasos 4, 3 y 2

  PASO 6 — CERRAR_ORDEN:
    LLAMAR ms-orden PATCH /estado → "EXITOSA"
    PUBLICAR "ORDEN_CERRADA_EXITOSA"

  PASO 7 — ENVIAR_CONTRATO (async):
    ENCOLAR en SQS para ms-notificaciones
```

**Features:** RF04-SC01/SC02/SC03/SC04
**Lineamientos:** ARQ-06, INT-03, INT-06, ESC-05, SEG-02, SEG-10, OBS-02, OBS-06, RNF-001

---

## Features y escenarios cubiertos

| Feature | Escenario | Descripción |
|---------|-----------|-------------|
| RF04 | SC01 | Activación exitosa — saga completa |
| RF04 | SC02 | Datos cliente no coinciden — rechazado en F01 |
| RF04 | SC03 | Error técnico generando contrato — compensación |
| RF04 | SC04 | Timeout OSS 30s — reversión |

## Lineamientos cubiertos

| Código | Descripción |
|--------|-------------|
| ARQ-03 | Responsabilidad única — orquestación activación |
| ARQ-06 | Reglas de negocio no embebidas en canales |
| INT-01 | API REST versionada |
| INT-03 | Timeout 30s, circuit breaker, reintentos |
| INT-06 | Idempotencia en cada paso de la saga |
| ESC-05 | Envío contrato desacoplado y asíncrono |
| SEG-02 | PDF contratos cifrados en reposo en S3 |
| SEG-10 | Auditoría de cada paso de la activación |
| OBS-02 | Correlation ID y Trace ID en toda la saga |
| OBS-06 | Trazas distribuidas end-to-end (X-Ray) |
| RNF-001 | Atomicidad — saga con compensación completa |
| RNF-003 | Validación datos cliente antes de activar |
| RNF-004 | Log de cada paso del proceso |
