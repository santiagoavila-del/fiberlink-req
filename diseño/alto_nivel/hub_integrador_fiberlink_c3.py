"""
Diagrama C4 Nivel 3 — Component Diagram
Hub Integrador FiberLink Andina Telecom
Generado con diagrams (https://diagrams.mingrammer.com)

C4 Nivel 3 descompone cada microservicio/contenedor en sus componentes internos:
  - HTTP Handler / Event Consumer
  - Domain Service (lógica de negocio)
  - Repository (acceso a datos)
  - Event Publisher
  - External Adapter (OSS, ERP, ITSM, etc.)
Se muestran los stores de datos y buses de mensajería que cada componente usa.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, Lambda, LambdaFunction
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift
from diagrams.aws.integration import Eventbridge, SQS, StepFunctions
from diagrams.aws.analytics import KinesisDataStreams, KinesisDataFirehose, Glue
from diagrams.aws.analytics import ES as OpenSearch
from diagrams.aws.network import APIGateway
from diagrams.aws.security import SecretsManager
from diagrams.aws.storage import S3
from diagrams.aws.management import Cloudwatch
from diagrams.aws.devtools import XRay
from diagrams.onprem.database import Oracle
from diagrams.onprem.compute import Server

# ─────────────────────────────────────────────────────────────
# Atributos del grafo
# ─────────────────────────────────────────────────────────────
graph_attr = {
    "fontsize": "11",
    "bgcolor": "#f4f6f9",
    "pad": "0.8",
    "splines": "ortho",
    "nodesep": "0.5",
    "ranksep": "0.9",
    "fontname": "Arial",
}

node_attr = {
    "fontsize": "9",
    "fontname": "Arial",
}

output = "hub_integrador_fiberlink_c3"

with Diagram(
    "C4 Nivel 3 — Componentes de Microservicios\nHub Integrador · FiberLink Andina Telecom",
    filename=output,
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="TB",
    show=False,
):

    # ═══════════════════════════════════════════════════════════
    # INFRAESTRUCTURA COMPARTIDA (entrada y buses)
    # ═══════════════════════════════════════════════════════════
    apigw   = APIGateway("API Gateway\n(REST v1)")
    eb      = Eventbridge("EventBridge\n(Bus Hub)")
    kinesis = KinesisDataStreams("Kinesis Streams\n(Alarmas red)")
    kfh     = KinesisDataFirehose("Kinesis Firehose")
    cw      = Cloudwatch("CloudWatch")
    xray    = XRay("X-Ray")
    secrets = SecretsManager("Secrets Manager")

    # ═══════════════════════════════════════════════════════════
    # DOMINIO 1: INSTALACIÓN Y ACTIVACIÓN
    # ═══════════════════════════════════════════════════════════
    with Cluster("Dominio: Instalación y Activación"):

        # ── ms-orden-instalacion ─────────────────────────────
        with Cluster("ms-orden-instalacion  [ECS Fargate]"):
            ord_handler  = ECS("OrdenHandler\n(REST: POST/GET/PATCH)")
            ord_service  = ECS("OrdenDomainService\n(validar/crear/\ncambiar estado)")
            ord_repo     = ECS("OrdenRepository\n(RDS PostgreSQL)")
            ord_cache    = ECS("OrdenCacheService\n(Redis TTL=5min)")
            ord_pub      = ECS("OrdenEventPublisher\n(EventBridge)")
            ord_audit    = ECS("AuditLogger\n(CorrelationID)")

        rds_ord = RDS("RDS PostgreSQL\n(ordenes + historial)")
        redis_ord = ElastiCache("ElastiCache Redis\n(caché órdenes)")

        # ── ms-programacion-instalacion ──────────────────────
        with Cluster("ms-programacion-instalacion  [ECS Fargate]"):
            prog_handler = ECS("ProgramacionHandler\n(REST: GET disp.\nPOST/PUT reprog.)")
            prog_service = ECS("ProgramacionDomainService\n(validar/confirmar/\nreprogramar)")
            prog_repo    = ECS("ProgramacionRepository\n(RDS PostgreSQL)")
            prog_cache   = ECS("DisponibilidadCache\n(Redis TTL=2min)")
            prog_pub     = ECS("ProgramacionEventPublisher\n(EventBridge)")

        rds_prog  = RDS("RDS PostgreSQL\n(cuadrillas + agenda)")
        redis_prog = ElastiCache("ElastiCache Redis\n(disponibilidad)")

        # ── ms-activacion-servicio ───────────────────────────
        with Cluster("ms-activacion-servicio  [ECS Fargate + Step Functions]"):
            act_handler  = ECS("ActivacionHandler\n(REST: POST solicitar)")
            act_service  = ECS("ActivacionDomainService\n(validar cliente/\norquestar saga)")
            act_saga     = StepFunctions("SagaActivacion\n(Step Functions)\n7 pasos + compensación")
            act_oss      = ECS("OSSAdapter\n(VPN → ONT/OLT/BRAS\ntimeout: 30s)")
            act_s3       = ECS("ContratoS3Service\n(generar PDF\ncifrado KMS)")
            act_pub      = ECS("ActivacionEventPublisher\n(EventBridge)")

        rds_act  = RDS("RDS PostgreSQL\n(activacion + contrato)")
        s3_docs  = S3("S3\n(contratos PDF)")
        oss_srv  = Server("OSS On-Premises\n(ONT/OLT/BRAS)")

        # ── ms-facturacion ───────────────────────────────────
        with Cluster("ms-facturacion  [ECS Fargate]"):
            fac_handler  = ECS("FacturacionHandler\n(REST: POST iniciar\nGET consultar)")
            fac_service  = ECS("FacturacionDomainService\n(validar/iniciar\nciclo cobro)")
            fac_repo     = ECS("FacturacionRepository\n(RDS PostgreSQL)")
            fac_erp      = ECS("ERPAdapter\n(SQS → ERP Unix\nVPN PrivateLink)")
            fac_cache    = ECS("FacturacionCacheService\n(Redis TTL=10min)")
            fac_pub      = ECS("FacturacionEventPublisher\n(EventBridge)")

        rds_fac   = RDS("RDS PostgreSQL\n(facturacion + erp_integracion)")
        redis_fac = ElastiCache("ElastiCache Redis\n(caché facturación)")
        sqs_erp   = SQS("SQS\n(cola ERP)")
        erp_srv   = Server("ERP On-Premises\n(Facturación Unix)")

        # ── ms-inventario ────────────────────────────────────
        with Cluster("ms-inventario  [ECS Fargate]"):
            inv_handler  = ECS("InventarioHandler\n(REST: GET disponib.\nPOST reservar)")
            inv_consumer = ECS("EventConsumer\n(EventBridge:\nPROGRAMADA/\nACTIVADO)")
            inv_service  = ECS("InventarioDomainService\n(reservar/liberar/\ninstalar equipos)")
            inv_repo     = ECS("InventarioRepository\n(FOR UPDATE lock)")
            inv_cache    = ECS("StockCacheService\n(Redis TTL=1min)")
            inv_pub      = ECS("InventarioEventPublisher\n(EventBridge)")

        rds_inv   = RDS("RDS PostgreSQL\n(equipo + stock + movimientos)")
        redis_inv = ElastiCache("ElastiCache Redis\n(stock en tiempo real)")

    # ═══════════════════════════════════════════════════════════
    # DOMINIO 2: SERVERLESS — NOTIFICACIONES Y AUDITORÍA
    # ═══════════════════════════════════════════════════════════
    with Cluster("Dominio: Notificaciones y Auditoría  [Lambda]"):

        # ── ms-notificaciones ────────────────────────────────
        with Cluster("ms-notificaciones  [Lambda]"):
            notif_consumer  = Lambda("EventConsumer\n(SQS + EventBridge:\nPROGRAMADA/REPROG/\nACTIVACION/INCIDENTE)")
            notif_service   = Lambda("NotificacionDomainService\n(idempotencia\nDynamoDB + plantillas)")
            notif_email     = Lambda("EmailAdapter\n(Amazon SES)")
            notif_whatsapp  = Lambda("WhatsAppAdapter\n(Meta Business API\n+ Secrets Manager)")
            notif_ivr       = Lambda("IVRAdapter\n(IVR On-Prem API)")
            notif_portal    = Lambda("PortalAdapter\n(push → Amplify)")
            notif_retry     = Lambda("RetryScheduler\n(CW Events 5min\nmax 3 intentos)")

        dynamo_notif = Dynamodb("DynamoDB\n(notificaciones\n+ idempotencia)")
        sqs_notif    = SQS("SQS\n(Notificaciones)")
        ses_srv      = Server("Amazon SES\n(Email)")
        wa_srv       = Server("WhatsApp\nBusiness API")
        ivr_srv      = Server("IVR\nCall Center")

        # ── ms-auditoria ─────────────────────────────────────
        with Cluster("ms-auditoria  [Lambda]"):
            audit_consumer  = Lambda("EventConsumer\n(EventBridge:\ntodos los eventos)")
            audit_writer    = Lambda("AuditWriter\n(INSERT only\npartición mensual)")
            audit_indexer   = Lambda("OpenSearchIndexer\n(indexa para búsqueda)")
            audit_validator = Lambda("ConsistencyValidator\n(activación vs facturación)")
            audit_handler   = Lambda("AuditQueryHandler\n(REST: GET auditoría\nroles: AUDITOR/ADMIN)")

        rds_audit  = RDS("RDS PostgreSQL\n(audit_evento\nparticionado)")
        opensrch   = OpenSearch("OpenSearch\n(índice auditoría)")
        s3_audit   = S3("S3 + Glacier\n(retención 5 años)")

    # ═══════════════════════════════════════════════════════════
    # DOMINIO 3: OBSERVABILIDAD DE RED
    # ═══════════════════════════════════════════════════════════
    with Cluster("Dominio: Observabilidad de Red"):

        # ── ms-integracion-red ───────────────────────────────
        with Cluster("ms-integracion-red  [ECS Fargate + Lambda]"):
            red_validator   = ECS("FuenteValidator\n(autoriza fuentes\n+ Secrets Manager)")
            red_normalizer  = Lambda("EventNormalizer\n(Lambda: esquema\ncanónico por fuente)")
            red_glue        = Glue("GlueETLJob\n(Oracle JDBC\nvía VPN)")
            red_sync        = ECS("InventarioSyncService\n(UPSERT nodo_red\n+ cliente_nodo)")
            red_itsm        = ECS("ITSMAdapter\n(Azure ITSM API\ncircuit breaker\n+ SQS retry)")
            red_monitor     = ECS("FuenteMonitor\n(CW Events 1min\ndetecta silencio)")
            red_flow        = ECS("FlowController\n(backpressure\nKinesis saturación)")

        rds_red    = RDS("RDS PostgreSQL\n(fuentes + mapeos\n+ ingesta + itsm_pub)")
        inv_oracle = Oracle("Inventario Oracle\n(Topología red)")
        itsm_srv   = Server("ITSM Azure\n(Mesa de ayuda)")
        sqs_itsm   = SQS("SQS\n(ITSM reintentos)")

        # ── ms-correlacion-incidentes ────────────────────────
        with Cluster("ms-correlacion-incidentes  [ECS Fargate]"):
            corr_consumer   = ECS("AlarmaConsumer\n(Kinesis Streams)")
            corr_dedup      = ECS("DeduplicadorService\n(Redis ventana 10min\nevita tormentas)")
            corr_engine     = ECS("CorrelacionEngine\n(traversal topología\nnodo raíz falla)")
            corr_calculator = ECS("AfectadosCalculator\n(subárbol nodo\nclientes + SLA)")
            corr_handler    = ECS("IncidenteHandler\n(REST: POST confirmar\nPOST resolver\nGET activos)")
            corr_itsm       = ECS("ITSMTicketService\n(crea/cierra tickets\nhijo vía SQS)")
            corr_pub        = ECS("IncidenteEventPublisher\n(EventBridge:\nINCIDENTE_MASIVO/\nRESUELTO)")

        rds_corr   = RDS("RDS PostgreSQL\n(alarmas + incidentes\n+ topología + SLA)")
        redis_corr = ElastiCache("ElastiCache Redis\n(dedup alarmas)")
        redshift   = Redshift("Redshift\n(KPIs incidentes)")

    # ═══════════════════════════════════════════════════════════
    # CONEXIONES — Dominio Instalación/Activación
    # ═══════════════════════════════════════════════════════════

    # API Gateway → Handlers
    apigw >> ord_handler
    apigw >> prog_handler
    apigw >> act_handler
    apigw >> fac_handler
    apigw >> inv_handler

    # ms-orden componentes internos
    ord_handler >> ord_service >> ord_repo >> rds_ord
    ord_service >> ord_cache >> redis_ord
    ord_service >> ord_pub >> eb
    ord_service >> ord_audit >> cw

    # ms-programacion componentes internos
    prog_handler >> prog_service >> prog_repo >> rds_prog
    prog_service >> prog_cache >> redis_prog
    prog_service >> prog_pub >> eb
    # Llama a ms-orden para cambiar estado
    prog_service >> Edge(label="PATCH /estado", style="dashed") >> ord_handler
    # Llama a ms-inventario para verificar stock
    prog_service >> Edge(label="GET disponibilidad", style="dashed") >> inv_handler

    # ms-activacion componentes internos
    act_handler >> act_service >> act_saga
    act_saga >> act_oss >> oss_srv
    act_saga >> act_s3 >> s3_docs
    act_saga >> act_pub >> eb
    act_saga >> xray
    act_service >> rds_act
    # Saga llama a ms-orden y ms-facturacion
    act_saga >> Edge(label="PATCH /estado EXITOSA", style="dashed") >> ord_handler
    act_saga >> Edge(label="POST /iniciar", style="dashed") >> fac_handler

    # ms-facturacion componentes internos
    fac_handler >> fac_service >> fac_repo >> rds_fac
    fac_service >> fac_erp >> sqs_erp >> erp_srv
    fac_service >> fac_cache >> redis_fac
    fac_service >> fac_pub >> eb

    # ms-inventario componentes internos
    inv_handler >> inv_service >> inv_repo >> rds_inv
    inv_consumer >> Edge(label="INSTALACION_PROGRAMADA\nSERVICIO_ACTIVADO") >> inv_service
    eb >> inv_consumer
    inv_service >> inv_cache >> redis_inv
    inv_service >> inv_pub >> eb

    # ═══════════════════════════════════════════════════════════
    # CONEXIONES — Dominio Notificaciones/Auditoría
    # ═══════════════════════════════════════════════════════════

    # ms-notificaciones componentes internos
    sqs_notif >> notif_consumer
    eb >> notif_consumer
    notif_consumer >> notif_service >> dynamo_notif
    notif_service >> notif_email >> ses_srv
    notif_service >> notif_whatsapp >> wa_srv
    notif_service >> notif_ivr >> ivr_srv
    notif_service >> notif_portal
    notif_retry >> notif_service
    notif_whatsapp >> secrets

    # ms-auditoria componentes internos
    eb >> audit_consumer >> audit_writer >> rds_audit
    audit_writer >> audit_indexer >> opensrch
    audit_writer >> s3_audit
    audit_consumer >> audit_validator >> cw
    apigw >> audit_handler >> opensrch

    # ═══════════════════════════════════════════════════════════
    # CONEXIONES — Dominio Observabilidad de Red
    # ═══════════════════════════════════════════════════════════

    # ms-integracion-red componentes internos
    kinesis >> red_validator >> red_normalizer >> kinesis
    red_normalizer >> rds_red
    red_glue >> inv_oracle
    red_glue >> red_sync >> rds_red
    red_sync >> Edge(label="TOPOLOGIA_ACTUALIZADA") >> eb
    eb >> red_itsm >> sqs_itsm >> itsm_srv
    red_itsm >> rds_red
    red_monitor >> cw
    red_monitor >> rds_red
    red_flow >> kinesis
    red_validator >> secrets

    # ms-correlacion-incidentes componentes internos
    kinesis >> corr_consumer >> corr_dedup
    corr_dedup >> redis_corr
    corr_dedup >> corr_engine >> rds_corr
    corr_engine >> corr_calculator >> rds_corr
    corr_calculator >> corr_pub >> eb
    apigw >> corr_handler >> rds_corr
    corr_handler >> corr_pub
    corr_handler >> corr_itsm >> sqs_itsm
    corr_pub >> kfh >> redshift

    # Observabilidad transversal
    [ord_service, prog_service, act_service, fac_service,
     inv_service, corr_engine, red_validator] >> cw

print(f"Diagrama C4 Nivel 3 generado: {output}.png")
