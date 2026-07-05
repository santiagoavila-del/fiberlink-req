# Microservicio: ms-facturacion

## Descripción
Gestiona el inicio del ciclo de facturación del servicio de internet tras la activación. Recibe la señal de activación, registra el plan, genera datos de facturación y sincroniza con el ERP on-premises Unix heredado vía cola asíncrona. Garantiza que la fecha de inicio de facturación sea siempre igual o posterior a la fecha de activación. Cubre Iniciativa 1 (Hub) e Iniciativa 2 (automatización).

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate
- **Base de datos:** PostgreSQL (Amazon RDS)
- **Mensajería:** EventBridge + SQS (cola ERP)
- **Integración:** ERP Unix on-premises vía VPN/PrivateLink
- **Caché:** ElastiCache (Redis) — consultas del portal

---

## Base de datos

```sql
CREATE TABLE facturacion_cliente (
    id                         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    numero_contrato            VARCHAR(30) NOT NULL UNIQUE,
    cliente_id                 VARCHAR(50) NOT NULL,
    plan_servicio_id           VARCHAR(50) NOT NULL,
    plan_nombre                VARCHAR(100) NOT NULL,
    monto_mensual              DECIMAL(10,2) NOT NULL,
    ciclo_facturacion          VARCHAR(10) NOT NULL,
    fecha_inicio_facturacion   DATE        NOT NULL,
    fecha_activacion_servicio  TIMESTAMPTZ NOT NULL,
    estado                     VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    erp_referencia_id          VARCHAR(50),
    correlation_id             VARCHAR(100),
    fecha_creacion             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_estado_fac CHECK (estado IN ('PENDIENTE','ACTIVO','SUSPENDIDO','CANCELADO'))
);

CREATE TABLE erp_integracion (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    facturacion_id  UUID        NOT NULL REFERENCES facturacion_cliente(id),
    tipo_mensaje    VARCHAR(30) NOT NULL,
    payload_enviado JSONB       NOT NULL,
    estado_envio    VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE',
    intentos        INTEGER     NOT NULL DEFAULT 0,
    erp_respuesta   JSONB,
    fecha_envio     TIMESTAMPTZ,
    error_detalle   TEXT
);

CREATE INDEX idx_fac_cliente   ON facturacion_cliente(cliente_id);
CREATE INDEX idx_fac_contrato  ON facturacion_cliente(numero_contrato);
CREATE INDEX idx_erp_factura   ON erp_integracion(facturacion_id, estado_envio);
```

---

## Funcionalidades

### F01 — Iniciar ciclo de facturación

**Contrato de entrada:**
```json
POST /v1/facturacion/iniciar
{ "numero_contrato": "CTR-2026-00123", "cliente_id": "CLI-00123",
  "plan_servicio_id": "PLAN-FIBRA-100", "monto_mensual": 35.00,
  "ciclo_facturacion": "5", "fecha_activacion": "2026-07-10T14:35:00-05:00",
  "correlation_id": "corr-act-001" }
```
**Pseudocódigo:**
```
FUNCIÓN iniciarFacturacion(datos):
  VERIFICAR idempotencia por numero_contrato
  fecha_inicio = FECHA(datos.fecha_activacion)  -- >= fecha activación
  INICIO TRANSACCIÓN
    INSERTAR facturacion_cliente estado='PENDIENTE'
    ENCOLAR en SQS cola-erp-integracion
    ACTUALIZAR estado='ACTIVO'
  FIN TRANSACCIÓN
  PUBLICAR "FACTURACION_INICIADA" en EventBridge
  REGISTRAR en audit_log
```
**Features:** RF04-SC01
**Lineamientos:** INT-02, INT-06, RNF-001, RNF-004, SEG-10

---

### F02 — Confirmar integración con ERP

**Pseudocódigo:**
```
FUNCIÓN confirmarERP(erp_referencia_id, numero_contrato, estado):
  SI estado = "CONFIRMADO": ACTUALIZAR integracion, vincular erp_id
  SI estado = "RECHAZADO":
    SI intentos < 3: REENCOLAR con backoff exponencial
    SINO: ALERTAR CloudWatch, REGISTRAR incidente
```
**Lineamientos:** INT-03, OBS-04

---

### F03 — Consultar facturación

**Contrato:** `GET /v1/facturacion?numero_contrato=CTR-2026-00123`
**Pseudocódigo:**
```
FUNCIÓN consultarFacturacion(numero_contrato):
  resultado = BUSCAR Redis TTL=10min
  SI no en caché: CONSULTAR PostgreSQL
  RETORNAR datos facturación (sin datos sensibles)
```
**Lineamientos:** ESC-04, SEG-07, RNF-001

---

## Lineamientos cubiertos

| Código | Descripción |
|--------|-------------|
| ARQ-03 | Responsabilidad única — ciclo facturación |
| INT-01 | API REST versionada |
| INT-02 | Integración asíncrona ERP vía SQS |
| INT-03 | Reintentos con backoff exponencial |
| INT-06 | Idempotencia por numero_contrato |
| ESC-04 | Caché Redis en consultas del portal |
| SEG-07 | Mínimo privilegio — cliente solo ve sus datos |
| SEG-10 | Auditoría de operaciones financieras |
| OBS-01 | Logs estructurados |
| OBS-04 | Alerta si ERP falla definitivamente |
| RNF-001 | Fecha inicio >= fecha activación; plan = plan contratado |
| RNF-003 | Datos financieros protegidos con mínimo privilegio |
| RNF-004 | Registro completo del inicio de facturación |
