## Stack Tecnológico

Proveedor Nube: AWS

Servicios:

- Cómputo:
  - Lambda: Elige Lambda cuando la carga de trabajo es intermitente o impredecible. El tráfico no es constante en el tiempo.
  - Fargate: Elige contenedores docker en Fargate cuando el tráfico es constante en el tiempo y además es alto (24/7). Se necesita que los microservicios siempre estén activos y respondan rápidamente.

- Contenedores:
  - Repositorio de imágenes docker: Elastic Container Registry (ECR)
  - Orquestador de contenedores: Preferencia de Elastic Container Service (ECS) sobre Elastic Kubernetes Service (EKS)

- Almacenamiento:
  - Archivos: Simple Storage Service (S3)

- Bases de datos:
  - SQL: Aurora PostgreSQL (Si tienes más escrituras que lecturas) o Aurora MySQL (Si tienes más lecturas que escrituras)
  - NoSQL: DynamoDB
  - Caché: ElastiCache (Redis)

- Redes y Entrega de Contenidos:
  - CDN (Content Delivery Network): CloudFront
  - Api Gateway: Api Gateway
  - DNS (Domain Name System): Route 53

- Administración y gobierno:
  - Systems Manager (Parameter Store)
  - CloudTrail (Auditoría)
  - CloudFormation (IaC)

- Integración de Aplicaciones:
  - Step Functions
  - Simple Notification Service (SNS)
  - Simple Queue Service (SQS)
  - EventBridge

- Observabilidad:
  - Métricas y Logs: CloudWatch
  - Trazas: X-Ray
  - Grafana

- Machine Learning:
  - Modelos Machine Learning: SageMaker AI
  - Imágenes y Videos: Rekognition
  - : Textract
  - Agentes IA: Bedrock, Bedrock AgentCore

- Análisis:
  - Athena
  - Redshift
  - OpenSearch
  - Kinesis
  - Lake Formation
  - Glue

- Seguridad, identidad y conformidad
  - Cognito
  - Secrets Manager
  - IAM
  - Key Management Service
  - WAF

- FrontEnd:
  - Amplify
  - Location Service