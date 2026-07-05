# Microservicio: ms-integracion-red

## Descripción
Gestiona la integración de las fuentes de datos de red al bus de eventos del Hub: NMS regionales, logs de red y el inventario Oracle on-premises. Normaliza eventos heterogéneos al esquema canónico, valida fuentes autorizadas, sincroniza la topología de red con el motor de correlación y publica incidentes hacia el ITSM en Azure. Es la puerta de entrada de datos de la Iniciativa 3 (Plataforma de Observabilidad) y cubre completamente RF06.

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate (proceso continuo) + Lambda (normalización event-driven)
- **Ingesta:** Amazon Kinesis Data Streams (eventos de red en tiempo real, alta velocidad)
- **Normalización:** AWS Lambda (transformación por esquema de fuente) + AWS Glue (ETL inventario Oracle)
- **Base de datos:** PostgreSQL (Amazon RDS) — fuentes registradas, esquemas de mapeo, estado integración
- **Integración Oracle:** AWS Glue + JDBC over VPN
- **Integración ITSM Azure:** SQS + adapter REST → Azure API Management
- **Mensajería:** EventBridge + Kinesis + SQS
- **Caché:** ElastiCache (Redis) — estado de fuentes en tiempo real

---

## Base de datos

```sql
-- Fuentes de datos autorizadas (NMS regionales, logs, inventario)
CREATE TABLE fuente_datos (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_fuente       VARCHAR(50) NOT NULL UNIQUE,
    nombre              VARCHAR(150) NOT NULL,
    tipo_fuente         VARCHAR(30) NOT NULL, -- NMS, LOG_RED, INVENTARIO, ITSM
    region              VARCHAR(50),
    endpoint            VARCHAR(500),
    estado              VARCHAR(20) NOT NULL DEFAULT 'REGISTRADA',
    ultima_senal        TIMESTAMPTZ,
    umbral_silencio_min INTEGER     NOT NULL DEFAULT 5, -- minutos sin señal = alerta
    credencial_id       VARCHAR(100), -- referencia en Secrets Manager
    fecha_registro      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_estado_fuente CHECK (estado IN (
        'REGISTRADA','INTEGRADA','SIN_SENAL','DESHABILITADA'))
);

-- Esquemas de mapeo por fuente (normalización)
CREATE TABLE esquema_mapeo (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fuente_id       UUID        NOT NULL REFERENCES fuente_datos(id),
    version         VARCHAR(10) NOT NULL DEFAULT '1.0',
    campo_origen    VARCHAR(100) NOT NULL,
    campo_canonico  VARCHAR(100) NOT NULL, -- campo en esquema canónico
    transformacion  TEXT,                  -- expresión de transformación (JSONPath, regex)
    obligatorio     BOOLEAN     NOT NULL DEFAULT FALSE,
    activo          BOOLEAN     NOT NULL DEFAULT TRUE
);

-- Registro de eventos recibidos (trazabilidad)
CREATE TABLE evento_ingesta (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fuente_id           UUID        NOT NULL REFERENCES fuente_datos(id),
    evento_externo_id   VARCHAR(150),
    payload_original    JSONB       NOT NULL,
    payload_canonico    JSONB,
    estado              VARCHAR(20) NOT NULL DEFAULT 'RECIBIDO',
    motivo_rechazo      TEXT,
    fecha_recepcion     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_procesamiento TIMESTAMPTZ,
    correlation_id      VARCHAR(100),
    CONSTRAINT chk_estado_evento CHECK (estado IN (
        'RECIBIDO','NORMALIZADO','RECHAZADO','ENVIADO_CORRELACION'))
);

-- Registro de sincronizaciones de inventario
CREATE TABLE sync_inventario (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha_inicio        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_fin           TIMESTAMPTZ,
    total_nodos         INTEGER     NOT NULL DEFAULT 0,
    nodos_actualizados  INTEGER     NOT NULL DEFAULT 0,
    nodos_nuevos        INTEGER     NOT NULL DEFAULT 0,
    estado              VARCHAR(20) NOT NULL DEFAULT 'EN_PROCESO',
    error_detalle       TEXT,
    CONSTRAINT chk_estado_sync CHECK (estado IN ('EN_PROCESO','EXITOSA','FALLIDA'))
);

-- Publicaciones al ITSM (trazabilidad de integración Azure)
CREATE TABLE itsm_publicacion (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incidente_id        UUID        NOT NULL, -- referencia a ms-correlacion
    payload_enviado     JSONB       NOT NULL,
    estado              VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    intentos            INTEGER     NOT NULL DEFAULT 0,
    itsm_ticket_id      VARCHAR(100),
    fecha_envio         TIMESTAMPTZ,
    fecha_confirmacion  TIMESTAMPTZ,
    error_detalle       TEXT,
    CONSTRAINT chk_estado_pub CHECK (estado IN (
        'PENDIENTE','ENVIADO','CONFIRMADO','FALLIDO','EN_REINTENTO'))
);

-- Métricas de calidad de datos por fuente
CREATE TABLE metrica_calidad_fuente (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fuente_id           UUID        NOT NULL REFERENCES fuente_datos(id),
    fecha_ventana       DATE        NOT NULL,
    total_eventos       INTEGER     NOT NULL DEFAULT 0,
    eventos_aceptados   INTEGER     NOT NULL DEFAULT 0,
    eventos_rechazados  INTEGER     NOT NULL DEFAULT 0,
    tasa_rechazo_pct    DECIMAL(5,2) GENERATED ALWAYS AS
        (CASE WHEN total_eventos > 0
              THEN ROUND(eventos_rechazados * 100.0 / total_eventos, 2)
              ELSE 0 END) STORED,
    CONSTRAINT uq_metrica UNIQUE(fuente_id, fecha_ventana)
);

CREATE INDEX idx_fuente_estado   ON fuente_datos(estado);
CREATE INDEX idx_evento_fuente   ON evento_ingesta(fuente_id, fecha_recepcion DESC);
CREATE INDEX idx_evento_estado   ON evento_ingesta(estado);
CREATE INDEX idx_itsm_estado     ON itsm_publicacion(estado);
```

