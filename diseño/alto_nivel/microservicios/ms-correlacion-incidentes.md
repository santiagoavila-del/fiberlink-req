# Microservicio: ms-correlacion-incidentes

## Descripción
Motor de correlación que agrupa alarmas de red en incidentes maestros, identifica el origen más probable de la falla, calcula los clientes afectados con base en la topología, deduplica eventos, abre incidentes en el ITSM (Azure) y coordina el ciclo de vida del incidente hasta su cierre con resolución en cascada. Es el corazón de la Iniciativa 3 (Plataforma de Observabilidad) y de RF05.

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate (proceso continuo, alta disponibilidad)
- **Base de datos:** PostgreSQL (Amazon RDS) — incidentes, topología, afectados
- **Caché:** ElastiCache (Redis) — deduplicación de eventos en ventana temporal
- **Mensajería:** Amazon Kinesis Data Streams (ingesta de alarmas en tiempo real) + EventBridge (publicación de incidentes)
- **Integración ITSM:** Azure Service Management API vía SQS + adapter
- **Análisis:** Amazon OpenSearch (búsqueda de alarmas correlacionadas)
- **BI:** Amazon Kinesis → Amazon Redshift → Power BI Azure

---

## Base de datos

```sql
-- Topología de red (sincronizada desde inventario Oracle)
CREATE TABLE nodo_red (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_nodo     VARCHAR(50) NOT NULL UNIQUE,
    nombre          VARCHAR(150) NOT NULL,
    tipo_nodo       VARCHAR(30) NOT NULL, -- OLT, SPLITTER, CTO, BRAS, ROUTER_CORE
    region          VARCHAR(50),
    zona            VARCHAR(50),
    padre_nodo_id   UUID        REFERENCES nodo_red(id), -- jerarquía de red
    estado          VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    ultima_sync     TIMESTAMPTZ,
    fuente_origen   VARCHAR(50) -- NMS que lo reportó
);

-- Clientes por nodo (qué clientes dependen de cada nodo)
CREATE TABLE cliente_nodo (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          VARCHAR(50) NOT NULL,
    nodo_id             UUID        NOT NULL REFERENCES nodo_red(id),
    tipo_cliente        VARCHAR(20) NOT NULL, -- RESIDENCIAL, EMPRESARIAL
    sla_activo          BOOLEAN     NOT NULL DEFAULT FALSE,
    contrato_id         VARCHAR(30),
    fecha_vinculacion   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cliente_nodo UNIQUE(cliente_id, nodo_id)
);

-- Alarmas recibidas (raw, antes de correlación)
CREATE TABLE alarma (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    alarma_externa_id VARCHAR(100) NOT NULL, -- ID original en NMS
    fuente_id       VARCHAR(50) NOT NULL,   -- NMS que la originó
    nodo_id         UUID        REFERENCES nodo_red(id),
    severidad       VARCHAR(20) NOT NULL,   -- CRITICA, MAYOR, MENOR, INFORMATIVA
    tipo_alarma     VARCHAR(60) NOT NULL,
    descripcion     TEXT,
    estado          VARCHAR(30) NOT NULL DEFAULT 'RECIBIDA',
    contador_ocurrencias INTEGER NOT NULL DEFAULT 1,
    incidente_id    UUID,                   -- FK a incidente_maestro si correlacionada
    fecha_primera   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_ultima    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id  VARCHAR(100),
    CONSTRAINT chk_estado_alarma CHECK (estado IN (
        'RECIBIDA','CORRELACIONADA','PENDIENTE_MANUAL','DESCARTADA'))
);

-- Incidentes maestros
CREATE TABLE incidente_maestro (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_incidente        VARCHAR(30) NOT NULL UNIQUE,
    nodo_origen_id          UUID        REFERENCES nodo_red(id),
    tipo_falla              VARCHAR(60),
    descripcion             TEXT,
    zona_impactada          VARCHAR(100),
    total_clientes_afectados INTEGER    NOT NULL DEFAULT 0,
    clientes_empresariales  INTEGER     NOT NULL DEFAULT 0,
    estado                  VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    itsm_ticket_id          VARCHAR(100), -- ID en el sistema ITSM Azure
    tiempo_estimado_reparacion VARCHAR(50),
    fecha_apertura          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_confirmacion      TIMESTAMPTZ,
    fecha_resolucion        TIMESTAMPTZ,
    duracion_minutos        INTEGER,       -- calculado al cerrar
    correlation_id          VARCHAR(100),
    CONSTRAINT chk_estado_inc CHECK (estado IN (
        'ACTIVO','CONFIRMADO','EN_RESOLUCION','RESUELTO','CANCELADO'))
);

-- Clientes afectados por incidente
CREATE TABLE incidente_cliente (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incidente_id        UUID        NOT NULL REFERENCES incidente_maestro(id),
    cliente_id          VARCHAR(50) NOT NULL,
    tipo_cliente        VARCHAR(20) NOT NULL,
    sla_activo          BOOLEAN     NOT NULL DEFAULT FALSE,
    notificado          BOOLEAN     NOT NULL DEFAULT FALSE,
    fecha_notificacion  TIMESTAMPTZ,
    CONSTRAINT uq_inc_cliente UNIQUE(incidente_id, cliente_id)
);

-- Tickets hijos en ITSM vinculados al incidente maestro
CREATE TABLE itsm_ticket (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incidente_id        UUID        NOT NULL REFERENCES incidente_maestro(id),
    itsm_ticket_id      VARCHAR(100) NOT NULL,
    tipo_ticket         VARCHAR(20) NOT NULL, -- MAESTRO, HIJO
    estado_itsm         VARCHAR(30),
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_cierre        TIMESTAMPTZ
);

-- Log de operaciones del motor de correlación (auditoría)
CREATE TABLE correlacion_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_operacion  VARCHAR(40) NOT NULL,
    alarma_id       UUID,
    incidente_id    UUID,
    resultado       VARCHAR(15) NOT NULL,
    detalle         TEXT,
    fecha           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id  VARCHAR(100)
);

CREATE INDEX idx_alarma_nodo    ON alarma(nodo_id, estado);
CREATE INDEX idx_alarma_fuente  ON alarma(fuente_id, fecha_primera DESC);
CREATE INDEX idx_inc_estado     ON incidente_maestro(estado);
CREATE INDEX idx_inc_cliente    ON incidente_cliente(incidente_id);
CREATE INDEX idx_nodo_padre     ON nodo_red(padre_nodo_id);
```

