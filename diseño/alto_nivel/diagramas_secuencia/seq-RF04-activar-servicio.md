# Diagrama de Secuencia — RF04: Activar Servicio de Internet

---

## SC01 — Activación exitosa

```mermaid
sequenceDiagram
    actor Tecnico
    participant AppMovil as App Móvil
    participant APIGW as API Gateway
    participant Cognito as Cognito
    participant msAct as ms-activacion-servicio
    participant SF as Step Functions (Saga)
    participant msOrden as ms-orden-instalacion
    participant OSS as OSS On-Premises
    participant CRM as CRM SaaS
    participant S3 as Amazon S3
    participant msFac as ms-facturacion
    participant SQS as SQS
    participant msNotif as ms-notificaciones
    participant msInv as ms-inventario
    participant EB as EventBridge
    participant msAudit as ms-auditoria
    actor Cliente

    Tecnico->>AppMovil: registra doc. cliente, confirma router/potencia óptica
    AppMovil->>APIGW: POST /v1/activaciones (orden_id, doc, ont_serie, router_serie, potencia)
    APIGW->>Cognito: validar token TECNICO ✓
    APIGW->>msAct: reenvía
    msAct->>msOrden: GET orden → cliente_documento ✓
    msAct->>msAct: doc coincide ✓ → CREATE activacion PENDIENTE
    msAct->>SF: INICIAR saga
    msAct-->>APIGW: 202 activacion_id PENDIENTE

    Note over SF: SAGA DE ACTIVACIÓN

    SF->>msOrden: confirmar estado PROGRAMADA ✓ (PASO 1)
    SF->>msAudit: INSERT DATOS_CLIENTE_VALIDADOS EXITOSO

    SF->>OSS: activar ONT + router (timeout 30s) (PASO 2)
    OSS-->>SF: confirmado < 30s ✓
    SF->>msAudit: INSERT SERVICIO_ACTIVADO_OSS EXITOSO

    SF->>CRM: estado servicio = ACTIVO (PASO 3)
    CRM-->>SF: ✓
    SF->>EB: SERVICIO_ACTIVADO
    EB->>msInv: equipos → INSTALADO
    SF->>msAudit: INSERT SERVICIO_ACTIVADO EXITOSO

    SF->>S3: subir PDF contrato (cifrado KMS) (PASO 4)
    S3-->>SF: URL ✓
    SF->>msAct: INSERT contrato (numero, cliente, plan, url_pdf)
    SF->>msAudit: INSERT CONTRATO_GENERADO EXITOSO

    SF->>msFac: POST /v1/facturacion/iniciar (PASO 5)
    msFac-->>SF: facturacion_id ✓
    SF->>msAudit: INSERT FACTURACION_INICIADA EXITOSO

    SF->>msOrden: PATCH /estado → EXITOSA (PASO 6)
    msOrden-->>SF: ✓
    SF->>msAudit: INSERT ORDEN_CERRADA_EXITOSA

    SF->>SQS: encolar ENVIO_CONTRATO (async, PASO 7)
    SQS->>msNotif: enviar PDF por email
    msNotif-->>Cliente: 📧 Contrato PDF
    msNotif->>msAudit: INSERT CONTRATO_ENVIADO_CLIENTE

    AppMovil-->>Tecnico: "Servicio activado correctamente"
```

---

## SC02 — Datos del cliente no coinciden

```mermaid
sequenceDiagram
    actor Tecnico
    participant AppMovil as App Móvil
    participant APIGW as API Gateway
    participant msAct as ms-activacion-servicio
    participant msOrden as ms-orden-instalacion
    participant msAudit as ms-auditoria

    Tecnico->>AppMovil: ingresa documento incorrecto
    AppMovil->>APIGW: POST /v1/activaciones (doc="99999999")
    APIGW->>msAct: reenvía
    msAct->>msOrden: GET orden → doc="12345678"
    msAct->>msAct: "99999999" ≠ "12345678" ✗ DATOS_CLIENTE_NO_COINCIDEN
    msAct->>msAudit: INSERT ACTIVACION_RECHAZADA FALLIDO
    msAct-->>APIGW: 422 "Los datos del cliente no coinciden con la orden. Verificar"
    APIGW-->>AppMovil: error en pantalla
```

---

## SC03 — Error técnico al generar contrato (compensación)

```mermaid
sequenceDiagram
    participant SF as Step Functions (Saga)
    participant OSS as OSS On-Premises
    participant CRM as CRM SaaS
    participant S3 as Amazon S3
    participant msOrden as ms-orden-instalacion
    participant CW as CloudWatch
    participant msAudit as ms-auditoria

    Note over SF: PASOS 1-3 exitosos (OSS activo, CRM activo)

    SF->>S3: subir PDF contrato (PASO 4)
    S3-->>SF: Error 500 ✗

    Note over SF: COMPENSACIÓN

    SF->>CRM: revertir estado=INACTIVO (compensar PASO 3)
    CRM-->>SF: ✓
    SF->>OSS: desactivar ONT + router (compensar PASO 2)
    OSS-->>SF: ✓
    SF->>msOrden: PATCH estado → FALLIDA
    SF->>CW: métrica ERROR_GENERACION_CONTRATO → alarma NOC
    SF->>msAudit: INSERT OPERACION_REVERTIDA + INCIDENTE_TECNICO
    Note over SF: "No fue posible realizar la activación del servicio"
```

---

## SC04 — Timeout activación OSS (> 30 segundos)

```mermaid
sequenceDiagram
    participant SF as Step Functions (Saga)
    participant OSS as OSS On-Premises
    participant msOrden as ms-orden-instalacion
    participant CW as CloudWatch
    participant msAudit as ms-auditoria

    Note over SF: PASO 1 completado ✓

    SF->>OSS: activar ONT + router (timeout=30s) (PASO 2)
    Note over OSS: sin respuesta...
    SF->>SF: timer expira 30s ✗ TIMEOUT_OSS

    SF->>msOrden: PATCH estado → FALLIDA
    SF->>CW: métrica TIMEOUT_OSS → alarma NOC
    SF->>msAudit: INSERT INCIDENTE_TECNICO (numero_contrato=null)
    Note over SF: "No fue posible realizar la activación del servicio"
    Note over SF: Técnico puede reintentar (operación idempotente por correlation_id)
```
