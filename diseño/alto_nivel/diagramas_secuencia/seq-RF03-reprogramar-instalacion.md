# Diagrama de Secuencia — RF03: Reprogramar Instalación del Servicio de Internet

---

## SC01 — Reprogramación exitosa

```mermaid
sequenceDiagram
    actor Cliente
    participant Portal as Portal (Amplify)
    participant Cognito as Cognito
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msOrden as ms-orden-instalacion
    participant msInv as ms-inventario
    participant EB as EventBridge
    participant msNotif as ms-notificaciones
    participant msAudit as ms-auditoria

    Cliente->>Portal: accede enlace reprogramación (token URL)
    Portal->>Cognito: validar token
    Cognito-->>Portal: válido ✓
    Cliente->>Portal: selecciona nueva_fecha + franja
    Portal->>APIGW: PUT /v1/programacion/{id}/reprogramar
    APIGW->>msProg: reenvía
    msProg->>msOrden: GET orden → estado=PROGRAMADA ✓
    msProg->>msProg: horas_restantes=144h > 24h ✓
    msProg->>msProg: nueva agenda disponible ✓
    msProg->>msProg: INICIO TRANSACCIÓN
    msProg->>msInv: liberar recursos anteriores
    msInv-->>msProg: liberados ✓
    msProg->>msInv: reservar nuevos recursos
    msInv-->>msProg: reservados ✓
    msProg->>msOrden: PATCH /estado → REPROGRAMADA
    msProg->>EB: INSTALACION_REPROGRAMADA
    msProg->>msProg: FIN TRANSACCIÓN ✓
    EB->>msNotif: nueva fecha + franja → email + WhatsApp al cliente
    EB->>msAudit: INSERT EXITOSO
    msProg-->>APIGW: 200 "Instalación reprogramada correctamente"
    APIGW-->>Portal: confirmación
    Portal-->>Cliente: pantalla de confirmación
```

---

## SC02 — Fuera del plazo permitido (< 24 horas)

```mermaid
sequenceDiagram
    actor Cliente
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msAudit as ms-auditoria

    Cliente->>APIGW: PUT /v1/programacion/{id}/reprogramar
    APIGW->>msProg: reenvía
    msProg->>msProg: horas_restantes = 8h < 24h ✗ PLAZO_VENCIDO
    msProg->>msAudit: INSERT FALLIDO PLAZO_REPROGRAMACION_VENCIDO
    msProg-->>APIGW: 422 "El plazo máximo es de 24 horas antes de la fecha programada"
    APIGW-->>Cliente: rechazo con motivo
```

---

## SC03 — Orden en estado no reprogramable

```mermaid
sequenceDiagram
    actor Cliente
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msOrden as ms-orden-instalacion
    participant msAudit as ms-auditoria

    Cliente->>APIGW: PUT /v1/programacion/{id}/reprogramar
    APIGW->>msProg: reenvía
    msProg->>msOrden: GET orden → estado=INSTALADA ✗
    msProg->>msAudit: INSERT FALLIDO ESTADO_NO_REPROGRAMABLE
    msProg-->>APIGW: 422 "La orden no se encuentra en un estado válido. Contactar a soporte"
    APIGW-->>Cliente: rechazo
```

---

## SC04 — Sin disponibilidad en nueva fecha

```mermaid
sequenceDiagram
    actor Cliente
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msAudit as ms-auditoria

    Cliente->>APIGW: PUT /v1/programacion/{id}/reprogramar (nueva_fecha=2026-07-20)
    APIGW->>msProg: reenvía
    msProg->>msProg: estado ✓, plazo ✓
    msProg->>msProg: nueva_agenda: capacidad_usada >= total ✗ SIN_DISPONIBILIDAD
    msProg->>msAudit: INSERT FALLIDO SIN_DISPONIBILIDAD_NUEVA_FECHA
    msProg-->>APIGW: 422 "No hay disponibilidad para la fecha seleccionada. Elija otra fecha"
    APIGW-->>Cliente: calendario con fechas disponibles
```

---

## SC05 — Error técnico con rollback

```mermaid
sequenceDiagram
    actor Cliente
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msInv as ms-inventario
    participant msAudit as ms-auditoria

    Cliente->>APIGW: PUT /v1/programacion/{id}/reprogramar (datos válidos)
    APIGW->>msProg: reenvía
    msProg->>msProg: validaciones OK ✓
    msProg->>msProg: INICIO TRANSACCIÓN
    msProg->>msInv: liberar + reservar nuevos ✓
    Note over msProg: Error técnico al actualizar PostgreSQL
    msProg->>msProg: ROLLBACK
    msProg->>msInv: revertir liberación + liberar nueva reserva
    msInv-->>msProg: estado restaurado ✓
    msProg->>msAudit: INSERT INCIDENTE_TECNICO + OPERACION_REVERTIDA
    msProg-->>APIGW: 500 "No fue posible reprogramar. Intente nuevamente"
    APIGW-->>Cliente: error, fecha original sin cambios
```
