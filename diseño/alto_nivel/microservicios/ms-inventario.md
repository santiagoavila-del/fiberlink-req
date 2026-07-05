# Microservicio: ms-inventario

## Descripción
Gestiona la disponibilidad, reserva, asignación y baja de equipos (ONT, routers, cables) y materiales. Garantiza que ningún equipo aparezca simultáneamente disponible y asignado. Sincroniza con el sistema Oracle on-premises. Cubre Iniciativa 1 (Hub) e Iniciativa 2 (automatización).

## Stack tecnológico
- **Cómputo:** AWS ECS Fargate
- **Base de datos:** PostgreSQL (Amazon RDS)
- **Caché:** ElastiCache (Redis)
- **Mensajería:** EventBridge (suscriptor/publicador)
- **Integración:** Oracle on-premises vía VPN/Glue JDBC

---

## Base de datos

```sql
CREATE TABLE tipo_equipo (
    id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo    VARCHAR(30) NOT NULL UNIQUE,
    nombre    VARCHAR(100) NOT NULL,
    categoria VARCHAR(20) NOT NULL, -- ONT, ROUTER, CABLE, MATERIAL
    activo    BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE equipo (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    serie          VARCHAR(50) UNIQUE,
    tipo_equipo_id UUID        NOT NULL REFERENCES tipo_equipo(id),
    almacen_id     VARCHAR(30) NOT NULL,
    estado         VARCHAR(20) NOT NULL DEFAULT 'DISPONIBLE',
    orden_id       UUID,
    cliente_id     VARCHAR(50),
    contrato_id    VARCHAR(30),
    fecha_estado   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_estado_eq CHECK (estado IN (
        'DISPONIBLE','RESERVADO','EN_TRANSITO','INSTALADO','DEFECTUOSO','DADO_DE_BAJA'))
);

CREATE TABLE stock_material (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_equipo_id      UUID        NOT NULL REFERENCES tipo_equipo(id),
    almacen_id          VARCHAR(30) NOT NULL,
    cantidad_total      INTEGER     NOT NULL DEFAULT 0,
    cantidad_reservada  INTEGER     NOT NULL DEFAULT 0,
    cantidad_disponible INTEGER GENERATED ALWAYS AS (cantidad_total - cantidad_reservada) STORED,
    CONSTRAINT chk_stock CHECK (cantidad_reservada <= cantidad_total),
    CONSTRAINT uq_stock UNIQUE(tipo_equipo_id, almacen_id)
);

CREATE TABLE movimiento_inventario (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    equipo_id        UUID        REFERENCES equipo(id),
    stock_id         UUID        REFERENCES stock_material(id),
    tipo_movimiento  VARCHAR(20) NOT NULL, -- RESERVA, LIBERACION, INSTALACION, BAJA
    cantidad         INTEGER     NOT NULL DEFAULT 1,
    orden_id         UUID,
    usuario_id       VARCHAR(50) NOT NULL,
    fecha_movimiento TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id   VARCHAR(100)
);

CREATE INDEX idx_equipo_estado ON equipo(estado);
CREATE INDEX idx_equipo_orden  ON equipo(orden_id);
CREATE INDEX idx_stock_almacen ON stock_material(almacen_id, tipo_equipo_id);
```

---

## Funcionalidades

### F01 — Consultar disponibilidad
**Contrato:** `GET /v1/inventario/disponibilidad?orden_id={uuid}&almacen_id=ALM-NORTE`
**Pseudocódigo:**
```
FUNCIÓN consultarDisponibilidad(orden_id, almacen_id):
  requerimientos = OBTENER plan de la orden
  PARA CADA item: CONTAR disponibles en stock/equipos
  RETORNAR materiales_disponibles, detalle por tipo
```
**Lineamientos:** ESC-04 (Redis), INT-01, RNF-001

---

### F02 — Reservar equipos y materiales
**Evento disparador:** `INSTALACION_PROGRAMADA`
**Pseudocódigo:**
```
FUNCIÓN reservarEquipos(orden_id, almacen_id, items):
  VERIFICAR idempotencia por orden_id
  INICIO TRANSACCIÓN
    PARA CADA item: SELECT FOR UPDATE → RESERVAR
    SI stock insuficiente → ROLLBACK error 422
    INSERTAR movimiento_inventario tipo=RESERVA
    INVALIDAR caché Redis
  FIN TRANSACCIÓN
  PUBLICAR "INVENTARIO_RESERVADO"
```
**Features:** RF01-SC01/SC03, RF03-SC01
**Lineamientos:** INT-02, INT-06, ESC-06, RNF-001

---

### F03 — Liberar equipos reservados
**Evento disparador:** `RECURSOS_LIBERADOS`
**Pseudocódigo:**
```
FUNCIÓN liberarReserva(orden_id, motivo):
  INICIO TRANSACCIÓN
    PARA CADA equipo reservado: SET estado=DISPONIBLE, orden_id=NULL
    ACTUALIZAR stock.cantidad_reservada -= cantidad
    INSERTAR movimiento tipo=LIBERACION
    INVALIDAR caché
  FIN TRANSACCIÓN
  PUBLICAR "INVENTARIO_LIBERADO"
```
**Features:** RF01-SC05, RF03-SC01

---

### F04 — Registrar equipos como instalados
**Evento disparador:** `SERVICIO_ACTIVADO`
**Pseudocódigo:**
```
FUNCIÓN registrarInstalacion(orden_id, cliente_id, contrato_id, equipos):
  INICIO TRANSACCIÓN
    PARA CADA equipo: SET estado=INSTALADO, cliente_id, contrato_id
    INSERTAR movimiento tipo=INSTALACION
    INVALIDAR caché
  FIN TRANSACCIÓN
  PUBLICAR "EQUIPOS_INSTALADOS" → OSS sincroniza
```
**Features:** RF04-SC01
**Lineamientos:** RNF-001, INT-02

---

## Lineamientos cubiertos

| Código | Descripción |
|--------|-------------|
| ARQ-03 | Responsabilidad única — gestión inventario |
| INT-02 | Suscriptor de eventos EventBridge |
| INT-06 | Idempotencia por orden_id |
| ESC-04 | Caché Redis disponibilidad en tiempo real |
| ESC-06 | Bloqueo fila (FOR UPDATE) previene doble asignación |
| SEG-10 | Auditoría de cada movimiento |
| OBS-01 | Logs estructurados |
| OBS-02 | Correlation ID en cada operación |
| RNF-001 | Equipo no puede estar disponible e instalado simultáneamente |
| RNF-004 | Trazabilidad completa de movimientos |