---

## Funcionalidades

---

### F01 — Deduplicar y filtrar alarmas entrantes

**Descripción:** Recibe alarmas del bus de eventos (Kinesis), verifica si ya existe una alarma activa del mismo nodo/tipo y descarta duplicados o incrementa el contador de ocurrencias. Evita que una falla masiva genere miles de incidentes individuales.

**Contrato de entrada (evento Kinesis):**
```json
{
  "alarma_externa_id": "NMS-NORTE-20260704-001",
  "fuente_id": "NMS-REGIONAL-NORTE",
  "codigo_nodo": "OLT-NORTE-A03",
  "severidad": "CRITICA",
  "tipo_alarma": "FIBRA_CORTADA",
  "descripcion": "Pérdida total de señal en OLT-NORTE-A03",
  "timestamp": "2026-07-04T18:00:00-05:00",
  "correlation_id": "corr-nms-001"
}
```

**Contrato de salida — nueva alarma:**
```json
{ "alarma_id": "uuid", "estado": "RECIBIDA", "accion": "NUEVA" }
```

**Contrato de salida — duplicado:**
```json
{ "alarma_id": "uuid-existente", "estado": "RECIBIDA", "accion": "INCREMENTADO", "contador": 5 }
```

**Pseudocódigo:**
```
FUNCIÓN deduplicarAlarma(evento):
  // Verificar en Redis (ventana 10 minutos)
  clave = "ALARMA:{fuente_id}:{codigo_nodo}:{tipo_alarma}"
  existente_id = OBTENER Redis[clave]

  SI existente_id:
    ACTUALIZAR alarma.contador_ocurrencias += 1
    ACTUALIZAR alarma.fecha_ultima = NOW()
    INSERTAR correlacion_log (tipo=DUPLICADO_DESCARTADO)
    RETORNAR { accion: "INCREMENTADO" }

  // Verificar nodo en topología
  nodo = BUSCAR nodo_red WHERE codigo_nodo = evento.codigo_nodo
  SI no existe:
    INSERTAR alarma con estado = "PENDIENTE_MANUAL"
    INSERTAR correlacion_log (tipo=NODO_NO_ENCONTRADO)
    PUBLICAR evento "ALARMA_SIN_CORRELACION" → alerta operador NOC
    RETORNAR { accion: "PENDIENTE_MANUAL" }

  // Nueva alarma válida
  alarma = INSERTAR alarma (estado=RECIBIDA, nodo_id=nodo.id)
  GUARDAR Redis[clave] = alarma.id  TTL=600s
  RETORNAR { alarma_id: alarma.id, accion: "NUEVA" }
```

