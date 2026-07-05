# Diagrama de Secuencia — RF06: Integración de Fuentes de Red al Bus de Eventos

---

## SC01 — Integración exitosa de NMS regional al bus

```mermaid
sequenceDiagram
    participant NMS as NMS Regional (autorizado)
    participant Kinesis as Kinesis Data Streams
    participant msIntRed as ms-integracion-red (Lambda)
    participant EB as EventBridge
    participant msCorrInc as ms-correlacion-incidentes
    participant msAudit as ms-auditoria

    NMS->>Kinesis: publicar evento (credencial válida, fuente registrada)
    Kinesis->>msIntRed: trigger Lambda
    msIntRed->>msIntRed: F01 validar fuente → INTEGRADA ✓
    msIntRed->>msIntRed: ACTUALIZAR fuente.ultima_senal = NOW()
    msIntRed->>msIntRed: F02 normalizar → esquema canónico ✓
    msIntRed->>msIntRed: INSERTAR evento_ingesta estado=NORMALIZADO
    msIntRed->>msIntRed: registrar fuente, región, timestamp
    msIntRed->>Kinesis: publicar evento canónico "alarmas-correlacion"
    Kinesis->>msCorrInc: evento canónico disponible
    msIntRed->>EB: FUENTE_INTEGRADA (indicador cobertura actualizado)
    EB->>msAudit: INSERT INTEGRACION_EXITOSA
```

---

## SC02 — Normalización de formatos heterogéneos

```mermaid
sequenceDiagram
    participant NMS_A as NMS Operador A (formato propio)
    participant NMS_B as NMS Operador B (formato diferente)
    participant Kinesis as Kinesis
    participant msIntRed as ms-integracion-red (Lambda)
    participant msAudit as ms-auditoria

    NMS_A->>Kinesis: { "alarm_id": "A001", "node_code": "OLT-N01", "sev": 1 }
    NMS_B->>Kinesis: { "eventId": "B002", "elementId": "RTR-S05", "priority": "high" }

    Kinesis->>msIntRed: batch de eventos
    msIntRed->>msIntRed: aplicar esquema_mapeo fuente_A:
      alarm_id → alarma_externa_id
      node_code → codigo_nodo
      sev:1 → severidad:CRITICA
    msIntRed->>msIntRed: aplicar esquema_mapeo fuente_B:
      eventId → alarma_externa_id
      elementId → codigo_nodo
      priority:high → severidad:MAYOR
    msIntRed->>msIntRed: conservar id_original de cada fuente
    msIntRed->>Kinesis: publicar 2 eventos en esquema canónico ✓
    msIntRed->>msAudit: INSERT NORMALIZACION_EXITOSA (2 eventos, 2 formatos)
    Note over msIntRed: NO se descarta ningún evento por diferencia de formato
```

---

## SC03 — Sincronización de inventario Oracle con motor de correlación

```mermaid
sequenceDiagram
    participant Scheduler as EventBridge Scheduler
    participant Glue as AWS Glue Job
    participant Oracle as Inventario Oracle (on-prem)
    participant VPN as VPN / PrivateLink
    participant msIntRed as ms-integracion-red
    participant msCorrInc as ms-correlacion-incidentes
    participant EB as EventBridge
    participant CW as CloudWatch
    participant msAudit as ms-auditoria

    Scheduler->>msIntRed: trigger F03 sincronizarInventario (cada 4h)
    msIntRed->>Glue: ejecutar job extract-inventory-oracle
    Glue->>VPN: conexión JDBC a Oracle
    VPN->>Oracle: SELECT nodos, puertos, clientes, topología
    Oracle-->>VPN: datos topología ✓
    VPN-->>Glue: dataset nodos + clientes
    Glue-->>msIntRed: dataset normalizado

    msIntRed->>msIntRed: validar integridad referencial nodos-clientes
    msIntRed->>msCorrInc: UPSERT nodo_red (nodos actualizados + nuevos)
    msIntRed->>msCorrInc: UPSERT cliente_nodo (vinculaciones)
    msIntRed->>msIntRed: UPDATE sync_inventario estado=EXITOSA
    msIntRed->>CW: métrica frescura_inventario = NOW()
    msIntRed->>EB: TOPOLOGIA_ACTUALIZADA
    EB->>msAudit: INSERT SYNC_INVENTARIO_EXITOSA
```

