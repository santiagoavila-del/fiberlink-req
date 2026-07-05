"""
Diagrama de Arquitectura — Hub Integrador FiberLink Andina Telecom
Iniciativas: I1 Plataforma de Integración | I2 Automatización Operacional | I3 Observabilidad
Generado con diagrams (https://diagrams.mingrammer.com)
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, Lambda, ECR
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift
from diagrams.aws.integration import Eventbridge, SQS, SNS, StepFunctions
from diagrams.aws.analytics import KinesisDataStreams, KinesisDataFirehose, Glue, ES as OpenSearch
from diagrams.aws.network import APIGateway, CloudFront, Route53
from diagrams.aws.security import WAF, Cognito, SecretsManager, KMS
from diagrams.aws.storage import S3, S3GlacierArchive
from diagrams.aws.management import Cloudwatch, Cloudtrail, Cloudformation
from diagrams.aws.devtools import XRay
from diagrams.aws.mobile import Amplify
from diagrams.onprem.database import Oracle
from diagrams.onprem.compute import Server
from diagrams.onprem.client import User


graph_attr = {
    "fontsize": "12",
    "bgcolor": "#f8f9fa",
    "pad": "0.6",
    "splines": "ortho",
    "nodesep": "0.7",
    "ranksep": "1.0",
    "fontname": "Arial",
}

node_attr = {
    "fontsize": "10",
    "fontname": "Arial",
}

output = "hub_integrador_fiberlink_v2"

with Diagram(
    "Hub Integrador FiberLink Andina Telecom\nI1: Integración  |  I2: Automatización  |  I3: Observabilidad",
    filename=output,
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="TB",
    show=False,
):

    # ─────────────────────────────────────────────────────
    # CANALES DE ENTRADA
    # ─────────────────────────────────────────────────────
    with Cluster("Canales de Entrada"):
        portal    = Amplify("Portal Cliente\n(Amplify)")
        app_movil = User("App Móvil\nTécnico")
        crm_saas  = Server("CRM SaaS\n(Salesforce)")
        noc_ui    = User("Portal NOC\n(Web UI)")

    # ─────────────────────────────────────────────────────
    # INGRESO Y SEGURIDAD
    # ─────────────────────────────────────────────────────
    with Cluster("Ingreso y Seguridad"):
        route53 = Route53("Route 53")
        waf     = WAF("WAF\n(OWASP + Rate Limit)")
        cf      = CloudFront("CloudFront\n(CDN + TLS 1.3)")
        apigw   = APIGateway("API Gateway\n(REST v1)")
        cognito = Cognito("Cognito\n(OAuth2/OIDC + MFA)")

    # ─────────────────────────────────────────────────────
    # HUB — INSTALACIÓN Y ACTIVACIÓN (ECS Fargate)
    # ─────────────────────────────────────────────────────
    with Cluster("Hub I1+I2 — Instalación y Activación (ECS Fargate)"):
        ms_orden = ECS("ms-orden\n-instalacion")
        ms_prog  = ECS("ms-programacion\n-instalacion")
        ms_act   = ECS("ms-activacion\n-servicio")
        ms_fac   = ECS("ms-facturacion")
        ms_inv   = ECS("ms-inventario")

    # ─────────────────────────────────────────────────────
    # HUB — OBSERVABILIDAD DE RED (ECS Fargate)
    # ─────────────────────────────────────────────────────
    with Cluster("Hub I3 — Observabilidad de Red (ECS Fargate)"):
        ms_corr   = ECS("ms-correlacion\n-incidentes")
        ms_intred = ECS("ms-integracion\n-red")

    # ─────────────────────────────────────────────────────
    # SERVERLESS
    # ─────────────────────────────────────────────────────
    with Cluster("Serverless"):
        ms_notif    = Lambda("ms-notificaciones")
        ms_audit    = Lambda("ms-auditoria")
        sf          = StepFunctions("Step Functions\n(Saga Activación)")
        lambda_norm = Lambda("Lambda\nNormalización NMS")
        glue        = Glue("AWS Glue\n(ETL Oracle)")

    # ─────────────────────────────────────────────────────
    # MENSAJERÍA Y EVENTOS
    # ─────────────────────────────────────────────────────
    with Cluster("Mensajería y Eventos"):
        eb          = Eventbridge("EventBridge\n(Bus Hub I1+I2)")
        kinesis     = KinesisDataStreams("Kinesis Streams\n(Alarmas de red I3)")
        sqs_notif   = SQS("SQS\nNotificaciones")
        sqs_erp     = SQS("SQS\nERP Integración")
        sqs_itsm    = SQS("SQS\nITSM Azure")
        sns         = SNS("SNS\nAlertas operativas")
        kfh         = KinesisDataFirehose("Kinesis Firehose\n(→ S3 / Redshift)")

    # ─────────────────────────────────────────────────────
    # ALMACENAMIENTO Y DATOS
    # ─────────────────────────────────────────────────────
    with Cluster("Almacenamiento y Datos"):
        rds_inst  = RDS("RDS PostgreSQL\n(órdenes + prog.)")
        rds_act   = RDS("RDS PostgreSQL\n(activación + fac.)")
        rds_inv   = RDS("RDS PostgreSQL\n(inventario)")
        rds_obs   = RDS("RDS PostgreSQL\n(correlación + red)")
        dynamo    = Dynamodb("DynamoDB\n(notificaciones)")
        redis     = ElastiCache("ElastiCache Redis\n(caché + dedup.)")
        s3        = S3("S3\n(contratos, evidencias)")
        opensrch  = OpenSearch("OpenSearch\n(auditoría)")
        glacier   = S3GlacierArchive("S3 Glacier\n(retención 5 años)")
        redshift  = Redshift("Redshift\n(KPIs + SLA)")

    # ─────────────────────────────────────────────────────
    # OBSERVABILIDAD
    # ─────────────────────────────────────────────────────
    with Cluster("Observabilidad"):
        cw      = Cloudwatch("CloudWatch\n(métricas + logs)")
        xray    = XRay("X-Ray\n(trazas)")
        grafana = Server("Grafana\n(dashboards)")
        powerbi = Server("Power BI Azure\n(tableros + SLA)")

    # ─────────────────────────────────────────────────────
    # SEGURIDAD Y GOBIERNO
    # ─────────────────────────────────────────────────────
    with Cluster("Seguridad y Gobierno"):
        secrets      = SecretsManager("Secrets Manager")
        kms          = KMS("KMS\n(cifrado)")
        cloudtrail   = Cloudtrail("CloudTrail")
        ecr          = ECR("ECR\n(imágenes Docker)")
        cfn          = Cloudformation("CloudFormation\n(IaC)")

    # ─────────────────────────────────────────────────────
    # SISTEMAS EXTERNOS / ON-PREMISES
    # ─────────────────────────────────────────────────────
    with Cluster("Sistemas Externos y On-Premises"):
        vpn        = Server("VPN / PrivateLink")
        oss_onprem = Server("OSS On-Premises\n(ONT/router/OLT)")
        erp_onprem = Server("ERP On-Premises\n(Facturación Unix)")
        inv_onprem = Oracle("Oracle\n(Inventario red)")
        nms        = Server("NMS Regionales\n(alarmas)")
        itsm_azure = Server("ITSM Azure\n(mesa de ayuda)")
        ivr        = Server("IVR\n(call center)")
        ses        = Server("Amazon SES\n(email)")
        whatsapp   = Server("WhatsApp\nBusiness API")
        gcp_pub    = Server("GCP Pub/Sub\n(analítica fallas)")

    # ═══════════════════════════════════════════════════════
    # CONEXIONES
    # ═══════════════════════════════════════════════════════

    # Canales → Ingreso
    route53   >> cf
    portal    >> waf
    app_movil >> waf
    noc_ui    >> waf
    waf       >> cf
    cf        >> apigw
    crm_saas  >> apigw
    apigw     >> cognito
    cognito   >> Edge(style="dashed", label="token") >> apigw

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
    ms_orden >> rds_inst
    ms_prog  >> rds_inst
    ms_act   >> rds_act
    ms_fac   >> rds_act
    ms_inv   >> rds_inv
    ms_notif >> dynamo
    ms_corr  >> rds_obs
    ms_intred >> rds_obs

    # Caché y deduplicación
    ms_prog  >> redis
    ms_fac   >> redis
    ms_inv   >> redis
    ms_corr  >> redis

    # Bus de eventos Hub (EventBridge)
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
    nms          >> kinesis
    kinesis      >> lambda_norm
    lambda_norm  >> ms_intred
    ms_intred    >> kinesis
    kinesis      >> ms_corr
    kinesis      >> kfh

    # Step Functions (saga activación)
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
    kfh      >> redshift
    kfh      >> s3
    redshift >> powerbi
    gcp_pub  >> Edge(style="dashed", label="analítica fallas") >> redshift

    # Observabilidad
    [ms_orden, ms_prog, ms_act, ms_fac, ms_inv, ms_corr, ms_intred] >> cw
    [ms_notif, ms_audit] >> cw
    ms_act    >> xray
    cw        >> grafana
    grafana   >> powerbi
    sns       >> cw
    cloudtrail >> cw

    # Seguridad
    [ms_act, ms_notif, ms_fac, ms_intred] >> secrets
    kms >> Edge(style="dashed", label="cifrado") >> s3
    kms >> Edge(style="dashed", label="cifrado") >> rds_act
    ecr >> Edge(style="dashed", label="imágenes") >> ms_act
    ecr >> Edge(style="dashed", label="imágenes") >> ms_corr

    # Integraciones on-premises
    sf      >> vpn
    vpn     >> oss_onprem
    sqs_erp >> vpn
    vpn     >> erp_onprem
    ms_inv  >> vpn

print(f"Diagrama generado: {output}.png")
