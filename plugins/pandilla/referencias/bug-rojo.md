# Bug: primero un comando rojo

Para los pedidos de tipo `bug`, antes de tocar código. Lo usan el brief de `/pandilla:lote` (paso 1) y `/pandilla:entrega` (paso 0). No reemplaza la prueba local completa rojo/verde: es el ciclo rápido con el que se encuentra la causa; la prueba completa demuestra después el arreglo por la entrada real.

Basado en la skill `diagnosing-bugs` de Matt Pocock ([mattpocock/skills](https://github.com/mattpocock/skills), MIT).

## 1. Comando rojo

Construye **un comando** (un test, un script, un curl o una consulta GraphQL contra local) y córrelo al menos una vez. Cumple las cuatro condiciones:

- **Rojo por el síntoma exacto:** recorre el código del bug y comprueba el síntoma exacto del brief, no un error cercano. «No se cayó» no sirve.
- **Repetible:** da el mismo resultado en cada corrida. Si el bug es intermitente, sube la tasa de reproducción (repetir, paralelizar, fijar tiempos) hasta que sea alta y estable.
- **Rápido:** segundos, no minutos.
- **Sin una persona:** lo corres tú, sin que nadie haga clic.

En orden de preferencia: un test en el punto donde el bug se ve; un curl o GraphQL contra los servicios locales; un script de navegador que comprueba la pantalla; repetir un payload o evento real guardado; correr la misma entrada en la base y en otra versión y comparar.

**Antes de creer el rojo, verifica el arnés.** Un rojo puede venir del script y no del bug: un selector que hace clic en otro botón, datos sembrados mal, un servicio abajo. Confirma que cada paso del comando hizo lo que pretendías (captura, log o respuesta de ese paso) y que el mensaje de falla coincide con el síntoma exacto. Córrelo dos veces.

Si no logras un comando rojo, para. Lista lo que intentaste y termina con una de estas salidas, nunca con una hipótesis sin comando:

- **NO SE REPRODUCE:** el síntoma no aparece con datos y pasos equivalentes a los del reporte. Deja la evidencia de lo que corriste. Es un resultado válido: se propone cerrar el ticket o pedir más datos.
- **BLOQUEADO:** falta algo para reproducir (acceso, datos, un servicio). Di qué.

Completo cuando puedes mostrar el comando, su salida roja (con secretos reemplazados por `<REDACTED>`) y la evidencia de que el arnés hizo lo que debía.

## 2. Reducir

Recorta del caso entradas, pasos, datos y configuración, uno a la vez, corriendo el comando después de cada corte. Completo cuando quitar cualquier elemento restante lo vuelve verde.

## 3. Hipótesis

Escribe de 3 a 5 hipótesis ordenadas antes de probar ninguna. Cada una con su predicción: «Si la causa es X, cambiar Y hace desaparecer el bug». Una hipótesis sin predicción se descarta. En `/entrega`, muéstralas al usuario y sigue sin esperar; en `/lote`, van en el informe de la tarea.

## 4. Instrumentar

Cada prueba responde a la predicción de una hipótesis y cambia una sola variable. Todo log temporal lleva la marca `[DEBUG-<4 hex>]`, la misma en toda la tarea, para borrarlos con un grep. Si el bug es de rendimiento, mide primero una línea base y después compara.

## 5. Arreglo y test de regresión

1. Convierte el caso reducido en un test que falla, en un punto donde el test recorra el bug tal como ocurre en quien llama. Si el área no tiene un punto así, anótalo como hallazgo en el informe: la arquitectura impide fijar el bug con un test.
2. Mira el test fallar.
3. Arregla.
4. Mira el test pasar y corre de nuevo el comando rojo original, sin reducir: tiene que salir verde.

## 6. Cierre

- `git grep -n "\[DEBUG-"` no devuelve nada.
- El commit y el PR dicen la causa confirmada y las hipótesis descartadas: «Causa: …. Descartadas: …».
- Sigue con la prueba local completa rojo/verde de `/pandilla:entrega` (paso 3).