---

## SC04 — Publicación de incidente al ITSM Azure

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant msIntRed as ms-integracion-red
    participant SQS as SQS ITSM
    participant AzureAPIGW as Azure API Management
    participant ITSM as ITSM Azure
    participant msCorrInc as ms-correlacion-incidentes
    participant msAudit as ms-auditoria

    EB->>msIntRed: INCIDENTE_MASIVO_ACTIVO (incidente_id, zona, clientes)
    msIntRed->>msIntRed: F04 verificar circuit_breaker_ITSM = CERRADO ✓
    msIntRed->>msIntRed: INSERT itsm_publicacion estado=PENDIENTE
    msIntRed->>AzureAPIGW: POST /incidents (titulo, descripcion, afectados, sla)
    AzureAPIGW->>ITSM: crear incidente maestro
    ITSM-->>AzureAPIGW: 201 itsm_ticket_id="INC-AZ-20260704-001"
    AzureAPIGW-->>msIntRed: ✓
    msIntRed->>msIntRed: UPDATE itsm_publicacion estado=CONFIRMADO
    msIntRed->>msCorrInc: PATCH incidente.itsm_ticket_id = INC-AZ-20260704-001
    msIntRed->>msAudit: INSERT ITSM_PUBLICACION_EXITOSA
    Note over msIntRed: trazabilidad: alarma → incidente interno → ITSM ticket
```

---

## SC05 — Rechazo de fuente no autorizada

```mermaid
sequenceDiagram
    participant SistemaDesconocido as Sistema no registrado
    participant Kinesis as Kinesis
    participant msIntRed as ms-integracion-red
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor Seguridad

    SistemaDesconocido->>Kinesis: publicar eventos (sin credencial válida)
    Kinesis->>msIntRed: trigger Lambda
    msIntRed->>msIntRed: F01 buscar fuente → NOT FOUND ✗
    msIntRed->>msIntRed: INSERT evento_ingesta estado=RECHAZADO FUENTE_NO_REGISTRADA
    msIntRed->>CW: alerta FUENTE_NO_AUTORIZADA
    CW-->>Seguridad: 🔔 "Intento de publicación desde fuente no autorizada"
    msIntRed->>msAudit: INSERT ACCESO_NO_AUTORIZADO (tipo_seguridad)
    Note over msIntRed: eventos NO enviados a normalización ni correlación
```

---

## SC06 — Evento con campos obligatorios ausentes

```mermaid
sequenceDiagram
    participant NMS as NMS Registrado
    participant Kinesis as Kinesis
    participant msIntRed as ms-integracion-red
    participant SQS as SQS Cola Rechazados
    participant msAudit as ms-auditoria

    NMS->>Kinesis: { "alarm_id": "A003" } -- falta codigo_nodo y severidad
    Kinesis->>msIntRed: trigger Lambda
    msIntRed->>msIntRed: F01 fuente autorizada ✓
    msIntRed->>msIntRed: F02 normalizar → campo obligatorio "codigo_nodo" ausente ✗
    msIntRed->>SQS: enviar a cola-rechazados con motivo
    msIntRed->>msIntRed: UPDATE metrica_calidad_fuente.eventos_rechazados += 1
    msIntRed->>msAudit: INSERT EVENTO_RECHAZADO (fuente, campo_faltante)
    Note over msIntRed: evento NO enviado a correlación
```

---

## SC07 — Pérdida de conectividad con NMS regional

```mermaid
sequenceDiagram
    participant Scheduler as CloudWatch Events (1 min)
    participant msIntRed as ms-integracion-red
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor OperadorNOC

    Scheduler->>msIntRed: F05 monitorearFuentes()
    msIntRed->>msIntRed: NMS-REGIONAL-SUR → ultima_senal hace 8 min > umbral(5 min)
    msIntRed->>msIntRed: UPDATE fuente.estado = SIN_SENAL
    msIntRed->>msIntRed: registrar ventana_perdida en correlacion_log
    msIntRed->>CW: alerta FUENTE_SIN_SENAL (region=SUR)
    CW-->>OperadorNOC: 🔔 "NMS región SUR sin señal desde las 18:00"
    msIntRed->>msAudit: INSERT FUENTE_SIN_SENAL
    Note over msIntRed: Al recuperarse: estado → INTEGRADA, recuperar eventos pendientes
