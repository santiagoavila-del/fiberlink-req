# Microservicio: ms-programacion-instalacion

## Descripción
Gestiona la asignación y validación de disponibilidad de recursos para programar la instalación: cuadrillas técnicas, materiales, equipos, permisos y rutas. Soporta la reprogramación con liberación y reasignación de recursos. Cubre Iniciativa 2 (automatización operacional).

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate
- **Base de datos:** PostgreSQL (Amazon RDS)
- **Caché:** ElastiCache (Redis) — disponibilidad de cuadrillas
- **Mensajería:** SQS (solicitudes) + EventBridge (confirmaciones)
- **API:** REST versionada — API Gateway

---

## Base de datos

```sql
CREATE TABLE cuadrilla (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo           VARCHAR(20) NOT NULL UNIQUE,
    nombre           VARCHAR(100) NOT NULL,
    zona             VARCHAR(50),
    capacidad_diaria INTEGER     NOT NULL DEFAULT 4,
    activa           BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE cuadrilla_agenda (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cuadrilla_id     UUID        NOT NULL REFERENCES cuadrilla(id),
    fecha            DATE        NOT NULL,
    franja_horaria   VARCHAR(20) NOT NULL,
    capacidad_total  INTEGER     NOT NULL DEFAULT 1,
    capacidad_usada  INTEGER     NOT NULL DEFAULT 0,
    estado           VARCHAR(15) NOT NULL DEFAULT 'DISPONIBLE',
    CONSTRAINT uq_agenda UNIQUE(cuadrilla_id, fecha, franja_horaria),
    CONSTRAINT chk_cap CHECK (capacidad_usada <= capacidad_total)
);

CREATE TABLE programacion (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id            UUID        NOT NULL UNIQUE,
    cuadrilla_id        UUID        REFERENCES cuadrilla(id),
    agenda_id           UUID        REFERENCES cuadrilla_agenda(id),
    fecha_programada    DATE        NOT NULL,
    franja_horaria      VARCHAR(20) NOT NULL,
    permisos_obtenidos  BOOLEAN     NOT NULL DEFAULT FALSE,
    ruta_habilitada     BOOLEAN     NOT NULL DEFAULT FALSE,
    estado              VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    intentos            INTEGER     NOT NULL DEFAULT 0,
    correlation_id      VARCHAR(100),
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_estado_prog CHECK (estado IN ('PENDIENTE','CONFIRMADA','REPROGRAMADA','CANCELADA','FALLIDA'))
);

CREATE INDEX idx_prog_orden ON programacion(orden_id);
CREATE INDEX idx_agenda_fecha ON cuadrilla_agenda(fecha, estado);
```

---

## Funcionalidades

### F01 — Verificar disponibilidad de recursos

**Contrato de entrada:** `GET /v1/programacion/disponibilidad?fecha=2026-07-10&zona=NORTE&franja=08:00-12:00`
**Contrato de salida:**
```json
{ "fecha": "2026-07-10", "franja_horaria": "08:00-12:00",
  "cuadrilla_disponible": true, "cuadrilla_id": "CUA-05",
  "cuadrilla_nombre": "Cuadrilla Norte 5", "franjas_alternativas": ["13:00-17:00"] }
```
**Pseudocódigo:**
```
FUNCIÓN verificarDisponibilidad(fecha, zona, franja):
  resultado = BUSCAR en Redis "DISPONIBILIDAD:{zona}:{fecha}:{franja}"
  SI no en caché:
    cuadrillas = CONSULTAR cuadrilla_agenda WHERE disponible Y capacidad libre
    GUARDAR en Redis TTL=2min
  RETORNAR disponible, cuadrilla, franjas_alternativas
```
**Lineamientos:** ESC-04, INT-01, ESC-02

---

### F02 — Registrar programación de instalación

**Contrato de entrada:**
```json
POST /v1/programacion
{ "orden_id": "uuid", "fecha_programada": "2026-07-10", "franja_horaria": "08:00-12:00",
  "cuadrilla_id": "CUA-05", "permisos_obtenidos": true, "ruta_habilitada": true,
  "operador_id": "USR-OP-001", "correlation_id": "corr-prog-001" }
```
**Contrato de salida — éxito (201):**
```json
{ "programacion_id": "uuid", "orden_id": "uuid", "fecha_programada": "2026-07-10",
  "estado": "CONFIRMADA", "mensaje": "Instalación programada correctamente" }
```
**Pseudocódigo:**
```
FUNCIÓN registrarProgramacion(datos):
  orden = VERIFICAR ms-orden GET /v1/ordenes/{id}
  VALIDAR permisos_obtenidos, ruta_habilitada, cuadrilla disponible
  disponibilidad_inv = LLAMAR ms-inventario GET /v1/inventario/disponibilidad
  SI NOT disponible → error 422

  INICIO TRANSACCIÓN
    INCREMENTAR agenda.capacidad_usada
    INSERTAR programacion estado="CONFIRMADA"
    LLAMAR ms-orden PATCH /estado → "PROGRAMADA"
    PUBLICAR "INSTALACION_PROGRAMADA" en EventBridge
  FIN TRANSACCIÓN
  REGISTRAR en audit_log
```
**Features:** RF01-SC01/SC02/SC03/SC04/SC05
**Lineamientos:** ARQ-03, INT-01, INT-03, INT-04, INT-06, ESC-05, OBS-01, OBS-02, SEG-10

---

### F03 — Reprogramar instalación

**Contrato de entrada:**
```json
PUT /v1/programacion/{programacion_id}/reprogramar
{ "nueva_fecha": "2026-07-15", "nueva_franja": "13:00-17:00",
  "nueva_cuadrilla_id": "CUA-03", "cliente_id": "CLI-00123", "correlation_id": "corr-reprg-001" }
```
**Pseudocódigo:**
```
FUNCIÓN reprogramar(programacion_id, nueva_fecha, nueva_franja, nueva_cuadrilla):
  VALIDAR estado = "CONFIRMADA"
  VALIDAR horas_restantes > 24h
  VERIFICAR disponibilidad nueva fecha/cuadrilla

  INICIO TRANSACCIÓN
    DECREMENTAR agenda_anterior.capacidad_usada
    INCREMENTAR nueva_agenda.capacidad_usada
    ACTUALIZAR programacion (nueva fecha, estado=REPROGRAMADA)
    LLAMAR ms-orden PATCH /estado → "REPROGRAMADA"
    PUBLICAR "INSTALACION_REPROGRAMADA" en EventBridge
  FIN TRANSACCIÓN
```
**Features:** RF03-SC01/SC02/SC03/SC04/SC05
**Lineamientos:** INT-03, INT-06, ESC-05, RNF-001, OBS-02

---

## Lineamientos cubiertos (resumen)

| Código | Descripción |
|--------|-------------|
| ARQ-03 | Responsabilidad única — programación y agenda |
| INT-01 | API REST versionada |
| INT-02 | Eventos EventBridge |
| INT-03 | Timeout y circuit breaker |
| INT-06 | Idempotencia por correlation_id |
| ESC-04 | Caché Redis — disponibilidad cuadrillas |
| ESC-05 | Operaciones diferibles desacopladas |
| SEG-07 | Mínimo privilegio |
| SEG-10 | Auditoría de programaciones |
| OBS-01 | Logs estructurados |
| OBS-02 | Correlation ID end-to-end |
| RNF-001 | Integridad de datos propagada vía eventos |
| RNF-003 | Rate limiting en API Gateway |
