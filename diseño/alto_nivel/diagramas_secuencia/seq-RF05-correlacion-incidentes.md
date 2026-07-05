# Diagrama de Secuencia — RF05: Correlación de Incidentes de Red con Clientes Afectados

---

## SC01 — Falla masiva agrupada en un solo incidente (< 5 minutos)

```mermaid
sequenceDiagram
    participant NMS as NMS Regional
    participant Kinesis as Kinesis Data Streams
    participant msIntRed as ms-integracion-red
    participant msCorrInc as ms-correlacion-incidentes
    participant EB as EventBridge
    participant ITSM as ITSM Azure (SQS adapter)
    participant msAudit as ms-auditoria

    NMS->>Kinesis: miles de alarmas (fibra cortada OLT-NORTE-A03)
    Kinesis->>msIntRed: batch de alarmas (trigger Lambda)
    msIntRed->>msIntRed: F01 deduplicar: Redis → solo 1 alarma nueva por nodo/tipo
    msIntRed->>msIntRed: F02 normalizar al esquema canónico
    msIntRed->>Kinesis: publicar alarma canónica "alarmas-correlacion"

    Kinesis->>msCorrInc: alarma canónica OLT-NORTE-A03 CRITICA
    msCorrInc->>msCorrInc: F02 traversal topología → nodo_origen = OLT-NORTE-A03
    msCorrInc->>msCorrInc: calcular clientes = 1250 (18 empresariales con SLA)
    msCorrInc->>msCorrInc: total > umbral(50) → crear incidente maestro
    msCorrInc->>msCorrInc: INSERT incidente_maestro INC-2026-0042 estado=ACTIVO
    msCorrInc->>msCorrInc: INSERT 1250 incidente_cliente
    msCorrInc->>EB: INCIDENTE_MASIVO_ACTIVO (< 5 minutos desde primera alarma)
    EB->>ITSM: SQS → publicar incidente maestro en ITSM Azure
    EB->>msAudit: INSERT INCIDENTE_CREADO EXITOSO
```

---

## SC02 — Notificación proactiva a clientes afectados

```mermaid
sequenceDiagram
    actor OperadorNOC
    participant APIGW as API Gateway
    participant msCorrInc as ms-correlacion-incidentes
    participant EB as EventBridge
    participant msNotif as ms-notificaciones
    participant Portal as Portal Cliente
    participant IVR as IVR On-Premises
    participant msAudit as ms-auditoria
    actor Cliente

    OperadorNOC->>APIGW: POST /v1/incidentes/{id}/confirmar (tiempo_estimado="2 horas")
    APIGW->>msCorrInc: reenvía
    msCorrInc->>msCorrInc: ACTUALIZAR incidente estado=CONFIRMADO
    msCorrInc->>EB: INCIDENTE_CONFIRMADO (lista clientes afectados, zona, tiempo)
    EB->>msNotif: INCIDENTE_MASIVO_ACTIVO
    msNotif->>msNotif: F02 iterar 1250 clientes
    msNotif-->>Cliente: 📧📱 email + WhatsApp (aviso falla + tiempo estimado)
    msNotif->>Portal: push notification falla masiva zona NORTE-QUITO
    msNotif->>IVR: actualizar mensaje zona impactada
    msNotif->>msNotif: registrar hora_envio por cliente en DynamoDB
    EB->>msAudit: INSERT CLIENTES_NOTIFICADOS EXITOSO
    msCorrInc-->>APIGW: 200 "Notificaciones proactivas en proceso"
    APIGW-->>OperadorNOC: confirmación
```

---

## SC03 — Cliente llama al call center y recibe info sin agente

```mermaid
sequenceDiagram
    actor Cliente
    participant IVR as IVR On-Premises
    participant msCorrInc as ms-correlacion-incidentes

    Cliente->>IVR: llama al call center (número reconocido)
    IVR->>msCorrInc: GET /v1/incidentes/cliente/{cliente_id}?estado=ACTIVO
    msCorrInc-->>IVR: incidente activo INC-2026-0042, tiempo_estimado="2 horas"
    IVR-->>Cliente: "Detectamos una falla en su zona. Tiempo estimado de reparación: 2 horas"
    IVR-->>Cliente: "¿Desea recibir actualizaciones por WhatsApp? Marque 1"
    Cliente->>IVR: marca 1
    IVR->>msCorrInc: POST suscribir cliente a actualizaciones
    msCorrInc-->>IVR: suscripción registrada ✓
```

---

## SC04 — Cierre del incidente con resolución en cascada

```mermaid
sequenceDiagram
    actor OperadorNOC
    participant APIGW as API Gateway
    participant msCorrInc as ms-correlacion-incidentes
    participant SQS as SQS ITSM
    participant ITSM as ITSM Azure
    participant EB as EventBridge
    participant msNotif as ms-notificaciones
    participant Kinesis as Kinesis → Redshift
    participant PowerBI as Power BI Azure
    participant msAudit as ms-auditoria
    actor Cliente

    OperadorNOC->>APIGW: POST /v1/incidentes/{id}/resolver (reparación verificada)
    APIGW->>msCorrInc: reenvía
    msCorrInc->>msCorrInc: TRANSACCIÓN: estado=RESUELTO, duracion=185min
    msCorrInc->>SQS: encolar cierre tickets hijos (ITSM)
    SQS->>ITSM: cerrar tickets hijos vinculados ✓
    msCorrInc->>EB: INCIDENTE_RESUELTO (lista clientes, duracion, sla_impactados)
    EB->>msNotif: enviar notificación de restablecimiento
    msNotif-->>Cliente: 📧📱 "Su servicio ha sido restablecido. Lamentamos la interrupción"
    EB->>Kinesis: publicar KPIs {duracion=185min, afectados=1250, sla=18}
    Kinesis->>Redshift: cargar métricas incidente
    Redshift->>PowerBI: actualizar tablero ejecutivo
    EB->>msAudit: INSERT INCIDENTE_CERRADO + DURACION_SLA EXITOSO
    msCorrInc-->>APIGW: 200 "Incidente cerrado. Tickets hijos cerrados: 47"
    APIGW-->>OperadorNOC: confirmación
```

