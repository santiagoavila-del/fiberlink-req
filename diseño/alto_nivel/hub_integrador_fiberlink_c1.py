"""
Diagrama C4 Nivel 1 — System Context
Hub Integrador FiberLink Andina Telecom
Generado con diagrams (https://diagrams.mingrammer.com)

C4 Nivel 1 muestra:
  - El sistema central (Hub Integrador)
  - Los actores/usuarios que interactúan con él
  - Los sistemas externos que se integran
Sin detallar componentes internos.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS
from diagrams.aws.general import General
from diagrams.onprem.compute import Server
from diagrams.onprem.client import User, Users
from diagrams.onprem.database import Oracle
from diagrams.aws.mobile import Amplify
from diagrams.aws.network import CloudFront
from diagrams.generic.blank import Blank

# ─────────────────────────────────────────────────────────────
# Atributos del grafo — estilo limpio para C4 Level 1
# ─────────────────────────────────────────────────────────────
graph_attr = {
    "fontsize": "13",
    "bgcolor": "#ffffff",
    "pad": "1.0",
    "splines": "ortho",
    "nodesep": "1.2",
    "ranksep": "1.6",
    "fontname": "Arial",
    "layout": "dot",
}

node_attr = {
    "fontsize": "11",
    "fontname": "Arial",
}

output = "hub_integrador_fiberlink_c1"

with Diagram(
    "C4 Nivel 1 — Contexto del Sistema\nHub Integrador · FiberLink Andina Telecom",
    filename=output,
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="TB",
    show=False,
):

    # ─────────────────────────────────────────────────────────
    # ACTORES / USUARIOS
    # ─────────────────────────────────────────────────────────
    with Cluster("Actores"):
        cliente     = User("Cliente\n(contrata / portal)")
        tecnico     = User("Técnico de Campo\n(app móvil)")
        agente_noc  = User("Agente NOC\n(portal monitoreo)")
        agente_crm  = User("Agente Comercial\n(CRM Salesforce)")

    # ─────────────────────────────────────────────────────────
    # SISTEMA CENTRAL
    # ─────────────────────────────────────────────────────────
    with Cluster("Sistema Central · AWS"):
        hub = ECS(
            "Hub Integrador\nFiberLink\n\n"
            "Plataforma central de integración,\n"
            "automatización y observabilidad\n"
            "(APIs · Eventos · Microservicios)"
        )

    # ─────────────────────────────────────────────────────────
    # SISTEMAS EXTERNOS — BSS / CRM
    # ─────────────────────────────────────────────────────────
    with Cluster("Sistemas BSS / CRM"):
        crm_saas    = Server("CRM SaaS\n(Salesforce)\nGestión comercial y contratos")
        erp_onprem  = Server("ERP On-Premises\n(Unix)\nMotor de facturación")
        itsm_azure  = Server("ITSM Azure\nMesa de ayuda / tickets")

    # ─────────────────────────────────────────────────────────
    # SISTEMAS EXTERNOS — OSS / RED
    # ─────────────────────────────────────────────────────────
    with Cluster("Sistemas OSS / Red"):
        oss_onprem  = Server("OSS On-Premises\nProvisión ONT / OLT / BRAS")
        nms         = Server("NMS Regionales\nAlarmas de red on-prem")
        inv_oracle  = Oracle("Inventario Oracle\nTopología y nodos de red")

    # ─────────────────────────────────────────────────────────
    # SISTEMAS EXTERNOS — CANALES / NOTIFICACIONES
    # ─────────────────────────────────────────────────────────
    with Cluster("Canales y Notificaciones"):
        portal_cliente = Server("Portal Cliente\n(Amplify · AWS)\nAutogestión y pagos")
        whatsapp    = Server("WhatsApp Business API\nNotificaciones al cliente")
        ses_email   = Server("Amazon SES\nNotificaciones por email")
        ivr         = Server("IVR Call Center\nNotificaciones de voz")

    # ─────────────────────────────────────────────────────────
    # SISTEMAS EXTERNOS — ANALÍTICA / DATOS
    # ─────────────────────────────────────────────────────────
    with Cluster("Analítica y Datos"):
        gcp_pubsub  = Server("GCP Pub/Sub\nAnalítica de fallas")
        powerbi     = Server("Power BI Azure\nTableros ejecutivos · SLA")

    # ═══════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════

    # Actores → Hub
    cliente     >> Edge(label="consulta estado /\nprogramación de instalación", color="#1a73e8") >> hub
    tecnico     >> Edge(label="confirma instalación /\ncaptura evidencias", color="#1a73e8") >> hub
    agente_noc  >> Edge(label="monitorea alarmas /\ncorrelación incidentes", color="#1a73e8") >> hub
    agente_crm  >> Edge(label="crea / modifica orden\nde instalación", color="#1a73e8") >> hub

    # Hub → actores (respuesta)
    hub >> Edge(label="estado del servicio /\nnotificaciones", style="dashed", color="#1a73e8") >> cliente

    # Hub ↔ BSS / CRM
    hub >> Edge(label="órdenes · activación ·\nestado de servicio", color="#e67e22") >> crm_saas
    crm_saas >> Edge(label="nuevas órdenes /\ncambios de plan", style="dashed", color="#e67e22") >> hub

    hub >> Edge(label="alta de cliente /\ncambio de plan", color="#e67e22") >> erp_onprem
    erp_onprem >> Edge(label="confirmación facturación", style="dashed", color="#e67e22") >> hub

    hub >> Edge(label="crea tickets de\nincidentes", color="#e67e22") >> itsm_azure

    # Hub ↔ OSS / Red
    hub >> Edge(label="provisión ONT /\nactivación OLT / BRAS", color="#27ae60") >> oss_onprem
    oss_onprem >> Edge(label="confirmación provisión /\nestado equipo", style="dashed", color="#27ae60") >> hub

    nms >> Edge(label="alarmas y eventos\nde red (streaming)", color="#27ae60") >> hub

    hub >> Edge(label="consulta inventario\nde red y nodos", color="#27ae60") >> inv_oracle
    inv_oracle >> Edge(label="topología · puertos ·\ncapacidad", style="dashed", color="#27ae60") >> hub

    # Hub → Canales / Notificaciones
    hub >> Edge(label="estado instalación /\nrecibos / servicio", color="#8e44ad") >> portal_cliente
    hub >> Edge(label="notificaciones\nal cliente", color="#8e44ad") >> whatsapp
    hub >> Edge(label="emails\ntransaccionales", color="#8e44ad") >> ses_email
    hub >> Edge(label="alertas\ncall center", color="#8e44ad") >> ivr

    # Hub ↔ Analítica
    gcp_pubsub >> Edge(label="analítica de fallas\nhistórica", style="dashed", color="#c0392b") >> hub
    hub >> Edge(label="KPIs · SLA ·\nmétrics operativas", color="#c0392b") >> powerbi

print(f"Diagrama C4 Nivel 1 generado: {output}.png")
