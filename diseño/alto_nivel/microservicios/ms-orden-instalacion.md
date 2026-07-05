# Microservicio: ms-orden-instalacion

## Descripción
Gestiona el ciclo de vida completo de las órdenes de instalación del servicio de internet, desde su creación hasta su cierre. Actúa como entidad central que coordina el estado de la orden y sirve como fuente de verdad para los demás microservicios. Cubre la Iniciativa 1 (Hub de integración) e Iniciativa 2 (automatización operacional).

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate
- **Base de datos:** PostgreSQL (Amazon RDS)
- **Caché:** ElastiCache (Redis)
- **Mensajería:** Amazon EventBridge (publicación de eventos de cambio de estado)
- **API:** REST versionada expuesta a través de Amazon API Gateway

---

## Base de datos

```sql
CREATE TABLE orden_instalacion (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    numero_orden            VARCHAR(20)     NOT NULL UNIQUE,
    cliente_id              VARCHAR(50)     NOT NULL,
    cliente_documento       VARCHAR(20)     NOT NULL,
    cliente_nombre          VARCHAR(150)    NOT NULL,
    cliente_email           VARCHAR(150),
    cliente_telefono        VARCHAR(20),
    plan_servicio_id        VARCHAR(50)     NOT NULL,
    plan_servicio_nombre    VARCHAR(100)    NOT NULL,
    direccion_instalacion   TEXT            NOT NULL,
    estado                  VARCHAR(30)     NOT NULL DEFAULT 'CREADA',
    fecha_creacion          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_actualizacion     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_programada        DATE,
    franja_horaria          VARCHAR(20),
    tecnico_asignado_id     VARCHAR(50),
    tecnico_asignado_nombre VARCHAR(150),
    numero_contrato         VARCHAR(30),
    observaciones           TEXT,
    origen_crm              VARCHAR(50),
    CONSTRAINT chk_estado CHECK (estado IN (
        'CREADA','PROGRAMADA','NOTIFICADA','REPROGRAMADA',
        'EN_INSTALACION','INSTALADA','ACTIVADA','EXITOSA',
        'CANCELADA','FALLIDA'
    ))
);

CREATE TABLE orden_estado_historial (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id            UUID        NOT NULL REFERENCES orden_instalacion(id),
    estado_anterior     VARCHAR(30),
    estado_nuevo        VARCHAR(30) NOT NULL,
    usuario_id          VARCHAR(50) NOT NULL,
    usuario_tipo        VARCHAR(20) NOT NULL,
    motivo              TEXT,
    fecha_cambio        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id      VARCHAR(100)
);

CREATE TABLE orden_recurso (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id        UUID        NOT NULL REFERENCES orden_instalacion(id),
    tipo_recurso    VARCHAR(30) NOT NULL,
    recurso_id      VARCHAR(50) NOT NULL,
    recurso_nombre  VARCHAR(150),
    cantidad        INTEGER     NOT NULL DEFAULT 1,
    estado          VARCHAR(20) NOT NULL DEFAULT 'RESERVADO',
    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_liberacion TIMESTAMPTZ
);

CREATE INDEX idx_orden_cliente ON orden_instalacion(cliente_id);
CREATE INDEX idx_orden_estado ON orden_instalacion(estado);
CREATE INDEX idx_orden_fecha_programada ON orden_instalacion(fecha_programada);
CREATE INDEX idx_historial_orden ON orden_estado_historial(orden_id);
```

---

## Funcionalidades

### F01 — Crear orden de instalación

**Contrato de entrada:**
```json
POST /v1/ordenes
{ "cliente_id": "CLI-00123", "cliente_documento": "12345678", "cliente_nombre": "Juan Pérez",
  "cliente_email": "juan@email.com", "cliente_telefono": "0991234567",
  "plan_servicio_id": "PLAN-FIBRA-100", "plan_servicio_nombre": "Fibra 100 Mbps",
  "direccion_instalacion": "Av. Principal 123, Quito", "origen_crm": "CRM-SF-001" }
```
**Contrato de salida — éxito (201):**
```json
{ "orden_id": "uuid", "numero_orden": "ORD-2026-00456", "estado": "CREADA", "fecha_creacion": "2026-07-04T10:00:00-05:00" }
```
**Pseudocódigo:**
```
FUNCIÓN crearOrden(datos):
  VALIDAR campos obligatorios → error 400 si falla
  numero_orden = GENERAR "ORD-{año}-{secuencia}"
  INSERTAR orden con estado = "CREADA"
  PUBLICAR evento "ORDEN_CREADA" en EventBridge
  REGISTRAR en audit_log
  RETORNAR orden_id, numero_orden, estado
```

**Features y escenarios:** RF01-SC01 (precondición)
**Lineamientos:** ARQ-03, ARQ-05, INT-01, INT-04, SEG-10, OBS-01, OBS-02

---

### F02 — Consultar orden

**Contrato de entrada:** `GET /v1/ordenes/{orden_id}`
**Pseudocódigo:**
```
FUNCIÓN consultarOrden(orden_id):
  resultado = BUSCAR en caché Redis
  SI no está: CONSULTAR PostgreSQL → guardar en caché TTL=5min
  RETORNAR datos completos con historial y recursos
```
**Lineamientos:** ESC-04, SEG-07, INT-01

---

### F03 — Actualizar estado de la orden

**Contrato de entrada:**
```json
PATCH /v1/ordenes/{orden_id}/estado
{ "estado_nuevo": "PROGRAMADA", "usuario_id": "USR-OP-001", "usuario_tipo": "OPERADOR",
  "motivo": "Recursos asignados", "correlation_id": "corr-xyz-789" }
```
**Pseudocódigo:**
```
FUNCIÓN actualizarEstado(orden_id, estado_nuevo, usuario, motivo):
  VALIDAR transición permitida en matriz de estados
  INICIO TRANSACCIÓN
    ACTUALIZAR orden.estado, INSERTAR historial
    INVALIDAR caché Redis
  FIN TRANSACCIÓN
  PUBLICAR "ORDEN_ESTADO_CAMBIADO" en EventBridge
  REGISTRAR en audit_log
```
**Features y escenarios:** RF01-SC01/SC05, RF03-SC01/SC05, RF04-SC01/SC02/SC03/SC04
**Lineamientos:** INT-02, INT-06, OBS-02, RNF-001, RNF-004

---

## Features y escenarios cubiertos (resumen)

| Feature | Escenario | Descripción |
|---------|-----------|-------------|
| RF01 | SC01–SC05 | Programación de instalación — gestión de estado |
| RF03 | SC01–SC05 | Reprogramación — cambio de estado con historial |
| RF04 | SC01–SC04 | Activación — cierre de orden como EXITOSA o FALLIDA |

## Lineamientos cubiertos (resumen)

| Código | Descripción |
|--------|-------------|
| ARQ-01 | Separación por dominio: órdenes |
| ARQ-03 | Responsabilidad única |
| ARQ-05 | Contratos explícitos |
| INT-01 | API REST versionada |
| INT-02 | Eventos en EventBridge |
| INT-06 | Idempotencia por correlation_id |
| ESC-04 | Caché Redis en consultas |
| SEG-07 | Mínimo privilegio |
| SEG-10 | Auditoría de operaciones críticas |
| OBS-01 | Logs estructurados |
| OBS-02 | Correlation ID / Trace ID |
| RNF-001 | Integridad de datos propagada vía eventos |
| RNF-004 | Auditabilidad — historial inmutable de estados |