**Features y escenarios que cubre:**
- RF05-SC06: Descarte de eventos duplicados o irrelevantes
- RF05-SC05: Alarma sin correlación por inventario desactualizado
- RF06-SC06: Evento con esquema inválido o campos ausentes (validación previa)

**Lineamientos que cubre:**
- ARQ-03: Responsabilidad única — deduplicación de alarmas
- ESC-04: Redis para deduplicación en ventana temporal
- ESC-07: Control de concurrencia ante picos masivos de alarmas
- OBS-01: Logs estructurados con acción tomada por alarma
- OBS-02: Correlation ID propagado desde NMS
- RNF-001: Integridad — nodo debe existir en topología antes de correlacionar

---

### F02 — Correlacionar alarmas y crear incidente maestro

**Descripción:** Evalúa las alarmas recibidas, identifica el nodo origen más probable mediante análisis de topología, calcula los clientes afectados y crea el incidente maestro. Solo crea incidente si el número de afectados supera el umbral configurado.

**Contrato de entrada (trigger interno — alarma nueva en estado RECIBIDA):**
```json
{ "alarma_id": "uuid", "nodo_id": "uuid-nodo", "severidad": "CRITICA", "correlation_id": "corr-nms-001" }
```

**Contrato de salida — incidente creado (201):**
```json
{
  "incidente_id": "uuid",
  "codigo_incidente": "INC-2026-0042",
  "nodo_origen": "OLT-NORTE-A03",
  "zona_impactada": "NORTE-QUITO",
  "total_clientes_afectados": 1250,
  "clientes_empresariales": 18,
  "estado": "ACTIVO",
  "mensaje": "Incidente maestro creado en menos de 5 minutos"
}
```

**Contrato de salida — umbral no alcanzado:**
```json
{ "accion": "ALARMA_INDIVIDUAL", "clientes_afectados": 3, "umbral": 50 }
```

**Pseudocódigo:**
```
FUNCIÓN correlacionarAlarma(alarma_id):
  alarma = OBTENER alarma por id
  nodo = OBTENER nodo_red (incluye jerarquía padres)

  // Traversal ascendente de topología para encontrar nodo raíz de la falla
  nodo_origen = IDENTIFICAR_NODO_RAIZ(nodo, alarmas_activas_en_padres)

  // Calcular clientes afectados (descendentes del nodo origen)
  clientes = OBTENER cliente_nodo WHERE nodo en SUBÁRBOL(nodo_origen)
  total = clientes.COUNT
  empresariales = clientes WHERE tipo_cliente = 'EMPRESARIAL' AND sla_activo = TRUE

  // Verificar umbral de incidente masivo
  UMBRAL_MASIVO = OBTENER configuración (default: 50 clientes)
  SI total < UMBRAL_MASIVO:
    ACTUALIZAR alarma.estado = 'CORRELACIONADA' (alarma individual)
    INSERTAR correlacion_log (tipo=UMBRAL_NO_ALCANZADO)
    RETORNAR { accion: "ALARMA_INDIVIDUAL" }

  // Verificar si ya existe incidente activo para este nodo
  inc_existente = BUSCAR incidente_maestro WHERE nodo_origen = nodo_origen AND estado = 'ACTIVO'
  SI inc_existente:
    VINCULAR alarma al incidente existente
    RETORNAR inc_existente

  // Crear incidente maestro
  codigo_incidente = GENERAR "INC-{año}-{secuencia}"
  INICIO TRANSACCIÓN
    INSERTAR incidente_maestro (estado=ACTIVO, nodo_origen, clientes, correlation_id)
    PARA CADA cliente EN clientes:
      INSERTAR incidente_cliente (incidente_id, cliente_id, tipo, sla_activo)
    ACTUALIZAR alarma.incidente_id = incidente.id, estado = 'CORRELACIONADA'
    INSERTAR correlacion_log (tipo=INCIDENTE_CREADO)
  FIN TRANSACCIÓN

  PUBLICAR "INCIDENTE_MASIVO_ACTIVO" en EventBridge
    → ms-notificaciones recibe para notificación proactiva
    → ms-auditoria registra
  
  RETORNAR incidente_id, codigo, nodo_origen, clientes, estado
```