---

## Funcionalidades

---

### F01 — Validar y autorizar fuente de datos

**Descripción:** Verifica que los eventos entrantes provengan de una fuente registrada y autorizada. Rechaza eventos de fuentes desconocidas y registra el intento en la bitácora de seguridad.

**Contrato de entrada (evento Kinesis — punto de ingesta):**
```json
{
  "fuente_id": "NMS-REGIONAL-NORTE",
  "credencial_token": "Bearer eyJhbGci...",
  "evento_externo_id": "EVT-2026-001",
  "payload": { "alarm_id": "A-001", "node": "OLT-N-03", "severity": "critical" },
  "timestamp": "2026-07-04T18:00:00-05:00"
}
```

**Contrato de salida — autorizado:**
```json
{ "autorizado": true, "fuente_id": "NMS-REGIONAL-NORTE", "evento_id": "uuid" }
```

**Contrato de salida — rechazado (fuente no registrada):**
```json
{ "autorizado": false, "motivo": "FUENTE_NO_REGISTRADA",
  "mensaje": "Fuente no autorizada. Evento rechazado y registrado en bitácora de seguridad." }
```

**Pseudocódigo:**
```
FUNCIÓN validarFuente(evento_entrada):
  fuente = BUSCAR fuente_datos WHERE codigo = evento.fuente_id

  SI no existe fuente:
    INSERTAR evento_ingesta (estado=RECHAZADO, motivo=FUENTE_NO_REGISTRADA)
    REGISTRAR en audit_log (tipo=ACCESO_NO_AUTORIZADO)
    PUBLICAR alerta "FUENTE_NO_AUTORIZADA" en CloudWatch → equipo seguridad
    RETORNAR { autorizado: false }

  SI fuente.estado = 'DESHABILITADA':
    INSERTAR evento_ingesta (estado=RECHAZADO, motivo=FUENTE_DESHABILITADA)
    RETORNAR { autorizado: false }

  // Validar credencial en Secrets Manager
  credencial_ok = VERIFICAR token contra Secrets Manager[fuente.credencial_id]
  SI NOT credencial_ok:
    REGISTRAR intento fallido en audit_log
    RETORNAR { autorizado: false }

  ACTUALIZAR fuente.ultima_senal = NOW(), estado = 'INTEGRADA'
  RETORNAR { autorizado: true }
```

