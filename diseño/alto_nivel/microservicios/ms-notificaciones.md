# Microservicio: ms-notificaciones

## Descripción
Gestiona el envío de notificaciones multicanal (email, WhatsApp, portal, IVR) a clientes durante el ciclo de vida del servicio de internet. Escucha eventos del bus y despacha de forma asíncrona con reintentos automáticos. Cubre notificaciones de instalación (RF02), reprogramación (RF03), activación (RF04) y alertas proactivas de incidentes masivos (RF05). Cubre Iniciativa 2 (automatización) e Iniciativa 3 (observabilidad proactiva).

## Stack tecnológico
- **Cómputo:** AWS Lambda (event-driven, carga intermitente)
- **Base de datos:** DynamoDB (registro idempotente de notificaciones)
- **Mensajería:** SQS + SNS
- **Canales externos:** Amazon SES (email), WhatsApp Business API (Meta), portal Amplify (push), IVR on-premises vía API

---

## Base de datos (DynamoDB)

```
Tabla: notificaciones
  PK: notificacion_id (UUID)
  GSI: idx_orden → orden_id
  GSI: idx_cliente → cliente_id

Atributos:
  orden_id, incidente_id, cliente_id, canal (EMAIL|WHATSAPP|PORTAL|IVR),
  estado (PENDIENTE|ENVIADA|FALLIDA|REINTENTANDO|FALLIDA_DEFINITIVA),
  tipo_evento (PROGRAMACION|REPROGRAMACION|ACTIVACION|INCIDENTE_MASIVO|RESTABLECIMIENTO),
  destinatario, contenido_asunto, contenido_cuerpo,
  intentos (max 3), fecha_creacion, fecha_envio, correlation_id, error_detalle

Tabla: plantilla_notificacion
  PK: tipo_evento, SK: canal
  Atributos: asunto_template, cuerpo_template, activa, version
```

---

## Funcionalidades

### F01 — Enviar notificación de programación/reprogramación

**Evento de entrada (SQS/EventBridge):**
```json
{ "tipo_evento": "INSTALACION_PROGRAMADA", "orden_id": "uuid",
  "cliente_email": "juan@email.com", "cliente_telefono": "0991234567",
  "fecha_programada": "2026-07-10", "franja_horaria": "08:00-12:00",
  "tecnico_nombre": "Carlos López", "enlace_reprogramacion": "https://portal.fiberlink.com/reprogramar?token=abc",
  "correlation_id": "corr-prog-001" }
```
**Pseudocódigo:**
```
FUNCIÓN procesarEventoProgramacion(evento):
  VERIFICAR idempotencia DynamoDB (orden_id + tipo_evento)
  SI ya ENVIADA → RETORNAR
  PARA canal EN [EMAIL, WHATSAPP]:
    SI datos_contacto[canal] disponible:
      ENVIAR notificación vía canal
      REGISTRAR estado=ENVIADA
    SINO: REGISTRAR estado=FALLIDA con motivo
  PUBLICAR "NOTIFICACION_ENVIADA" → ms-orden-instalacion
  REGISTRAR en audit_log
```
**Features:** RF02-SC01/SC02/SC03/SC04/SC05, RF03-SC01
**Lineamientos:** INT-02, INT-03, INT-06, ESC-03, ESC-05, SEG-08, OBS-01, OBS-02

---

### F02 — Enviar notificación proactiva de incidente masivo

**Evento de entrada:**
```json
{ "tipo_evento": "INCIDENTE_MASIVO_ACTIVO", "incidente_id": "INC-2026-001",
  "clientes_afectados": ["CLI-00123","CLI-00456"],
  "zona_impactada": "NORTE-QUITO", "tiempo_estimado_reparacion": "2 horas",
  "correlation_id": "corr-inc-001" }
```
**Pseudocódigo:**
```
FUNCIÓN procesarIncidenteMasivo(evento):
  PARA CADA cliente_id EN evento.clientes_afectados:
    OBTENER datos_contacto del cliente (email, telefono)
    ENVIAR por EMAIL y WHATSAPP: aviso de falla + tiempo estimado
    ACTUALIZAR portal (push notification)
    REGISTRAR hora envío en DynamoDB
  LLAMAR IVR API: actualizar mensaje zona_impactada
  PUBLICAR "CLIENTES_NOTIFICADOS" en EventBridge
  REGISTRAR en audit_log
```
**Features:** RF05-SC02/SC07
**Lineamientos:** INT-02, ESC-03, ESC-05, OBS-01

---

### F03 — Enviar notificación de restablecimiento de servicio

**Pseudocódigo:**
```
FUNCIÓN procesarRestablecimiento(evento):
  PARA CADA cliente EN incidente.clientes_afectados:
    ENVIAR notificación de restablecimiento por EMAIL y WHATSAPP
    ACTUALIZAR portal (estado normal)
  LLAMAR IVR API: limpiar mensaje de incidente
  REGISTRAR en audit_log
```
**Features:** RF05-SC04

---

### F04 — Reintentar notificaciones fallidas

**Trigger:** CloudWatch Events cada 5 minutos
**Pseudocódigo:**
```
FUNCIÓN reintentarNotificaciones():
  pendientes = CONSULTAR DynamoDB WHERE estado IN ('FALLIDA','REINTENTANDO')
               AND intentos < 3
  PARA CADA notif:
    intentos += 1
    REINTENTAR envío
    SI éxito: estado = ENVIADA
    SI falla Y intentos >= 3:
      estado = FALLIDA_DEFINITIVA
      PUBLICAR alerta CloudWatch
      REGISTRAR incidente técnico
```
**Features:** RF02-SC05, RF05-SC07
**Lineamientos:** INT-03, OBS-04, RNF-003

---

## Lineamientos cubiertos

| Código | Descripción |
|--------|-------------|
| ARQ-03 | Responsabilidad única — notificaciones multicanal |
| INT-02 | Integración asíncrona vía SQS y EventBridge |
| INT-03 | Reintentos automáticos con backoff |
| INT-06 | Idempotencia — no duplica envíos |
| ESC-03 | Lambda escala horizontalmente |
| ESC-05 | Notificación diferible y desacoplada |
| SEG-08 | Credenciales API WhatsApp/IVR en Secrets Manager |
| OBS-01 | Logs estructurados con estado por canal |
| OBS-02 | Correlation ID propagado desde evento origen |
| OBS-04 | Alerta cuando se agotan reintentos |
| RNF-003 | Seguridad — credenciales externas protegidas |
| RNF-004 | Registro de cada intento de notificación |