```

---

## SC08 — Falla en sincronización del inventario Oracle

```mermaid
sequenceDiagram
    participant Scheduler as EventBridge Scheduler
    participant msIntRed as ms-integracion-red
    participant Glue as AWS Glue Job
    participant Oracle as Oracle On-Premises
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor EquipoDatos

    Scheduler->>msIntRed: trigger sincronizarInventario
    msIntRed->>Glue: ejecutar job
    Glue->>Oracle: JDBC connection
    Oracle-->>Glue: Error (BD no disponible)
    Glue-->>msIntRed: FALLO conexión Oracle

    msIntRed->>msIntRed: ROLLBACK — NO actualizar topología con datos parciales
    msIntRed->>msIntRed: UPDATE sync.estado = FALLIDA
    msIntRed->>msIntRed: conservar última versión válida de nodo_red (sin cambios)
    msIntRed->>msIntRed: verificar tiempo_sin_sync > umbral_frescura → marcar DESACTUALIZADO
    msIntRed->>CW: alerta SINCRONIZACION_INVENTARIO_FALLIDA
    CW-->>EquipoDatos: 🔔 "Sincronización Oracle fallida. Topología desactualizada"
    msIntRed->>msAudit: INSERT SYNC_FALLIDA
```

---

## SC09 — ITSM Azure no disponible al publicar incidente

```mermaid
sequenceDiagram
    participant msIntRed as ms-integracion-red
    participant AzureAPIGW as Azure API Management
    participant SQS as SQS ITSM Reintentos
    participant CW as CloudWatch
    participant msAudit as ms-auditoria
    actor OperadorNOC

    msIntRed->>AzureAPIGW: POST /incidents
    AzureAPIGW-->>msIntRed: Error 503 (no disponible) intento 1
    msIntRed->>SQS: encolar con delay 30s
    Note over SQS: reintento 2 delay 60s → falla
    Note over SQS: reintento 3 delay 120s → falla
    msIntRed->>msIntRed: UPDATE itsm_publicacion estado=FALLIDO
    msIntRed->>msIntRed: conservar incidente en sistema interno (NO descartar)
    msIntRed->>CW: alerta ITSM_NO_DISPONIBLE
    CW-->>OperadorNOC: 🔔 "ITSM Azure no disponible. Incidente INC-2026-0042 en cola"
    msIntRed->>msAudit: INSERT ITSM_PUBLICACION_FALLIDA
```

---

## SC10 — Saturación del bus de eventos por pico de tráfico

```mermaid
sequenceDiagram
    participant NMS_Multi as NMS Múltiples (pico)
    participant Kinesis as Kinesis Data Streams
    participant CW as CloudWatch
    participant msIntRed as ms-integracion-red
    participant msAudit as ms-auditoria
    actor EquipoPlataforma

    NMS_Multi->>Kinesis: volumen > capacidad contratada
    Kinesis->>CW: métrica WriteProvisionedThroughputExceeded > umbral
    CW->>msIntRed: alarma KINESIS_SATURACION
    msIntRed->>msIntRed: F06 aplicar control de flujo:
    msIntRed->>Kinesis: priorizar severidad CRITICA → shard dedicado
    msIntRed->>Kinesis: backpressure en eventos MENOR/INFORMATIVA
    msIntRed->>CW: alerta SATURACION_BUS → equipo plataforma
    CW-->>EquipoPlataforma: 🔔 "Bus saturado. Escalar shards Kinesis"
    msIntRed->>msAudit: INSERT METRICA_PICO (para ajuste de capacidad)
    Note over Kinesis: eventos confirmados NO se pierden (at-least-once)
```