**Features:** RF06-SC05 (fuente no autorizada)
**Lineamientos:** SEG-03, SEG-07, SEG-08, SEG-10, OBS-01, OBS-02, RNF-003

---

### F02 — Normalizar evento al esquema canónico

**Descripción:** Transforma el evento recibido desde cualquier NMS (con formato propio) al esquema canónico de alarma del Hub. Soporta múltiples esquemas de mapeo configurables por fuente. Rechaza eventos con campos obligatorios ausentes.

**Esquema canónico de alarma:**
```json
{
  "alarma_externa_id": "string",
  "fuente_id": "string",
  "codigo_nodo": "string",
  "severidad": "CRITICA|MAYOR|MENOR|INFORMATIVA",
  "tipo_alarma": "string",
  "descripcion": "string",
  "timestamp": "ISO-8601",
  "region": "string",
  "correlation_id": "string"
}
```

**Pseudocódigo:**
```
FUNCIÓN normalizarEvento(evento_entrada, fuente_id):
  esquemas = OBTENER esquema_mapeo WHERE fuente_id = fuente_id AND activo = TRUE

  evento_canonico = {}
  PARA CADA campo_mapping EN esquemas:
    valor = EXTRAER evento_entrada[campo_mapping.campo_origen]
    SI campo_mapping.transformacion:
      valor = APLICAR transformacion(valor)
    evento_canonico[campo_mapping.campo_canonico] = valor

  // Validar campos obligatorios
  campos_obligatorios = [codigo_nodo, severidad, tipo_alarma, fuente_id]
  PARA CADA campo EN campos_obligatorios:
    SI evento_canonico[campo] IS NULL:
      INSERTAR evento_ingesta (estado=RECHAZADO, motivo="CAMPO_OBLIGATORIO: {campo}")
      ENVIAR a cola-rechazados SQS
      ACTUALIZAR metrica_calidad_fuente.eventos_rechazados += 1
      RETORNAR { normalizado: false }

  ACTUALIZAR evento_ingesta.payload_canonico = evento_canonico, estado=NORMALIZADO
  ACTUALIZAR metrica_calidad_fuente.eventos_aceptados += 1

  // Publicar al Kinesis de alarmas para ms-correlacion-incidentes
  PUBLICAR evento_canonico en Kinesis stream "alarmas-correlacion"
  RETORNAR { normalizado: true, evento_canonico }
```

**Features:** RF06-SC01 (integración exitosa NMS), RF06-SC02 (formatos heterogéneos), RF06-SC06 (campo obligatorio ausente)
**Lineamientos:** ARQ-02, INT-04, INT-05, ESC-05, OBS-01

---

### F03 — Sincronizar inventario Oracle con motor de correlación

**Descripción:** Proceso programado (EventBridge Scheduler) que extrae la topología de red del Oracle on-premises y actualiza la tabla `nodo_red` y `cliente_nodo` en ms-correlacion-incidentes. Preserva la última versión válida si la sincronización falla.

**Trigger:** EventBridge Scheduler (configurable, ej: cada 4 horas)

**Pseudocódigo:**
```
FUNCIÓN sincronizarInventario():
  sync = INSERTAR sync_inventario (estado=EN_PROCESO)

  INTENTAR:
    // Extracción desde Oracle vía Glue Job (JDBC over VPN)
    nodos_oracle = EJECUTAR Glue Job "extract-inventory-oracle"
    // Resultado: lista de nodos con jerarquía, clientes asociados

    SI nodos_oracle IS EMPTY O error_conexion:
      LANZAR excepción ORACLE_NO_DISPONIBLE

    // Validar integridad referencial
    SI nodos_sin_cliente > umbral_anomalia:
      PUBLICAR alerta "INVENTARIO_ANOMALIA_DETECTADA"

    INICIO TRANSACCIÓN
      PARA CADA nodo EN nodos_oracle:
        UPSERT nodo_red (codigo_nodo, tipo, region, padre, estado)
      PARA CADA vinculacion EN nodos_oracle.clientes:
        UPSERT cliente_nodo (cliente_id, nodo_id, tipo, sla)
      ACTUALIZAR sync.estado = EXITOSA, nodos_actualizados, fecha_fin
    FIN TRANSACCIÓN

    PUBLICAR "TOPOLOGIA_ACTUALIZADA" en EventBridge
    PUBLICAR metrica frescura_inventario = NOW() en CloudWatch

  EN CASO DE ERROR:
    // NO actualizar con datos parciales
    ROLLBACK si hay transacción abierta
    ACTUALIZAR sync.estado = FALLIDA, error_detalle
    SI tiempo_sin_sync > umbral_frescura:
      ACTUALIZAR fuente.estado = 'SIN_SENAL' (o marcar como DESACTUALIZADO)
    PUBLICAR alerta "SINCRONIZACION_INVENTARIO_FALLIDA" → CloudWatch → equipo datos
    CONSERVAR última versión válida (sin modificar nodo_red)
```

