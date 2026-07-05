## Rol / Persona
Actua como un Arquitecto de Solución experto en diseño de soluciones en nube

## Contexto
El nombre de la empresa es FiberLink Andina Telecom, una empresa del secitor telecomunicaciones, que ofrece servicio de internet fijo por fibra optica, conectividad empresarial, enlaces duplicados, telefonia IP y servicios administados por red.La aspiración del directorio es operar como una telco digital: vender con disponibilidad real,provisionar automáticamente, monitorear de extremo a extremo, atender proactivamente y retenerclientes con información confiable. Para ello necesita una arquitectura que integre OSS, BSS,canales, red, datos y nubes.
La cadena de valor analizada abarca las siguientes fases:
Fase 1: Captación de clientes.Considerar: El CRM comercial es SaaS. El portal web corre en AWS con base PostgreSQL administrada. La appmóvil consume APIs en Azure API Management. El inventario de red está en Oracle on premises ycontiene nodos, CTO, puertos, splitters, rutas y capacidad. Los mapas GIS heredados de operadores adquiridos se guardan en servidores locales y archivos shapefile. Los vendedores de campo usantablets con una aplicación offline que sincroniza al final del día.
Fase 2: Instalación del servicio. Considerar: Las órdenes se originan en el CRM y pasan al sistema de gestión de órdenes alojado en Azure SQL.La agenda de cuadrillas está en un SaaS de field service. El inventario de equipos se administra en elERP on premises. La provisión de ONT y router se realiza desde una plataforma OSS local. Lostécnicos usan una app móvil que captura fotos, señal óptica, serie de equipo y firma del cliente.
Fase 3: Activación del servicio. Considerar: La plataforma de provisión corre on premises y se comunica con OLT (Terminal de Línea Óptica),BRAS (Broadband Remote Access Server) y sistemas de autenticación. El CRM mantiene el contrato.Facturación tiene el plan y ciclo de cobro. El portal de clientes en AWS muestra estado del servicio. ElNOC monitorea alarmas en herramientas locales. La activación se confirma mediante mensajes entresistemas, pero algunas respuestas quedan pendientes o duplicadas.
Fase 4: Operación del servicio. Las herramientas NMS están instaladas en data centers regionales. Los logs de red se almacenan enservidores locales con retención limitada. Parte de los eventos se envía a GCP Pub/Sub paraanalítica de fallas, pero no todos los equipos están integrados. Los tableros ejecutivos se muestran enPower BI sobre Azure. El call center usa una plataforma de mesa de ayuda en Azure que no recibealarmas en tiempo real.
Fase 5: Facturación del servcicio. El motor de facturación está on premises en servidores Unix heredados. Recibe altas y cambios delCRM, estados de activación del OSS, pagos de pasarelas SaaS y consumos de serviciosempresariales. El portal de clientes en AWS muestra recibos y permite pagar. La conciliación bancariase procesa en el ERP. Las promociones se gestionan en CRM, pero no siempre llegan con la mismaregla a facturación.
Fase 6: Retención del cliente. El modelo de churn se ejecuta en GCP BigQuery con datos de facturación, tickets, pagos ycampañas. El CRM SaaS muestra propensión, pero se actualiza semanalmente. Los eventos de redno llegan con suficiente detalle por cliente. El portal y la app registran interacciones en AWS. Lascampañas de retención se ejecutan desde un SaaS de marketing.

## Proyecto / Objetivo 

Diseñar una solución que considere 3 iniciativas:
1.Implementación de una plataforma de integración empresarial. 
1.1.Objetivo:Implementar una plataforma centralizada de integración basada en APIs y eventos para eliminar las integraciones punto a punto y habilitar una arquitectura escalable y desacoplada.
1.2. Problema que resuelve: La integración actual genera dependencia entre aplicaciones, duplicidad de lógica de negocio y altos costos de mantenimiento.
1.3.Beneficios esperados:
-Reducir el tiempo de integración mediante un Hub con APIs reutilizables.
-Disminuir la complejidad operativa sustituyendo integraciones punto a punto.
-Incrementar la reutilización de servicios mediante APIs de negocio estandarizadas.
-Mejorar la trazabilidad incorporando monitoreo de extremo a extremo.
-Facilitar la evolución tecnológica desacoplando las aplicaciones.

2.Automatización y mejoras operacionales.
2.1.Objetivo:Automatizar procesos críticos para reducir tareas manuales y mejorar la eficiencia en la provisión y gestión de servicios.
2.2.Problema que resuelve:Los procesos entre CRM, OSS, Inventario y Facturación dependen de actividades manuales que generan retrasos y errores.
2.3.Beneficios esperados:
-Reducir los tiempos de provisión mediante flujos automatizados.
-Disminuir errores operativos eliminando tareas repetitivas.
-Incrementar la productividad del personal operativo.
-Mejorar el cumplimiento de los SLA mediante automatización.
Incrementar la trazabilidad de los procesos operacionales.

3.Plataforma de observabilidad.
3.1.Objetivos:Centralizar métricas, logs, trazas y eventos para mejorar el monitoreo y la operación.
3.2.Problemas que resuelve:La información operacional está distribuida en diferentes herramientas, dificultando detectar incidentes y analizar causas raíz.
3.3.Beneficios esperados:
-Reducir los tiempos de detección y resolución de incidentes.
-Incrementar la disponibilidad mediante monitoreo proactivo.
-Mejorar la visibilidad operacional con dashboards unificados.
-Optimizar la toma de decisiones basada en datos.
-Mejorar la experiencia del cliente mediante indicadores operativos.

Se debe considerar:
- Todos los requerimientos de carpeta "requerimientos"
- Todos los lineamientos de carpeta "lineamientos"
- Volumetría en archivo "volumetria.md"


Realiza estos pasos:
  1. Diseño de Microservicios:
    - Crea una carpeta "diseño/alto_nivel/microservicios"
    - Diseña microservicios y por cada uno incluye: nombre, funcionalidades, estructura de su base de datos con sentencias sql. Para cada funcionalidad incluye su contrato de entrada y salida, algoritmo en pseudocódigo, lista de features y escenarios que cubre (código y descripción) y lista de lineamientos (código y descripción) que cubre. Genera un archivo markdown por cada microservicio.
  2. Diagrama de Secuencia (UML) entre Microservicios:
    - Crea una carpeta "diseño/alto_nivel/diagramas_secuencia"
    - Por cada archivo de requerimientos elabora un Diagrama de Secuencia, en formato mermaid, que utilice los microservicios y cubra todos los escenarios. Genera un archivo markdown por cada uno.
  3. Diagrama de Arquitectura (Servicios de Nube)
    - Elabora un Diagrama de Arquitectura (Architecture Diagram), en formato mermaid, que incluya todos los servicios de AWS necesarios incluyendo los microservicios requeridos para las mejoras operativas. Genera un archivo markdown "diagrama_arquitectura.md" en carpeta "diseño/alto_nivel"

## Requisitos de la respuesta
- Genera un archivo "decisiones_diseño.md" en carpeta "diseño/alto_nivel" que resuma los criterios de decisión principales tomados para el diseño propuesto. Indica el modelo LLM usado y la fecha como referencia.

## Elementos adicionales
- Si consideras que hay algún lineamiento relevante no indicado en carpeta "lineamientos", inclúyelo en el diseño pero indica explícitamente el criterio utilizado en el archivo "decisiones_diseño.md"
