"""
Diagrama C4 Nivel 2 — Container Diagram
Hub Integrador FiberLink Andina Telecom
Generado con diagrams (https://diagrams.mingrammer.com)

C4 Nivel 2 descompone el sistema central en sus contenedores:
  - Aplicaciones / microservicios
  - Bases de datos
  - Colas y buses de eventos
  - Capas de seguridad y acceso
  - Observabilidad
Se muestran también los actores externos y sistemas externos de primer nivel.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, Lambda, ECR
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift
from diagrams.aws.integration import Eventbridge, SQS, SNS, StepFunctions
from diagrams.aws.analytics import KinesisDataStreams, KinesisDataFirehose, Glue
from diagrams.aws.analytics import ES as OpenSearch
from diagrams.aws.network import APIGateway, CloudFront, Route53
from diagrams.aws.security import WAF, Cognito, SecretsManager, KMS
from diagrams.aws.storage import S3, S3GlacierArchive
from diagrams.aws.management import Cloudwatch, Cloudtrail
from diagrams.aws.devtools import XRay
from diagrams.aws.mobile import Amplify
from diagrams.onprem.database import Oracle
from diagrams.onprem.compute import Server
from diagrams.onprem.client import User

# ─────────────────────────────────────────────────────────────
# Atributos del grafo
# ─────────────────────────────────────────────────────────────
graph_attr = {
    "fontsize": "12",
    "bgcolor": "#f0f4f8",
    "pad": "0.8",
    "splines": "ortho",
    "nodesep": "0.6",
    "ranksep": "1.1",
    "fontname": "Arial",
}

node_attr = {
    "fontsize": "10",
    "fontname": "Arial",
}

output = "hub_integrador_fiberlink_c2"

with Diagram(
    "C4 Nivel 2 — Contenedores del Sistema\nHub Integrador · FiberLink Andina Telecom",
    filename=output,
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="TB",
    show=False,
):

    # ═══════════════════════════════════════════════════════════
    # ACTORES EXTERNOS
    # ═══════════════════════════════════════════════════════════
    with Cluster("Actores"):
        cliente    = User("Cliente\n(portal / app)")
        tecnico    = User("Técnico\nde Campo")
        agente_noc = User("Agente NOC")
        agente_crm = User("Agente\nComercial")

    # ═══════════════════════════════════════════════════════════
    # HUB INTEGRADOR — SISTEMA CENTRAL (AWS)
    # ═══════════════════════════════════════════════════════════
    with Cluster("Hub Integrador FiberLink · AWS"):

        # ── Capa 1: Canales de entrada ──────────────────────────
        with Cluster("Canales de Entrada"):
            portal    = Amplify("Portal Cliente\n(Amplify)")
            app_movil = User("App Móvil\nTécnico")
            noc_ui    = User("Portal NOC\n(Web UI)")

        # ── Capa 2: Ingreso y seguridad ─────────────────────────
        with Cluster("Ingreso y Seguridad"):
            route53 = Route53("Route 53\n(DNS)")
            waf     = WAF("WAF\n(OWASP + Rate Limit)")
            cf      = CloudFront("CloudFront\n(CDN · TLS 1.3)")
            apigw   = APIGateway("API Gateway\n(REST v1)")
            cognito = Cognito("Cognito\n(OAuth2/OIDC · MFA)")

        # ── Capa 3a: Microservicios — Instalación y Activación ──
        with Cluster("Contenedores: Instalación y Activación  [ECS Fargate]"):
            ms_orden = ECS("ms-orden\n-instalacion")
            ms_prog  = ECS("ms-programacion\n-instalacion")
            ms_act   = ECS("ms-activacion\n-servicio")
            ms_fac   = ECS("ms-facturacion")
            ms_inv   = ECS("ms-inventario")
            sf       = StepFunctions("Step Functions\n(Saga Activación)")

        # ── Capa 3b: Microservicios — Observabilidad de Red ─────
        with Cluster("Contenedores: Observabilidad de Red  [ECS Fargate]"):
            ms_corr   = ECS("ms-correlacion\n-incidentes")
            ms_intred = ECS("ms-integracion\n-red")

        # ── Capa 3c: Serverless ─────────────────────────────────
        with Cluster("Contenedores: Serverless  [Lambda]"):
            ms_notif    = Lambda("ms-notificaciones")
            ms_audit    = Lambda("ms-auditoria")
            lambda_norm = Lambda("Lambda Normalización\n(NMS → canónico)")
            glue        = Glue("Glue ETL\n(Oracle → Hub)")

        # ── Capa 4: Mensajería y Eventos ────────────────────────
        with Cluster("Mensajería y Eventos"):
            eb        = Eventbridge("EventBridge\n(Bus Hub I1+I2)")
            kinesis   = KinesisDataStreams("Kinesis Streams\n(Alarmas red · I3)")
            kfh       = KinesisDataFirehose("Kinesis Firehose\n(→ S3 / Redshift)")
            sqs_notif = SQS("SQS\nNotificaciones")
            sqs_erp   = SQS("SQS\nERP Integración")
            sqs_itsm  = SQS("SQS\nITSM Azure")
            sns       = SNS("SNS\nAlertas operativas")

        # ── Capa 5: Almacenamiento y Datos ──────────────────────
        with Cluster("Almacenamiento y Datos"):
            rds_inst = RDS("RDS PostgreSQL\n(órdenes + prog.)")
            rds_act  = RDS("RDS PostgreSQL\n(activación + fac.)")
            rds_inv  = RDS("RDS PostgreSQL\n(inventario)")
            rds_obs  = RDS("RDS PostgreSQL\n(correlación + red)")
            dynamo   = Dynamodb("DynamoDB\n(notificaciones)")
            redis    = ElastiCache("ElastiCache Redis\n(caché + dedup.)")
            s3       = S3("S3\n(contratos · evidencias)")
            opensrch = OpenSearch("OpenSearch\n(auditoría)")
            glacier  = S3GlacierArchive("S3 Glacier\n(retención 5 años)")
            redshift = Redshift("Redshift\n(KPIs · SLA)")

        # ── Capa 6: Observabilidad ──────────────────────────────
        with Cluster("Observabilidad"):
            cw         = Cloudwatch("CloudWatch\n(métricas · logs)")
            xray       = XRay("X-Ray\n(trazas)")
            cloudtrail = Cloudtrail("CloudTrail\n(auditoría AWS)")
            grafana    = Server("Grafana\n(dashboards)")

        # ── Capa 7: Seguridad y Gobierno ────────────────────────
        with Cluster("Seguridad y Gobierno"):
            secrets = SecretsManager("Secrets Manager")
            kms     = KMS("KMS\n(cifrado)")
            ecr     = ECR("ECR\n(imágenes Docker)")

    # ═══════════════════════════════════════════════════════════
    # SISTEMAS EXTERNOS
    # ═══════════════════════════════════════════════════════════
    with Cluster("Sistemas Externos · BSS / CRM"):
        crm_saas   = Server("CRM SaaS\n(Salesforce)")
        erp_onprem = Server("ERP On-Premises\n(Facturación Unix)")
        itsm_azure = Server("ITSM Azure\n(Mesa de ayuda)")

    with Cluster("Sistemas Externos · OSS / Red"):
        vpn        = Server("VPN / PrivateLink")
        oss_onprem = Server("OSS On-Premises\n(ONT / OLT / BRAS)")
        inv_onprem = Oracle("Inventario Oracle\n(Topología de red)")
        nms        = Server("NMS Regionales\n(Alarmas on-prem)")

    with Cluster("Sistemas Externos · Notificaciones"):
        ses      = Server("Amazon SES\n(Email)")
        whatsapp = Server("WhatsApp\nBusiness API")
        ivr      = Server("IVR Call Center")

    with Cluster("Sistemas Externos · Analítica"):
        gcp_pub = Server("GCP Pub/Sub\n(Analítica fallas)")
        powerbi = Server("Power BI Azure\n(Tableros · SLA)")

    # ═══════════════════════════════════════════════════════════
    # CONEXIONES
    # ═══════════════════════════════════════════════════════════

    # Actores → Canales
    cliente    >> portal
    tecnico    >> app_movil
    agente_noc >> noc_ui
    agente_crm >> Edge(label="crea órdenes", style="dashed") >> apigw

    # Canales → Ingreso
    route53   >> cf
    portal    >> waf
    app_movil >> waf
    noc_ui    >> waf
    waf       >> cf
    cf        >> apigw
    crm_saas  >> apigw
    apigw     >> cognito
    cognito   >> Edge(style="dashed", label="token JWT") >> apigw

    # API Gateway → Microservicios
    apigw >> ms_orden
    apigw >> ms_prog
    apigw >> ms_act
    apigw >> ms_fac
    apigw >> ms_inv
    apigw >> ms_notif
    apigw >> ms_corr
    apigw >> ms_intred

    # Microservicios → Bases de datos
    ms_orden  >> rds_inst
    ms_prog   >> rds_inst
    ms_act    >> rds_act
    ms_fac    >> rds_act
    ms_inv    >> rds_inv
    ms_notif  >> dynamo
    ms_corr   >> rds_obs
    ms_intred >> rds_obs

    # Caché y deduplicación
    ms_prog   >> redis
    ms_fac    >> redis
    ms_inv    >> redis
    ms_corr   >> redis

    # Bus de eventos EventBridge
    ms_orden  >> eb
    ms_prog   >> eb
    ms_act    >> eb
    ms_fac    >> eb
    ms_inv    >> eb
    ms_corr   >> eb
    ms_intred >> eb

    # EventBridge → consumidores
    eb >> ms_notif
    eb >> ms_audit
    eb >> ms_inv
    eb >> ms_corr
    eb >> sqs_notif
    eb >> sqs_erp
    eb >> sqs_itsm

    # Kinesis — flujo alarmas de red
    nms         >> kinesis
    kinesis     >> lambda_norm
    lambda_norm >> ms_intred
    ms_intred   >> kinesis
    kinesis     >> ms_corr
    kinesis     >> kfh

    # Step Functions — saga activación
    ms_act >> sf
    sf     >> ms_orden
    sf     >> ms_fac
    sf     >> xray

    # Notificaciones
    sqs_notif >> ms_notif
    ms_notif  >> ses
    ms_notif  >> whatsapp
    ms_notif  >> ivr
    ms_notif  >> portal

    # Auditoría
    ms_audit >> opensrch
    ms_audit >> s3
    s3       >> Edge(style="dashed", label="lifecycle") >> glacier

    # Almacenamiento adicional
    ms_act  >> s3
    sqs_erp >> ms_fac

    # ITSM Azure
    sqs_itsm >> itsm_azure

    # ETL Inventario Oracle
    glue >> vpn
    vpn  >> inv_onprem
    glue >> ms_intred

    # KPIs / analítica
    kfh     >> redshift
    kfh     >> s3
    redshift >> powerbi
    gcp_pub >> Edge(style="dashed", label="analítica fallas") >> redshift

    # Observabilidad interna
    [ms_orden, ms_prog, ms_act, ms_fac, ms_inv,
     ms_corr, ms_intred, ms_notif, ms_audit] >> cw
    ms_act >> xray
    cw     >> grafana
    grafana >> powerbi
    sns    >> cw
    cloudtrail >> cw

    # Seguridad
    [ms_act, ms_notif, ms_fac, ms_intred] >> secrets
    kms >> Edge(style="dashed", label="cifrado") >> s3
    kms >> Edge(style="dashed", label="cifrado") >> rds_act
    ecr >> Edge(style="dashed", label="imágenes") >> ms_act
    ecr >> Edge(style="dashed", label="imágenes") >> ms_corr

    # Integraciones on-premises (VPN / PrivateLink)
    sf      >> vpn
    vpn     >> oss_onprem
    sqs_erp >> vpn
    vpn     >> erp_onprem
    ms_inv  >> vpn

print(f"Diagrama C4 Nivel 2 generado: {output}.png")
