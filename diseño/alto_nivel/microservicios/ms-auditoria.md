# Microservicio: ms-auditoria

## Descripción
Captura, almacena y expone el registro de auditoría inmutable de todos los eventos críticos del ciclo de vida del servicio. Escucha eventos de todos los microservicios y los persiste en almacén append-only. Provee API de consulta para auditores y detecta inconsistencias entre activación y facturación. Cubre Iniciativa 1 (trazabilidad), Iniciativa 2 (compliance) e Iniciativa 3 (observabilidad).

## Stack tecnológico
- **Cómputo:** AWS Lambda (event-driven)
- **Base de datos:** PostgreSQL con particionamiento mensual + S3 + S3 Glacier
- **Búsqueda:** Amazon OpenSearch
- **Mensajería:** EventBridge (suscriptor de todos los eventos)

---

## Base de datos

```sql
-- Tabla append-only (sin UPDATE ni DELETE)
CREATE TABLE audit_evento (
    id                   UUID        NOT NULL DEFAULT gen_random_uuid(),
    correlation_id       VARCHAR(100),
    trace_id             VARCHAR(100),
    tipo_evento          VARCHAR(60)  NOT NULL,
    microservicio_origen VARCHAR(50)  NOT NULL,
    orden_id             UUID,
    cliente_id           VARCHAR(50),
    numero_contrato      VARCHAR(30),
    usuario_id           VARCHAR(50),
    usuario_tipo         VARCHAR(20),
    estado_anterior      VARCHAR(30),
    estado_nuevo         VARCHAR(30),
    resultado            VARCHAR(10)  NOT NULL, -- EXITOSO, FALLIDO
    payload              JSONB,
    mensaje_error        TEXT,
    fecha_evento         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, fecha_evento)
) PARTITION BY RANGE (fecha_evento);

CREATE TABLE audit_inconsistencia (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_inconsistencia VARCHAR(60) NOT NULL,
    orden_id            UUID,
    numero_contrato     VARCHAR(30),
    descripcion         TEXT        NOT NULL,
    dato_activacion     JSONB,
    dato_facturacion    JSONB,
    estado              VARCHAR(20) NOT NULL DEFAULT 'DETECTADA',
    fecha_deteccion     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_orden      ON audit_evento(orden_id);
CREATE INDEX idx_audit_cliente    ON audit_evento(cliente_id);
CREATE INDEX idx_audit_contrato   ON audit_evento(numero_contrato);
CREATE INDEX idx_audit_tipo       ON audit_evento(tipo_evento);
CREATE INDEX idx_audit_fecha      ON audit_evento(fecha_evento DESC);
```

---

## Funcionalidades

### F01 — Capturar evento de auditoría (solo INSERT)

**Evento de entrada (EventBridge):** Cualquier evento publicado por cualquier microservicio del hub.

**Pseudocódigo:**
```
FUNCIÓN capturarEvento(evento):
  INSERT INTO audit_evento (todos los campos del evento)
  INDEXAR en OpenSearch
  SI tipo_evento IN ['SERVICIO_ACTIVADO','FACTURACION_INICIADA']:
    ENCOLAR verificación consistencia
```
**Lineamientos:** OBS-08, OBS-09, OBS-10, RNF-004

---

### F02 — Verificar consistencia activación vs facturación

**Pseudocódigo:**
```
FUNCIÓN verificarConsistencia(numero_contrato):
  evento_act = BUSCAR SERVICIO_ACTIVADO WHERE contrato = numero_contrato
  evento_fac = BUSCAR FACTURACION_INICIADA WHERE contrato = numero_contrato
  VALIDAR: mismo cliente, mismo plan, fecha_fac >= fecha_act, mismo contrato
  SI inconsistencia: INSERT audit_inconsistencia, PUBLICAR alerta CloudWatch
```
**Lineamientos:** OBS-03, OBS-04, RNF-001, RNF-004

---

### F03 — Consultar log de auditoría por orden

**Contrato:** `GET /v1/auditoria/ordenes/{orden_id}` (solo roles AUDITOR/ADMIN)
**Pseudocódigo:**
```
FUNCIÓN consultarAuditoriaOrden(orden_id, filtros):
  VALIDAR rol = AUDITOR o ADMIN_SISTEMAS
  resultado = BUSCAR OpenSearch WHERE orden_id ORDER BY fecha ASC
  RETORNAR eventos (sin passwords, tokens ni datos sensibles)
```
**Lineamientos:** OBS-05, OBS-10, OBS-11

---

## Eventos auditables capturados (RNF-004 — 14 eventos)

| # | Tipo de evento | Microservicio |
|---|----------------|---------------|
| 1 | ORDEN_CREADA | ms-orden-instalacion |
| 2 | INSTALACION_PROGRAMADA | ms-programacion-instalacion |
| 3 | RECURSOS_RESERVADOS | ms-inventario |
| 4 | NOTIFICACION_ENVIADA | ms-notificaciones |
| 5 | INSTALACION_REPROGRAMADA | ms-programacion-instalacion |
| 6 | ACTIVACION_SOLICITADA | ms-activacion-servicio |
| 7 | DATOS_CLIENTE_VALIDADOS | ms-activacion-servicio |
| 8 | SERVICIO_ACTIVADO_OSS | ms-activacion-servicio |
| 9 | SERVICIO_ACTIVADO | ms-activacion-servicio |
| 10 | CONTRATO_GENERADO | ms-activacion-servicio |
| 11 | FACTURACION_INICIADA | ms-facturacion |
| 12 | ORDEN_CERRADA_EXITOSA | ms-orden-instalacion |
| 13 | CONTRATO_ENVIADO_CLIENTE | ms-notificaciones |
| 14 | OPERACION_REVERTIDA | ms-activacion / ms-programacion |

## Lineamientos cubiertos

| Código | Descripción |
|--------|-------------|
| ARQ-03 | Responsabilidad única — auditoría centralizada |
| INT-02 | Suscriptor EventBridge |
| ESC-03 | Lambda escala por volumen de eventos |
| OBS-01 | Logs estructurados |
| OBS-02 | Correlation ID y Trace ID |
| OBS-03 | Métricas de inconsistencias |
| OBS-04 | Alertas ante inconsistencias |
| OBS-05 | No expone datos sensibles |
| OBS-08 | Registros inmutables (solo INSERT) |
| OBS-09 | Retención mínima 5 años |
| OBS-10 | Acceso restringido a roles autorizados |
| OBS-11 | OpenSearch para consultas sin impacto operativo |
| RNF-001 | Verificación consistencia activación vs facturación |
| RNF-004 | 14 eventos auditables capturados |
