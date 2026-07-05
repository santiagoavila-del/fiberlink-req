# Decisiones de Diseño — Hub Integrador FiberLink Andina Telecom

**Modelo LLM utilizado:** Claude (Anthropic) — Auto model
**Fecha de generación:** 4 de julio de 2026
**Versión:** 2.0 — Incorpora RF05 (correlación de incidentes) y RF06 (integración de fuentes de red)
**Iniciativas cubiertas:** I1 (Plataforma de Integración), I2 (Automatización Operacional), I3 (Plataforma de Observabilidad)

---

## 1. 9 Microservicios por dominio de negocio (ARQ-01, ARQ-03, ARQ-04)

**Decisión:** Se diseñaron 9 microservicios con responsabilidad única agrupados en dos dominios:
- **Dominio Instalación/Activación (I1, I2):** ms-orden, ms-programacion, ms-activacion, ms-facturacion, ms-inventario, ms-notificaciones, ms-auditoria
- **Dominio Observabilidad de Red (I3):** ms-correlacion-incidentes, ms-integracion-red

**Criterio:** ARQ-01 (separación por dominios), ARQ-03 (responsabilidad única), ARQ-04 (bajo acoplamiento). Los dominios de instalación y observabilidad tienen actores distintos (operador/técnico vs NOC/ingeniero de red), tasas de cambio independientes y tecnologías de ingesta diferentes (REST/EventBridge vs Kinesis).

**Alternativa descartada:** Un servicio único de "operaciones" que gestionara tanto el ciclo de instalación como la correlación de incidentes fue descartado por violar ARQ-02 (acoplamiento fuerte) y ARQ-07 (evolución con mínimo impacto lateral).

---

## 2. Kinesis Data Streams para alarmas de red (ESC-07, INT-02, RF06)

**Decisión:** Las alarmas provenientes de los NMS regionales se ingestan vía Amazon Kinesis Data Streams, no vía EventBridge ni SQS.

**Criterio:** RF06-SC10 exige control de saturación sin pérdida de eventos. Kinesis garantiza orden por partición, retención configurable (24h-365 días), throughput de millones de registros/segundo escalable por shards y semántica at-least-once sin pérdida de mensajes confirmados. EventBridge tiene un límite de throughput que no escala para el volumen de alarmas de red durante una falla masiva (miles de eventos simultáneos de múltiples NMS). ESC-07 (backpressure) se implementa nativamente con la partición de shards por severidad.

---

## 3. Patrón Saga con Step Functions para activación (INT-03, INT-06, RNF-001)

**Decisión:** El proceso de activación del servicio (RF04) se implementa como saga orquestada en AWS Step Functions con pasos de compensación.

**Criterio:** RF04 requiere reversión completa ante cualquier fallo parcial (generación de contrato, inicio de facturación, activación OSS). INT-03 (circuit breaker), RNF-001 (atomicidad). Una transacción distribuida 2PC fue descartada por riesgo de bloqueos. La saga con compensación es el patrón estándar para transacciones distribuidas en arquitecturas de microservicios.

---

## 4. Motor de correlación en ECS Fargate con topología en PostgreSQL (ARQ-03, ESC-06, RF05)

**Decisión:** ms-correlacion-incidentes corre en ECS Fargate con la topología de red almacenada en PostgreSQL (no en un grafo).

**Criterio:** La topología de FiberLink es jerárquica (árbol: nodo_raíz → OLT → splitter → CTO → cliente), no un grafo de propósito general. PostgreSQL con auto-referencia (campo padre_nodo_id) y consultas recursivas CTE es suficiente para el traversal ascendente de árbol que requiere la correlación. ESC-06 (prevención de cuellos de botella): bloqueos a nivel fila en creación de incidente garantizan que una falla masiva no genere incidentes duplicados. Una base de datos de grafos (Neptune) fue evaluada pero descartada por complejidad operativa innecesaria para topología árbol.

---

## 5. Redis para deduplicación de alarmas en ventana temporal (ESC-04, ESC-07, RF05-SC06)

**Decisión:** La deduplicación de alarmas se implementa con ElastiCache Redis usando clave compuesta `{fuente}:{nodo}:{tipo}` con TTL de 10 minutos.

**Criterio:** RF05-SC06 exige que eventos duplicados del mismo equipo no generen alarmas duplicadas. Redis provee operaciones atómicas SET-con-TTL con latencia < 1ms, ideal para el volumen masivo de alarmas durante una falla. Una deduplicación en PostgreSQL (SELECT + INSERT) bajo carga de miles de alarmas/segundo sería un cuello de botella severo. ESC-07 (control de concurrencia).

---

## 6. Lambda para normalización de NMS (ESC-03, INT-04, RF06-SC02)

**Decisión:** La normalización de eventos heterogéneos de NMS se implementa en AWS Lambda (no en ECS Fargate).

**Criterio:** La normalización es una transformación stateless event-driven disparada por Kinesis. Su carga es directamente proporcional al volumen de alarmas y varía entre cero (sin alarmas) y miles/segundo (falla masiva). Lambda escala a cero en reposo (ESC-03) y horizontalmente sin límite ante picos. ECS Fargate sería costoso para un proceso que pasa la mayor parte del tiempo inactivo.

---

## 7. AWS Glue + JDBC para sincronización Oracle on-premises (INT-07, RF06-SC03)