**Features:** RF06-SC03 (sincronización exitosa), RF06-SC08 (falla sincronización Oracle)
**Lineamientos:** INT-02, INT-03, ESC-05, OBS-03, OBS-04, RNF-001

---

### F04 — Publicar incidente al ITSM (Azure)

**Descripción:** Recibe el evento de incidente creado por ms-correlacion-incidentes y lo publica al sistema ITSM en Azure via API. Garantiza entrega con reintentos exponenciales. No descarta el incidente ante fallo del ITSM.

**Evento de entrada (EventBridge):**
```json
{
  "tipo_evento": "INCIDENTE_MASIVO_ACTIVO",
  "incidente_id": "uuid",
  "codigo_incidente": "INC-2026-0042",
  "nodo_origen": "OLT-NORTE-A03",
  "zona_impactada": "NORTE-QUITO",
  "total_clientes_afectados": 1250,
  "clientes_empresariales": 18,
  "tiempo_estimado": "2 horas",
  "correlation_id": "corr-inc-001"
}
```

**Pseudocódigo:**
```
FUNCIÓN publicarITSM(evento_incidente):
  // Verificar disponibilidad ITSM (circuit breaker)
  SI circuit_breaker_ITSM = ABIERTO:
    ENCOLAR en SQS-itsm-reintentos
    RETORNAR { encolado: true }

  pub = INSERTAR itsm_publicacion (estado=PENDIENTE, payload=evento)

  INTENTAR (timeout=10s):
    respuesta = LLAMAR Azure ITSM API POST /incidents
      { titulo, descripcion, zona, afectados, sla_impactados }
    
    SI respuesta.status = 201:
      ACTUALIZAR pub: estado=CONFIRMADO, itsm_ticket_id=respuesta.id
      ACTUALIZAR ms-correlacion: incidente.itsm_ticket_id = respuesta.id
      RETORNAR { confirmado: true, itsm_ticket_id }

  EN CASO DE ERROR:
    pub.intentos += 1
    SI pub.intentos < 3:
      ENCOLAR en SQS con delay exponencial (30s, 60s, 120s)
      ACTUALIZAR pub.estado = EN_REINTENTO
    SINO:
      ACTUALIZAR pub.estado = FALLIDO
      PUBLICAR alerta "ITSM_PUBLICACION_FALLIDA" → CloudWatch → NOC
      CONSERVAR incidente en sistema interno (no descartar)
```

**Features:** RF06-SC04 (publicación exitosa ITSM), RF06-SC09 (ITSM no disponible)
**Lineamientos:** INT-03, INT-06, INT-08, ESC-07, OBS-04

---

### F05 — Monitorear señal de fuentes integradas

**Descripción:** Proceso continuo que verifica que cada fuente integrada siga publicando eventos dentro del umbral de silencio configurado. Alerta al NOC si una fuente pierde señal.

**Trigger:** CloudWatch Events cada 1 minuto

**Pseudocódigo:**
```
FUNCIÓN monitorearFuentes():
  fuentes_activas = OBTENER fuente_datos WHERE estado = 'INTEGRADA'
  PARA CADA fuente:
    tiempo_sin_senal = DIFERENCIA(NOW(), fuente.ultima_senal) en minutos
    SI tiempo_sin_senal > fuente.umbral_silencio_min:
      ACTUALIZAR fuente.estado = 'SIN_SENAL'
      REGISTRAR ventana_perdida en correlacion_log
      PUBLICAR "FUENTE_SIN_SENAL" en CloudWatch
        → alerta al operador NOC sobre región sin cobertura
      // Al recuperarse: estado → INTEGRADA, recuperar eventos pendientes
```

