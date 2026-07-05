# Diagrama de Secuencia — RF02: Notificar Programación de Instalación al Cliente

---

## SC01 — Notificación exitosa (email + WhatsApp)

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant SQS as SQS Notificaciones
    participant msNotif as ms-notificaciones (Lambda)
    participant SES as Amazon SES
    participant WA as WhatsApp Business API
    participant msOrden as ms-orden-instalacion
    participant msAudit as ms-auditoria
    actor Cliente

    EB->>SQS: INSTALACION_PROGRAMADA (email, telefono, fecha, franja, tecnico, enlace)
    SQS->>msNotif: trigger Lambda
    msNotif->>msNotif: verificar idempotencia DynamoDB (orden_id+tipo ≠ ENVIADA)
    msNotif->>SES: enviar email con datos + enlace reprogramación
    SES-->>Cliente: 📧 Email
    SES-->>msNotif: confirmado ✓
    msNotif->>WA: POST WhatsApp API
    WA-->>Cliente: 📱 WhatsApp
    WA-->>msNotif: confirmado ✓
    msNotif->>msNotif: INSERT DynamoDB EMAIL=ENVIADA, WA=ENVIADA
    msNotif->>EB: NOTIFICACION_ENVIADA
    EB->>msOrden: actualizar notificacion=ENVIADA
    EB->>msAudit: INSERT EXITOSO
```

---

## SC02 — Email no registrado

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant msNotif as ms-notificaciones (Lambda)
    participant msAudit as ms-auditoria

    EB->>msNotif: INSTALACION_PROGRAMADA (cliente_email=null)
    msNotif->>msNotif: cliente_email = null ✗
    msNotif->>msNotif: INSERT DynamoDB EMAIL=FALLIDA motivo=EMAIL_NO_REGISTRADO
    EB->>msAudit: INSERT FALLIDO "Correo electrónico no registrado"
    Note over msNotif: "No es posible notificar al cliente. Correo electrónico no registrado"
```

---

## SC03 — Teléfono no registrado

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant msNotif as ms-notificaciones (Lambda)
    participant msAudit as ms-auditoria

    EB->>msNotif: INSTALACION_PROGRAMADA (cliente_telefono=null)
    msNotif->>msNotif: email enviado ✓
    msNotif->>msNotif: cliente_telefono = null ✗
    msNotif->>msNotif: INSERT DynamoDB WA=FALLIDA motivo=TELEFONO_NO_REGISTRADO
    EB->>msAudit: INSERT FALLIDO "Número de teléfono no registrado"
```

---

## SC04 — Datos de programación incompletos

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant msNotif as ms-notificaciones (Lambda)
    participant msAudit as ms-auditoria

    EB->>msNotif: INSTALACION_PROGRAMADA (fecha_programada=null)
    msNotif->>msNotif: validar datos → fecha_programada=null ✗
    msNotif->>msNotif: INSERT DynamoDB FALLIDA motivo=DATOS_INCOMPLETOS
    EB->>msAudit: INSERT FALLIDO "Datos de programación incompletos"
    Note over msNotif: "La orden no cuenta con datos de programación completos"
```

---

## SC05 — Error técnico con reintento automático (hasta 3 veces)

```mermaid
sequenceDiagram
    participant SQS as SQS Notificaciones
    participant msNotif as ms-notificaciones (Lambda)
    participant SES as Amazon SES
    participant CW as CloudWatch
    participant msAudit as ms-auditoria

    SQS->>msNotif: intento 1
    msNotif->>SES: enviar email
    SES-->>msNotif: Error 503
    msNotif->>msNotif: intentos=1 → devolver a SQS
    Note over SQS: espera 5 min
    SQS->>msNotif: intento 2
    SES-->>msNotif: Error 503
    msNotif->>msNotif: intentos=2 → devolver a SQS
    Note over SQS: espera 10 min
    SQS->>msNotif: intento 3
    SES-->>msNotif: Error 503
    msNotif->>msNotif: FALLIDA_DEFINITIVA (intentos=3)
    msNotif->>CW: métrica NOTIFICACION_FALLIDA_MAX_REINTENTOS → alarma NOC
    EB->>msAudit: INSERT INCIDENTE_TECNICO
    Note over msNotif: "No fue posible enviar la notificación al cliente"
```
