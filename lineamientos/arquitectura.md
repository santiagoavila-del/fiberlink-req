## Lineamientos de Arquitectura

Objetivos:
- Busca que la solución sea mantenible, modular y evolutiva.
- Responde a: ¿Cómo construimos una solución ordenada y fácil de evolucionar?

Lineamientos:
- ARQ-01: La solución debe separarse por capas o dominios con responsabilidades claras.
- ARQ-02: Debe evitarse el acoplamiento fuerte entre componentes.
- ARQ-03: Cada servicio o módulo debe tener una responsabilidad bien definida.
- ARQ-04: La arquitectura debe favorecer bajo acoplamiento y alta cohesión.
- ARQ-05: Deben preferirse contratos explícitos entre componentes sobre dependencias implícitas.
- ARQ-06: Las reglas de negocio no deben quedar embebidas en canales o interfaces.
- ARQ-07: Los componentes deben poder evolucionar con mínimo impacto lateral.
- ARQ-08: Deben definirse criterios claros para decidir entre monolito, microservicios o serverless