**Features:** RF06-SC07 (pérdida de conectividad NMS)
**Lineamientos:** OBS-03, OBS-04, INT-03

---

### F06 — Gestionar saturación del bus de eventos

**Descripción:** Monitorea el throughput del Kinesis Data Stream. Ante saturación, aplica control de flujo priorizando eventos críticos sin perder eventos confirmados.

**Pseudocódigo:**
```
FUNCIÓN gestionarSaturacion():
  metricas_kinesis = OBTENER CloudWatch métricas de Kinesis
    (IncomingRecords, WriteProvisionedThroughputExceeded)
  
  SI WriteProvisionedThroughputExceeded > umbral_saturacion:
    // Priorizar eventos CRITICOS — moverlos a shard dedicado
    APLICAR partitionKey = 'CRITICO' para severidad CRITICA
    // Aplicar backpressure a fuentes de menor severidad
    PUBLICAR alerta "KINESIS_SATURACION" → equipo plataforma
    REGISTRAR metricas_pico para ajuste de capacidad (scaling de shards)
```

**Features:** RF06-SC10 (saturación del bus)
**Lineamientos:** ESC-03, ESC-06, ESC-07, ESC-08, OBS-04

---

## Features y escenarios cubiertos (resumen)

| Feature | Escenario | Descripción |
|---------|-----------|-------------|
| RF06 | SC01 | Integración exitosa NMS al bus — F01 + F02 |
| RF06 | SC02 | Normalización formatos heterogéneos — F02 |
| RF06 | SC03 | Sincronización inventario Oracle — F03 |
| RF06 | SC04 | Publicación incidente al ITSM Azure — F04 |
| RF06 | SC05 | Rechazo fuente no autorizada — F01 |
| RF06 | SC06 | Evento con campos obligatorios ausentes — F02 |
| RF06 | SC07 | Pérdida de conectividad NMS — F05 |
| RF06 | SC08 | Falla sincronización Oracle — F03 |
| RF06 | SC09 | ITSM Azure no disponible — F04 |
| RF06 | SC10 | Saturación del bus de eventos — F06 |

## Lineamientos cubiertos (resumen)

| Código | Descripción |
|--------|-------------|
| ARQ-01 | Capa de ingesta y normalización separada del motor de correlación |
| ARQ-02 | Desacoplamiento — normalización independiente de correlación |
| ARQ-03 | Responsabilidad única — integración de fuentes de red |
| INT-01 | API REST versionada para gestión de fuentes |
| INT-02 | Kinesis + EventBridge para integración asíncrona |
| INT-03 | Circuit breaker y reintentos en ITSM Azure |
| INT-04 | Esquema canónico con contrato explícito |
| INT-05 | Versionado de esquemas de mapeo por fuente |
| INT-06 | Idempotencia en normalización por evento_externo_id |
| INT-07 | Desacoplamiento fuentes-correlación vía Kinesis |
| INT-08 | Trazabilidad de intercambio alarma→incidente→ITSM |
| ESC-03 | Lambda escala horizontalmente para normalización |
| ESC-05 | Sincronización de inventario asíncrona y diferible |
| ESC-06 | Control de flujo sin pérdida de eventos |
| ESC-07 | Backpressure ante saturación de Kinesis |
| ESC-08 | Métricas de pico para ajuste de capacidad |
| SEG-03 | Autenticación centralizada de fuentes |
| SEG-07 | Mínimo privilegio — fuentes solo acceden a su tópico |
| SEG-08 | Credenciales NMS en Secrets Manager |
| SEG-10 | Auditoría de fuentes no autorizadas |
| OBS-01 | Logs estructurados con fuente, evento y resultado |
| OBS-02 | Correlation ID desde NMS hasta ITSM |
| OBS-03 | Métricas de calidad de datos por fuente |
| OBS-04 | Alertas ante fuente sin señal, saturación o ITSM fallido |
| OBS-06 | Trazas distribuidas end-to-end desde NMS hasta incidente |
| RNF-001 | Integridad — topología siempre válida para correlación |
| RNF-003 | Seguridad — fuentes no autorizadas rechazadas y alertadas |
| RNF-004 | Auditabilidad — trazabilidad completa del evento desde origen |
