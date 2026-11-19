# cuadrilla

Plugin de [Claude Code](https://claude.com/claude-code) para poner a varios agentes a trabajar en paralelo en tu repo, cada uno en su propio git worktree. Antes de commitear, cada cambio pasa por un panel de revisores y un verificador que intenta refutarlos. Un tablero local te muestra en vivo qué está haciendo cada agente.

```
/cuadrilla:lote "arreglar el doble envío del formulario" "agregar export CSV de pedidos"
```

Cada pedido sigue el mismo flujo:

1. Su worktree, con puertos propios.
2. Implementación con un test rojo primero.
3. Compuertas: formato, lint, tipos y tests.
4. `/cuadrilla:panel`, con hasta 3 vueltas de corrección.
5. Prueba local rojo/verde.
6. Regresión de flujos críticos.
7. Un commit, y un PR o un commit local según el perfil del proyecto.
8. Revisión independiente en una sesión limpia.

Nunca mergea. Nunca toca producción.

## Qué trae

| | |
|---|---|
| `/cuadrilla:lote` | Orquesta N tareas en paralelo (máximo 4 activas por defecto) y lleva el estado y el resumen |
| `/cuadrilla:entrega` | El mismo ciclo para una sola tarea, en tu rama actual |
| `/cuadrilla:panel` | Revisores en paralelo (Sonnet), elegidos por las rutas que toca el diff, y un verificador (Opus) que descarta los falsos positivos. Veredicto: APROBADO o CAMBIOS REQUERIDOS |
| `/cuadrilla:iniciar` | Lee tu repo, te hace 3 o 4 preguntas y escribe el perfil `.claude/cuadrilla.md` |
| `/cuadrilla:tablero` | Tablero local en http://localhost:7788: cada sesión como una mesa, con sus subagentes, herramientas, tokens, hallazgos y veredictos |
| Revisores | `correctitud`, `sistemas`, `seguridad`, `datos`, `superficies`, `infra`, `costos` y el `verificador` |
| `scripts/` | `entorno.sh` (puertos propios por worktree, instalación, permisos negados), `wt` (corre un comando con ese entorno) y `fila.sh` (fila para recursos que solo admiten uno a la vez) |

## Instalar

```
/plugin marketplace add GonzaloAfa/cuadrilla
/plugin install cuadrilla@cuadrilla
```

Después, en cada repo donde lo quieras usar:

```
/cuadrilla:iniciar
```

Requisitos: git, Python 3 (para el tablero y el hook) y `gh` si las tareas publican PRs. Opcional: [T3 Code](https://t3.codes).

## Cómo funciona

### El perfil del proyecto

Todo lo específico de tu repo vive en `.claude/cuadrilla.md`, versionado y editable:

- rama base;
- compuertas y fallas conocidas;
- cómo aislar los worktrees;
- qué revisor mira qué rutas;
- flujos críticos;
- si se publica un PR o se deja un commit local;
- si se puede medir producción y cómo;
- qué tienen prohibido las tareas.

Las skills no traen nada de ningún proyecto: leen el perfil. En [`ejemplos/`](ejemplos/) hay dos perfiles completos.

Puedes sumar revisores propios en `.claude/cuadrilla/revisores/<nombre>.md`, por ejemplo uno de reglas clínicas o de pagos. También puedes complementar uno del plugin con las reglas de tu dominio.

### Aislamiento entre worktrees

Varios agentes a la vez chocan en tres cosas: puertos, bases de datos compartidas y recursos únicos. `entorno.sh` asigna puertos libres a cada worktree, sin repetir los de otros worktrees aunque estén apagados, y los deja en `.wt-env`. Cada comando corre con `wt <comando>`. Lo que no se puede duplicar, como un simulador o un e2e pesado, va en fila con `fila.sh`.

Si tu proyecto necesita una base por worktree, `/cuadrilla:iniciar` te ayuda a escribir un script propio en `scripts/cuadrilla/`.

### Dos motores

- **Con [T3 Code](https://t3.codes)** (si existe la herramienta `delegate_task`): cada tarea es un hilo con su worktree y corre su propio panel.
- **Solo Claude Code:** cada tarea es un subagente con `isolation: "worktree"`. Como un subagente no puede lanzar subagentes, el orquestador corre el panel sobre su worktree y le devuelve los hallazgos.

### Seguridad

- Las tareas corren sin supervisión y pueden leer texto de terceros (tickets, issues). Por eso nunca consultan producción. Si el perfil lo permite, las mediciones (solo lectura y solo agregados) las hace el orquestador, con una consulta que escribe él.
- `entorno.sh --negar <herramienta>` niega en cada worktree las herramientas que alcanzan producción, por ejemplo un servidor MCP de base de datos.
- Nada de push intermedio: un commit, un push, un PR. El merge siempre lo hace una persona.

### El tablero

El plugin registra un hook en los eventos de sesión, herramientas y subagentes. El hook anota un resumen corto de cada evento en `~/.claude/cuadrilla/events.jsonl`, que rota a los 20 MB. `/cuadrilla:tablero` levanta un servidor que solo escucha en `127.0.0.1`. Nada sale de tu computador.

Variables de entorno:

- `CUADRILLA_DIR`: carpeta del archivo de eventos;
- `CUADRILLA_PUERTO`: puerto del tablero.

## Por qué así

- **Un verificador adversarial** que descarta lo que no puede reproducir leyendo el código. Sin él, el ruido de los revisores tapa los hallazgos reales.
- **Regresión obligatoria con evidencia** antes de decir «listo para merge»: mapa de quienes consumen lo que cambió, tests en la base frente a la rama, y cada flujo crítico probado de punta a punta.
- **Revisión independiente en una sesión limpia**: quien implementó no se revisa a sí mismo.

## Licencia

[MIT](LICENSE)
