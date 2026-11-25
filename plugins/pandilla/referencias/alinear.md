# Alinear un pedido

Lo usan `/pandilla:lote` (en «Preparar», antes de despachar) y `/pandilla:entrega` (paso 0). Una tarea del lote corre sola y no puede preguntarle nada al usuario: cada decisión que quede abierta al despachar la toma el agente a ciegas. Alinear es cerrar esas decisiones antes.

Basado en la skill `grilling` de Matt Pocock ([mattpocock/skills](https://github.com/mattpocock/skills), MIT).

## Hechos y decisiones

- **Un hecho lo averiguas tú**, nunca se lo preguntas al usuario: si el problema sigue en la base, qué hace hoy el código, qué dice el ticket y sus comentarios, qué dejaron intentos anteriores (informes de lotes, PRs cerrados, notas o memoria del proyecto), cuántos casos hay en producción. Producción solo si el perfil lo permite y con sus reglas; si no, anota el dato como «no verificado». Cuando un intento anterior contradice al ticket, gana la evidencia más reciente y reproducible, y la contradicción va en la pregunta. Si la investigación es larga, lánzala en un subagente de solo lectura y sigue con las preguntas que no dependen de ella.
- **Una decisión es del usuario:** qué resultado espera, qué queda fuera, qué regla de negocio aplica, qué dirección toma una pantalla, qué hacer si la premisa ya no se cumple.

## Qué revisar por pedido

1. **Tipo:** `bug` (algo que funcionaba o debía funcionar falla) o `cambio` (comportamiento nuevo o distinto).
2. **Premisa:** el problema existe hoy en la base. Es un hecho: verifícalo. Si no se cumple, la pregunta es qué hacer (cerrar, reformular o probar con otros datos).
3. **Síntoma exacto** (solo `bug`): qué ve quién, dónde, con qué datos, y qué debería ver. Sale del ticket, de los logs o de la reproducción. Si no se puede precisar, es una pregunta. Si la premisa no se cumple, escribe «no reproducible: <por qué>» y la pregunta pasa a ser qué hacer con el pedido.
4. **Resultado esperado:** qué cambia para quién usa el producto, en una frase.
5. **Bordes:** qué queda fuera de alcance, y los casos vecinos que el pedido no menciona (otro país, sin sesión, sin configuración, datos existentes). Un problema vecino que encuentres va a «Fuera de alcance» con la propuesta de un ticket aparte; solo es pregunta si meterlo o no cambia lo que hará esta tarea.
6. **Reglas de negocio** que el cambio fija o altera.
7. **Cómo se prueba:** el flujo completo que recorrerá la prueba local.

## Rondas

- Pregunta en rondas. Una ronda junta todas las preguntas que ya se pueden responder sin esperar otra respuesta. Las que dependen de otra pregunta abierta van en la ronda siguiente.
- En `/lote`, una sola ronda para todos los pedidos, agrupada por pedido.
- Cada pregunta lleva tu respuesta recomendada y está redactada para que «sí» la acepte:

```
**<ID> · P1 · <título>**: <pregunta, con las opciones si las hay>
➡️ Recomiendo: <respuesta y por qué, en una línea>
```

- Un pedido sin decisiones abiertas no lleva preguntas: lista sus supuestos en una línea («Supuestos: …») para que el usuario pueda vetarlos.
- Si el usuario pidió lanzar sin preguntas, aplica las respuestas recomendadas y márcalas como `asumida` en el brief y en el resumen final. Un pedido que cambia una regla de negocio sin una decisión tomada no se lanza nunca de esta forma.

## Cuándo termina

La alineación termina cuando cada pedido tiene su tipo, su premisa verificada, su síntoma exacto (si es `bug`) y ninguna decisión abierta, y el usuario respondió la última ronda. Su resultado va al brief, en «Decisiones»:

```
Tipo: bug | cambio
Premisa: verificada en <base> (<cómo>) | no se cumple → <decisión del usuario>
Síntoma exacto: <qué ve quién, dónde, con qué datos; qué debería ver>   (solo bug)
Decisiones:
- <decisión> (usuario | recomendada aceptada | asumida)
Fuera de alcance: <lista>
```

El panel recibe estas decisiones con el pedido: no son hallazgos, salvo que el código las contradiga.
