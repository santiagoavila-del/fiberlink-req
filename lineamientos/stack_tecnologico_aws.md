## Stack Tecnológico

Proveedor Nube: AWS

Servicios:

- Cómputo:
  - Lambda: Elige Lambda cuando la carga de trabajo es intermitente o impredecible. El tráfico no es constante en el tiempo.
  - Fargate: Elige contenedores docker en Fargate cuando el tráfico es constante en el tiempo y además es alto (24/7). Se necesita que los microservicios siempre estén activos y respondan rápidamente.

- Contenedores:
  - Repositorio de imágenes docker: Elastic Container Registry (ECR)
  - Orquestador de contenedores: Preferencia de Elastic Container Service (ECS) sobre Elastic Kubernetes Service (EKS)

- Bases de datos:
  - SQL: Oracle (para aplicaciones on-premise), PostgresSQL para soluciones sobre AWS y AzureSQL para soluciones sobre Azure. 
  - NoSQL: DynamoDB

- Redes y Entrega de Contenidos:
  - Api Gateway: Api Gateway, Azure API Management

- Administración y gobierno:
  - Systems Manager (Parameter Store)
  - CloudTrail (Auditoría)

- Integración de Aplicaciones:
  - Step Functions
  - Simple Notification Service (SNS)
  - Simple Queue Service (SQS)
  - EventBridge
  - GCP Pub/Sub

- Observabilidad:
  - Métricas y Logs: CloudWatch
  - Trazas: X-Ray
  - Grafana

- Machine Learning:
  - Modelos Machine Learning: GCP BigQuery

- Análisis:
  - PowerBI Azure

- Seguridad, identidad y conformidad
  - Cognito
  - Secrets Manager
  - IAM
  - Key Management Service
  - WAF