**Features y escenarios que cubre:**
- RF05-SC01: Agrupación en un solo incidente, identificación origen, lista clientes, apertura < 5 minutos
- RF05-SC08: Umbral no alcanzado — alarma individual
- RF05-SC09: Error técnico durante creación del incidente

**Lineamientos que cubre:**
- ARQ-06: Lógica de correlación centralizada, no embebida en canales
- INT-02: Publicación de eventos en EventBridge
- ESC-05: Procesamiento asíncrono de correlación
- ESC-06: Transacción con bloqueo en creación de incidente
- OBS-03: Métricas de incidentes por zona, severidad y clientes afectados

---

### F03 — Confirmar incidente y activar notificación proactiva

**Descripción:** El operador del NOC confirma el incidente maestro. El sistema activa el flujo de notificación proactiva a clientes afectados, actualiza el IVR y publica el aviso en el portal.

**Contrato de entrada:**
```json
POST /v1/incidentes/{incidente_id}/confirmar
Authorization: Bearer {token_noc}
{
  "operador_id": "NOC-OP-005",
  "tiempo_estimado_reparacion": "2 horas",
  "comentario": "Corte de fibra en nodo OLT-NORTE-A03, cuadrilla en camino",
  "correlation_id": "corr-inc-001"
}
```

**Contrato de salida — éxito (200):**
```json
{
  "incidente_id": "uuid",
  "estado": "CONFIRMADO",
  "clientes_a_notificar": 1250,
  "mensaje": "Incidente confirmado. Notificaciones proactivas en proceso."
}
```

**Pseudocódigo:**
```
FUNCIÓN confirmarIncidente(incidente_id, operador_id, tiempo_estimado):
  incidente = OBTENER incidente WHERE estado = 'ACTIVO'
  ACTUALIZAR incidente.estado = 'CONFIRMADO'
  ACTUALIZAR incidente.tiempo_estimado_reparacion = tiempo_estimado
  ACTUALIZAR incidente.fecha_confirmacion = NOW()

  PUBLICAR "INCIDENTE_CONFIRMADO" en EventBridge con:
    { incidente_id, clientes_afectados[], zona, tiempo_estimado }
  → ms-notificaciones envía email/WhatsApp a cada cliente
  → portal muestra aviso de falla masiva
  → IVR actualizado con mensaje de zona impactada

  REGISTRAR en audit_log
```

**Features:** RF05-SC02, RF05-SC03

---

### F04 — Cerrar incidente maestro con resolución en cascada

**Descripción:** El operador del NOC marca el incidente como resuelto. El sistema cierra automáticamente los tickets hijos en el ITSM, calcula la duración total para SLA, notifica el restablecimiento a clientes y publica KPIs en Power BI.

**Contrato de entrada:**
```json
POST /v1/incidentes/{incidente_id}/resolver
Authorization: Bearer {token_noc}
{ "operador_id": "NOC-OP-005", "comentario_resolucion": "Fibra reparada y señal restaurada" }
```

