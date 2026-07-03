## Rol / Persona
Actua como un Arquitecto de Solución experto en diseño de soluciones en nube

## Contexto
Un nuevo neobanco (Banco 100% digital) desea implementar una solución tecnológica nativa de nube

## Tarea / Objetivo 

Diseñar un core bancario nativo de nube considerando:
- Todos los requerimientos de carpeta "requerimientos"
- Todos los lineamientos de carpeta "lineamientos"
- Volumetría en archivo "volumetria.md"
- Será utilizado por los clientes del banco desde una App y Web de autoservicio

Realiza estos pasos:
  1. Diseño de Microservicios:
    - Crea una carpeta "diseño/alto_nivel/microservicios"
    - Diseña microservicios y por cada uno incluye: nombre, funcionalidades, estructura de su base de datos con sentencias sql. Para cada funcionalidad incluye su contrato de entrada y salida, algoritmo en pseudocódigo, lista de features y escenarios que cubre (código y descripción) y lista de lineamientos (código y descripción) que cubre. Genera un archivo markdown por cada microservicio.
  2. Diagrama de Secuencia (UML) entre Microservicios:
    - Crea una carpeta "diseño/alto_nivel/diagramas_secuencia"
    - Por cada archivo de requerimientos elabora un Diagrama de Secuencia, en formato mermaid, que utilice los microservicios y cubra todos los escenarios. Genera un archivo markdown por cada uno.
  3. Diagrama de Arquitectura (Servicios de Nube)
    - Elabora un Diagrama de Arquitectura (Architecture Diagram), en formato mermaid, que incluya todos los servicios de AWS necesarios incluyendo los microservicios del core bancario. Genera un archivo markdown "diagrama_arquitectura.md" en carpeta "diseño/alto_nivel"

## Requisitos de la respuesta
- Genera un archivo "decisiones_diseño.md" en carpeta "diseño/alto_nivel" que resuma los criterios de decisión principales tomados para el diseño propuesto. Indica el modelo LLM usado y la fecha como referencia.

## Elementos adicionales
- Si consideras que hay algún lineamiento relevante no indicado en carpeta "lineamientos", inclúyelo en el diseño pero indica explícitamente el criterio utilizado en el archivo "decisiones_diseño.md"
