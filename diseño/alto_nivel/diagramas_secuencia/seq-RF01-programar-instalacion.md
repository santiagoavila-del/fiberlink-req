# Diagrama de Secuencia — RF01: Programar Instalación del Servicio de Internet

---

## SC01 — Programación exitosa

```mermaid
sequenceDiagram
    actor Operador
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msOrden as ms-orden-instalacion
    participant msInv as ms-inventario
    participant EB as EventBridge
    participant msNotif as ms-notificaciones
    participant msAudit as ms-auditoria

    Operador->>APIGW: POST /v1/programacion (orden_id, fecha, cuadrilla, permisos=true, ruta=true)
    APIGW->>msProg: reenvía (token validado)
    msProg->>msOrden: GET /v1/ordenes/{orden_id}
    msOrden-->>msProg: orden estado=CREADA ✓
    msProg->>msProg: validar permisos ✓, ruta ✓, cuadrilla disponible ✓ (Redis)
    msProg->>msInv: GET /v1/inventario/disponibilidad?orden_id
    msInv-->>msProg: materiales_disponibles=true ✓
    msProg->>msInv: POST /v1/inventario/reservas (ONT, router, materiales)
    msInv-->>msProg: reserva_confirmada ✓
    msProg->>msProg: TRANSACCIÓN: incrementar agenda, insertar programacion=CONFIRMADA
    msProg->>msOrden: PATCH /estado → PROGRAMADA
    msProg->>EB: INSTALACION_PROGRAMADA
    EB->>msNotif: notificar cliente (email + WhatsApp)
    EB->>msAudit: INSERT audit_evento EXITOSO
    msProg-->>APIGW: 201 "Instalación programada correctamente"
    APIGW-->>Operador: confirmación
```

---

## SC02 — Cuadrilla no disponible

```mermaid
sequenceDiagram
    actor Operador
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msOrden as ms-orden-instalacion
    participant msAudit as ms-auditoria

    Operador->>APIGW: POST /v1/programacion (fecha sin cuadrilla)
    APIGW->>msProg: reenvía
    msProg->>msOrden: GET orden ✓
    msProg->>msProg: verificar cuadrilla Redis → capacidad_usada >= total ✗
    msProg->>msAudit: INSERT FALLIDO CUADRILLA_NO_DISPONIBLE
    msProg-->>APIGW: 422 "No hay cuadrilla disponible. Por favor elija otra fecha"
    APIGW-->>Operador: rechazo
```

---

## SC03 — Materiales insuficientes

```mermaid
sequenceDiagram
    actor Operador
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msInv as ms-inventario
    participant msAudit as ms-auditoria

    Operador->>APIGW: POST /v1/programacion (cuadrilla OK, sin materiales)
    APIGW->>msProg: reenvía
    msProg->>msProg: cuadrilla ✓, permisos ✓
    msProg->>msInv: GET disponibilidad
    msInv-->>msProg: materiales_disponibles=false (ONT: 0)
    msProg->>msAudit: INSERT FALLIDO MATERIALES_INSUFICIENTES
    msProg-->>APIGW: 422 "Materiales insuficientes en inventario"
    APIGW-->>Operador: rechazo
```

---

## SC04 — Permisos no obtenidos

```mermaid
sequenceDiagram
    actor Operador
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msAudit as ms-auditoria

    Operador->>APIGW: POST /v1/programacion (permisos_obtenidos=false)
    APIGW->>msProg: reenvía
    msProg->>msProg: validar permisos_obtenidos = false ✗
    msProg->>msAudit: INSERT FALLIDO PERMISOS_NO_OBTENIDOS
    msProg-->>APIGW: 422 "Los permisos de instalación son requeridos antes de programar"
    APIGW-->>Operador: rechazo
```

---

## SC05 — Error técnico con rollback

```mermaid
sequenceDiagram
    actor Operador
    participant APIGW as API Gateway
    participant msProg as ms-programacion-instalacion
    participant msInv as ms-inventario
    participant EB as EventBridge
    participant msAudit as ms-auditoria

    Operador->>APIGW: POST /v1/programacion (todos los datos válidos)
    APIGW->>msProg: reenvía
    msProg->>msInv: reservar equipos ✓
    msProg->>msProg: INICIO TRANSACCIÓN
    Note over msProg: Error técnico en PostgreSQL
    msProg->>msProg: ROLLBACK
    msProg->>msInv: DELETE reservas (liberar)
    EB->>msAudit: INSERT OPERACION_REVERTIDA + INCIDENTE_TECNICO
    msProg-->>APIGW: 500 "No fue posible programar la instalación. Intente nuevamente"
    APIGW-->>Operador: error
```
