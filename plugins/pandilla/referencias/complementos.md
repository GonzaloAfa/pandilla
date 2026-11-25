# Complementos

Skills y agentes de terceros que pandilla usa **si están instalados**. pandilla no copia su contenido: los nombra, los detecta y los carga en el paso que corresponde. Instalados en el usuario (`~/.claude`), valen para todos los proyectos; instalados en un repo (`.claude/`), solo para ese repo.

- **Qué hay instalado:** `<plugin>/scripts/complementos.sh` (tabla), `--faltan` (lo que falta, con su comando de instalación) y `--ruta <nombre>` (la ruta del archivo instalado).
- **Instalar:** `/pandilla:iniciar --complementos`. Nunca se instala nada sin preguntar.
- **Apagar uno en un proyecto:** en el perfil, sección «Complementos», línea `Apagados: <nombre>, …`. El perfil también puede agregar reglas propias (por ejemplo, `mobile-native` siempre que se toque una web que corre en webviews).
- **Si uno falta:** el paso sigue sin él y el informe lo dice en una línea («sin complemento <nombre>»). Ningún complemento es requisito.

## Cuándo se usa cada uno

| Paso | Condición | Complemento | Cómo |
|---|---|---|---|
| Alinear | Pedido de un comportamiento nuevo, con el resultado o el alcance difuso | `product-manager` | Subagente (`model: sonnet`, solo lectura) que redacta problema, no-objetivos y métrica de éxito en 15 líneas. Sus vacíos se vuelven preguntas de la ronda; su texto no se copia al brief |
| Alinear | Pedido de UI con la dirección abierta, y solo en una sesión con el usuario (`/entrega` o antes de despachar el lote) | `prototype` | Skill: variantes detrás de un selector en una ruta desechable. La variante elegida entra a «Decisiones» y la ruta se borra |
| Implementar | El pedido toca UI | `emil-design-foundations`, `emil-ui-polish` | La tarea carga las skills con la herramienta `Skill` antes de escribir UI. Las reglas del proyecto y su sistema de diseño mandan sobre las de la skill |
| Implementar | Web que corre en celular o en un webview | `mobile-native` | Igual que la anterior |
| Prueba local | El pedido toca UI | `break-ui` | Además del flujo normal, una pasada con datos extremos (nombres largos, vacíos, montos enormes, texto no latino) con capturas |
| Prueba local | El pedido toca UI | `evidence-collector` | Subagente (`model: sonnet`) que recorre las pantallas y deja capturas. Ignora su regla de «mínimo 3 a 5 problemas»: reporta solo lo que reprodujo, con captura |
| Prueba local | Cambia una API pública o un contrato entre servicios | `api-tester` | Subagente (`model: sonnet`) que prueba la API contra los servicios locales: casos válidos, inválidos, sin permiso y límites |
| Panel | El diff toca UI | `emil-ui-review` | Su `SKILL.md` (y `STANDARDS.md` si existe) va como «Complemento» al revisor `superficies`. Sus disparadores objetivos (accesibilidad mínima, salto de diseño, input menor a 16 px, hover sin alternativa táctil, `transition: all`) son W; jerarquía, espaciado y pulido son S |
| Panel | El diff toca UI y no está `emil-ui-review` | `accessibility-auditor` | Su archivo va como «Complemento» a `superficies`, solo para el piso de accesibilidad |
| Aceptar la prueba | Siempre que hay una prueba local | `reality-checker` | Subagente (`model: sonnet`, solo lectura) en contexto limpio que revisa la evidencia (tabla de cobertura, capturas, logs) contra el brief. Parte de «falta evidencia» y entrega LISTO o FALTA, con qué falta. Complementa la verificación del orquestador en `/lote`; en `/entrega` la reemplaza como revisión independiente de la prueba |

Los agentes se lanzan por su `name:` como `subagent_type` (por ejemplo `"Reality Checker"`). Las skills, con la herramienta `Skill` por su nombre, o leyendo la ruta que da `complementos.sh --ruta`.

## Fuentes

- Emil Kowalski, [emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT): `prototype`, `break-ui`, `mobile-native`. La serie `emil-design-foundations`, `emil-ui-polish` y `emil-ui-review` no está en ese repo: se instala a mano desde donde la consiga cada uno.
- [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT): `Product Manager`, `Reality Checker`, `Evidence Collector`, `API Tester`, `Accessibility Auditor`.