**Pseudocódigo:**
```
FUNCIÓN resolverIncidente(incidente_id, operador_id, comentario):
  incidente = OBTENER incidente WHERE estado IN ('CONFIRMADO','EN_RESOLUCION')

  INICIO TRANSACCIÓN
    ACTUALIZAR incidente.estado = 'RESUELTO'
    ACTUALIZAR incidente.fecha_resolucion = NOW()
    duracion = DIFERENCIA(fecha_apertura, fecha_resolucion) en minutos
    ACTUALIZAR incidente.duracion_minutos = duracion

    // Cerrar tickets hijos en ITSM
    tickets_hijos = OBTENER itsm_ticket WHERE incidente_id AND tipo = 'HIJO'
    PARA CADA ticket:
      ENCOLAR cierre en SQS-ITSM
      ACTUALIZAR itsm_ticket.estado_itsm = 'CERRADO_PENDIENTE'
  FIN TRANSACCIÓN

  PUBLICAR "INCIDENTE_RESUELTO" en EventBridge:
    → ms-notificaciones envía notificación de restablecimiento
    → ms-auditoria registra cierre
    → Kinesis → Redshift → Power BI publica KPIs:
        { codigo_incidente, duracion_minutos, total_afectados, sla_impactados }

  REGISTRAR en audit_log
```

**Features:** RF05-SC04 (cierre cascada, notificación restablecimiento, duración SLA, Power BI)

**Lineamientos que cubre:**
- INT-02: Publicación EventBridge en cascada
- INT-03: Cierre tickets ITSM con reintentos vía SQS
- OBS-03: KPIs de incidente publicados en Redshift → Power BI
- OBS-07: Dashboards operativos actualizados automáticamente

---

### F05 — Consultar incidentes activos

**Contrato de entrada:** `GET /v1/incidentes?estado=ACTIVO&zona=NORTE`
**Pseudocódigo:**
```
FUNCIÓN consultarIncidentes(filtros):
  VALIDAR token y rol (NOC, SOPORTE, ADMIN)
  resultados = BUSCAR incidente_maestro con filtros + paginación
  ENRIQUECER con clientes_afectados y alarmas correlacionadas
  RETORNAR lista con estado, zona, clientes, tiempo estimado
```
**Lineamientos:** INT-01, SEG-07, OBS-07

---

## Features y escenarios cubiertos (resumen)

| Feature | Escenario | Descripción |
|---------|-----------|-------------|
| RF05 | SC01 | Falla masiva agrupada en un solo incidente — F02 |
| RF05 | SC02 | Notificación proactiva a clientes — F03 |
| RF05 | SC03 | Cliente en IVR recibe info sin agente — F03 (IVR vía ms-notificaciones) |
| RF05 | SC04 | Cierre cascada con KPIs — F04 |
| RF05 | SC05 | Alarma sin correlación (inventario desactualizado) — F01 |
| RF05 | SC06 | Descarte de eventos duplicados — F01 |
| RF05 | SC07 | Falla en notificaciones proactivas — F03 + ms-notificaciones |
| RF05 | SC08 | Umbral no alcanzado — F02 alarma individual |
| RF05 | SC09 | Error técnico creando incidente — F02 con rollback |

## Lineamientos cubiertos (resumen)

| Código | Descripción |
|--------|-------------|
| ARQ-01 | Capa de dominio: operación de red y correlación |
| ARQ-03 | Responsabilidad única — motor de correlación |
| ARQ-06 | Lógica de negocio no embebida en canales |
| INT-01 | API REST versionada |
| INT-02 | Eventos EventBridge para notificaciones en cascada |
| INT-03 | Reintentos con backoff en integración ITSM |
| INT-06 | Idempotencia en creación de incidente por nodo origen |
| ESC-04 | Redis para deduplicación en ventana temporal |
| ESC-05 | Correlación asíncrona desacoplada de ingesta |
| ESC-06 | Bloqueo transaccional en creación de incidente |
| ESC-07 | Control de concurrencia ante picos masivos |
| SEG-07 | Acceso al NOC restringido por rol |
| SEG-10 | Auditoría de cada operación del incidente |
| OBS-01 | Logs estructurados por alarma y operación |
| OBS-02 | Correlation ID propagado desde NMS hasta ITSM |
| OBS-03 | Métricas de incidentes, duración y SLA |
| OBS-04 | Alertas ante nodo sin correlación o ITSM fállido |
| OBS-06 | Trazas distribuidas end-to-end (X-Ray) |
| OBS-07 | KPIs publicados en Power BI vía Redshift |
| RNF-001 | Integridad — topología sincronizada antes de correlacionar |
| RNF-003 | Seguridad — fuentes no autorizadas rechazadas |
| RNF-004 | Auditabilidad — log de cada operación del motor |