**Decisión:** La sincronización del inventario Oracle on-premises con la topología del motor de correlación se realiza con AWS Glue Jobs vía JDBC sobre VPN.

**Criterio:** Oracle on-premises no puede recibir una conexión directa desde Kinesis o EventBridge. Glue provee un conector JDBC administrado que corre en la VPC con acceso al Oracle a través de VPN/PrivateLink. INT-07 (minimizar acoplamiento directo). La frecuencia de sincronización (cada 4 horas) es adecuada para una topología que cambia con poca frecuencia; una sincronización en tiempo real sería costosa e innecesaria.

---

## 8. SQS con reintentos exponenciales para integración ITSM Azure (INT-03, RF06-SC09)

**Decisión:** La publicación de incidentes al ITSM Azure se realiza de forma asíncrona via SQS con política de reintentos exponenciales (30s, 60s, 120s).

**Criterio:** RF06-SC09 requiere que el incidente no se descarte aunque el ITSM no esté disponible. INT-03 (reintentos y circuit breaker). Una llamada síncrona directa al ITSM Azure bloquearía el flujo de correlación. SQS con DLQ garantiza que ningún incidente se pierda; el circuit breaker evita saturar el ITSM en recuperación.

---

## 9. EventBridge como bus de eventos del Hub de integración (INT-02, INT-07, I1)

**Decisión:** Amazon EventBridge es el bus central de integración para los eventos de negocio del Hub (instalación, activación, facturación, notificaciones). Kinesis se usa exclusivamente para el flujo de telemetría de red.

**Criterio:** Separar los buses por naturaleza del tráfico: EventBridge para eventos de negocio (latencia baja, volumen moderado, enrutamiento por reglas), Kinesis para telemetría de red (volumen extremadamente alto, orden garantizado, retención). Esta separación implementa ARQ-01 (separación por dominios) y evita que el tráfico de alarmas de red sature el bus de negocio.

---

## 10. Redshift + Power BI Azure para KPIs de incidentes y SLA (OBS-07, OBS-03, RF05-SC04)

**Decisión:** Los KPIs de incidentes (duración, SLA impactados, zonas) se publican vía Kinesis Firehose → Redshift → Power BI Azure.

**Criterio:** OBS-07 requiere dashboards operativos. Power BI Azure ya es la herramienta usada por FiberLink para tableros ejecutivos (mencionado en el contexto). Redshift provee el warehouse analítico para consultas históricas de SLA. Kinesis Firehose conecta el flujo de eventos de correlación con Redshift sin código adicional. Stack tecnológico define Redshift y Power BI Azure como herramientas de análisis aprobadas.

---

## 11. PostgreSQL (×4 instancias RDS) — segregación por dominio (ARQ-01, ESC-06)

**Decisión:** Se usan 4 instancias RDS PostgreSQL segregadas por dominio: instalación+programación, activación+facturación, inventario, observabilidad (correlación+integración).

**Criterio:** ARQ-01 (dominios con responsabilidades claras). Una única instancia PostgreSQL compartida crea acoplamiento fuerte de datos entre dominios y un cuello de botella de escritura bajo carga (ESC-06). La segregación permite escalar, hacer backup y tunar cada instancia según el patrón de acceso de su dominio. El costo adicional está justificado por el aislamiento de fallos y la mantenibilidad.

---

## 12. Secrets Manager para todas las credenciales externas (SEG-08, RNF-003)

**Decisión:** Todas las credenciales externas (NMS regionales, WhatsApp API, ERP Unix, ITSM Azure) se almacenan en AWS Secrets Manager con rotación automática.

**Criterio:** SEG-08 prohíbe almacenar secretos en código o configuración. RNF-003 (RG-03) identifica las integraciones heredadas con credenciales compartidas como riesgo crítico. Secrets Manager provee rotación automática, acceso auditado y cifrado con KMS. Elimina el riesgo de credenciales hardcodeadas en imágenes Docker o variables de entorno.

---

## Lineamientos adicionales aplicados (no documentados en /lineamientos)

| Criterio adicional | Justificación |
|-------------------|---------------|
| **Patrón Saga con compensación** | Estándar industria para transacciones distribuidas. Requerido por RF04-SC03/SC04 y principio de atomicidad RNF-001. |
| **Particionamiento mensual tabla audit_evento** | Tabla append-only crece indefinidamente. Particionamiento previene degradación de consultas (OBS-11) y facilita archivado a Glacier (OBS-09). |
| **Traversal árbol con CTE recursivo en PostgreSQL** | La topología de red de FiberLink es jerárquica, no un grafo general. CTEs recursivas son suficientes y evitan introducir Neptune. |
| **Kinesis Firehose como pipeline logs→S3/Redshift** | Conector administrado sin código entre Kinesis y el warehouse analítico. Reduce costo operativo vs ETL personalizado. |
| **Circuit breaker en integración ITSM Azure** | Protege el sistema ante indisponibilidad del ITSM durante incidentes masivos (precisamente cuando más se usa). Patrón estándar para integraciones con sistemas externos. |
| **Append-only para audit_evento** | OBS-08 requiere registros inmutables. Se implementa a nivel de base de datos: solo INSERT, sin UPDATE/DELETE, con política de rol de base de datos. |
| **GCP Pub/Sub como receptor secundario** | El contexto indica que parte de los eventos ya se envía a GCP Pub/Sub para analítica de fallas. Se mantiene como canal secundario de Kinesis Firehose para no romper integraciones existentes. |