---

## SC05 — Alarma sin correlación (inventario desactualizado)

```mermaid
sequenceDiagram
    participant Kinesis as Kinesis
    participant msCorrInc as ms-correlacion-incidentes
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor OperadorNOC

    Kinesis->>msCorrInc: alarma nodo "OLT-SUR-X99" (no existe en topología)
    msCorrInc->>msCorrInc: F01 BUSCAR nodo_red WHERE codigo=OLT-SUR-X99 → NOT FOUND
    msCorrInc->>msCorrInc: INSERT alarma estado=PENDIENTE_MANUAL
    msCorrInc->>CW: publicar alerta NODO_NO_EN_TOPOLOGIA
    CW-->>OperadorNOC: 🔔 alerta "Nodo OLT-SUR-X99 no encontrado en inventario"
    msCorrInc->>msAudit: INSERT ALARMA_SIN_CORRELACION + discrepancia inventario
    Note over msCorrInc: NO se crea incidente maestro automáticamente
```

---

## SC06 — Descarte de eventos duplicados

```mermaid
sequenceDiagram
    participant Kinesis as Kinesis
    participant msIntRed as ms-integracion-red
    participant Redis as ElastiCache Redis
    participant msAudit as ms-auditoria

    Kinesis->>msIntRed: alarma #1 OLT-NORTE-A03 CRITICA
    msIntRed->>Redis: SET "ALARMA:NMS-NORTE:OLT-NORTE-A03:FIBRA_CORTADA" TTL=600s
    Redis-->>msIntRed: nueva → procesar

    Kinesis->>msIntRed: alarma #2 OLT-NORTE-A03 CRITICA (duplicado)
    msIntRed->>Redis: GET clave → existe (id=alarma-001)
    msIntRed->>msIntRed: UPDATE alarma.contador_ocurrencias += 1 (= 2)
    msIntRed->>msAudit: INSERT DUPLICADO_DESCARTADO (contador=2)
    Note over msIntRed: NO genera nueva alarma ni nuevo incidente
```

---

## SC07 — Falla en entrega de notificaciones proactivas

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant msNotif as ms-notificaciones
    participant SES as Amazon SES
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor OperadorNOC

    EB->>msNotif: INCIDENTE_CONFIRMADO (1250 clientes)
    msNotif->>SES: enviar emails
    SES-->>msNotif: Error 503 (servicio no disponible)
    msNotif->>msNotif: intentos=1/3 → reencolar con backoff
    Note over msNotif: reintento 2 → falla, reintento 3 → falla
    msNotif->>msNotif: FALLIDA_DEFINITIVA (max reintentos)
    msNotif->>CW: alerta NOTIFICACION_INCIDENTE_FALLIDA
    CW-->>OperadorNOC: 🔔 "No se pudo notificar a clientes del incidente INC-2026-0042"
    msNotif->>msAudit: INSERT INCIDENTE_TECNICO_NOTIFICACION
    Note over msNotif: clientes NO marcados como notificados
```

---

## SC08 — Umbral no alcanzado (falla localizada)

```mermaid
sequenceDiagram
    participant Kinesis as Kinesis
    participant msCorrInc as ms-correlacion-incidentes
    participant msAudit as ms-auditoria

    Kinesis->>msCorrInc: alarma nodo CTO-BARRIO-07
    msCorrInc->>msCorrInc: calcular clientes afectados = 3
    msCorrInc->>msCorrInc: 3 < umbral(50) → NO crear incidente maestro
    msCorrInc->>msCorrInc: UPDATE alarma.estado = CORRELACIONADA (individual)
    msCorrInc->>msAudit: INSERT UMBRAL_NO_ALCANZADO (3 clientes, visible soporte)
    Note over msCorrInc: alarma individual disponible para soporte nivel 1
```

---

## SC09 — Error técnico al crear incidente maestro

```mermaid
sequenceDiagram
    participant Kinesis as Kinesis
    participant msCorrInc as ms-correlacion-incidentes
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor OperadorNOC

    Kinesis->>msCorrInc: alarma masiva válida (1250 clientes)
    msCorrInc->>msCorrInc: correlación ✓, clientes calculados ✓
    msCorrInc->>msCorrInc: INICIO TRANSACCIÓN crear incidente
    Note over msCorrInc: Error técnico al insertar en PostgreSQL
    msCorrInc->>msCorrInc: ROLLBACK
    msCorrInc->>msCorrInc: mantener alarmas correlacionadas en cola reproceso
    msCorrInc->>CW: alerta FALLO_CREACION_INCIDENTE
    CW-->>OperadorNOC: 🔔 "Error al crear incidente. Alarmas en cola de reproceso"
    msCorrInc->>msAudit: INSERT INCIDENTE_TECNICO_PLATAFORMA
    Note over msCorrInc: incidente NO marcado como creado
```
