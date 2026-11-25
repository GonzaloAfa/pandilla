# Diseño simple

Cuatro preguntas para que el código no crezca ni se repita. No imponen una arquitectura: preguntan si cada pieza nueva se justifica, y la respuesta por defecto es «menos». Las reglas escritas del proyecto (`CLAUDE.md`, el perfil) mandan sobre estas.

Basado en `codebase-design` y la lista de malos olores de `code-review` de Matt Pocock ([mattpocock/skills](https://github.com/mattpocock/skills), MIT), que a su vez vienen de Ousterhout y Fowler.

## Las cuatro preguntas

1. **¿Ya existe algo que hace esto?** Antes de escribir una función, un tipo, un componente o una consulta, búscalo en el repo (`git grep` por el concepto, no solo por el nombre). Si existe, úsalo; si casi sirve, extiéndelo. Dos copias de una regla de negocio terminan contradiciéndose.
2. **Si lo borro, ¿la complejidad desaparece o se reparte entre quienes lo llaman?** Un wrapper, servicio o capa que solo pasa datos de un lado a otro desaparece sin perder nada: sobra. Un módulo se gana su lugar cuando esconde mucho detrás de una interfaz chica.
3. **¿Hay un segundo uso real hoy?** Una interfaz con una sola implementación, un parámetro o flag para un caso que nadie pidió, una configuración «por si acaso»: se escriben cuando aparece el segundo uso, no antes. La tercera repetición es la señal para extraer.
4. **¿Un cambio de negocio se hace en un solo lugar?** Si cambiar una regla obliga a tocar muchos archivos, la regla no tiene dueño. Junta lo que cambia junto.

Además: nombres que dicen lo que hacen, con el vocabulario del dominio del proyecto; flujo explícito con cláusulas de guarda en vez de anidar.

## Mapa de reutilización

Antes de implementar, la tarea escribe en su informe:

```
Reutiliza: <función/módulo existente> (<ruta>) para <qué>
Nuevo: <pieza nueva> — <por qué no sirve lo existente, en una línea>
```

Cada pieza nueva sin su línea es un hallazgo del revisor `diseno`.

## Severidad en el panel

- **W:** lógica de negocio duplicada (la misma regla, cálculo o validación escrita dos veces, en el diff o contra código existente); una abstracción nueva (interfaz, capa, clase base, fábrica) con un solo uso; un wrapper que solo delega; una regla escrita del proyecto sobre diseño rota.
- **S:** nombres que no dicen lo que hacen, parámetros que viajan siempre juntos, funciones largas que se leerían mejor partidas, condicionales repetidos que pedirían un mapa.
- Nunca: preferencias de estilo que el linter ya cubre, ni pedir una capa o patrón que el cambio no necesita.
