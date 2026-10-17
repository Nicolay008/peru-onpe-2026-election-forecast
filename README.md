# Proyección electoral ONPE — Segunda Vuelta Perú 2026

Conjunto de herramientas en Python para seguir en tiempo real el conteo de la segunda vuelta presidencial peruana 2026 a partir de la API pública de resultados de la ONPE, proyectar el resultado final y estimar cuánto podía cambiar ese resultado según cómo se resolvieran las actas enviadas al Jurado Electoral Especial (JEE).

![Panel de gráficos generado por el script principal](img/onpe_graficos_130806.png)

## Componentes

El proyecto tiene cuatro scripts que cubren distintas etapas del análisis:

| Script | Qué responde |
|---|---|
| `onpe_analisis_electoral.py` | ¿Cómo va el conteo por región y macrorregión, y cómo evoluciona en el tiempo? |
| `onpe_proyeccion.py` | ¿Cuál será el resultado final si las actas pendientes votan como las ya contadas? ¿Qué tan sensible es al voto del exterior? |
| `onpe_impugnados.py` | ¿Qué porcentaje de las actas enviadas al JEE tendría que anularse para invertir el resultado? |
| `onpe_probabilidad.py` | Con tasas de anulación basadas en elecciones anteriores, ¿qué probabilidad hay de que el resultado se invierta? |

### 1. Monitoreo regional — `onpe_analisis_electoral.py`

En cada ejecución:

1. Detecta el proceso electoral activo en la API.
2. Obtiene los resultados nacionales y del extranjero por separado.
3. Consulta los 25 departamentos (incluido el Callao) y los agrupa en cinco macrorregiones: Norte, Centro, Sur, Oriente y Lima Metropolitana.
4. Proyecta los votos de cada región con avance entre 10 % y 99,5 %: `votos_actuales / (avance / 100)`.
5. Guarda un snapshot en el historial para seguir la evolución del conteo.
6. Genera un panel de cuatro gráficos: evolución del porcentaje de votos, avance del conteo, resultados por macrorregión y actas impugnadas por región.

Puede ejecutarse en modo continuo, actualizando cada cierto intervalo.

### 2. Proyección ponderada y sensibilidad — `onpe_proyeccion.py`

Para cada región estima los votos que faltan contar como:

```
votos_pendientes = actas_pendientes × votos_válidos_por_acta_de_la_región × proporción_de_cada_candidato
```

Usar los votos por acta de cada región, en lugar de un promedio nacional, evita que regiones con mesas más grandes o más pequeñas distorsionen la proyección. El mismo cálculo se aplica al voto del exterior.

Incluye un **análisis de sensibilidad** que recalcula el resultado final suponiendo distintos porcentajes (del 50 % al 70 %) para uno de los candidatos en las actas pendientes del exterior.

### 3. Punto de quiebre por actas en el JEE — `onpe_impugnados.py`

Estima, por región, cuántos votos hay en las actas enviadas al JEE (actas × votos por acta) y cuál es la ventaja neta de cada candidato en ellas. Con eso calcula:

- El resultado si el JEE anulara entre el 1 % y el 30 % de esas actas, de forma proporcional en cada región.
- El **porcentaje exacto de anulación** que invertiría el resultado.
- Un análisis específico de Lima, que concentraba la mayor parte de las actas observadas.

### 4. Simulación Monte Carlo — `onpe_probabilidad.py`

Ejecuta 100 000 simulaciones en las que la tasa de anulación de actas se modela con una distribución Beta, calibrada en cuatro escenarios construidos a partir de las segundas vueltas de 2011, 2016 y 2021. Considera dos supuestos:

- **Neutral:** las anulaciones afectan a todas las regiones por igual.
- **Lima con más impugnaciones:** Lima tiene una tasa de anulación 50 % mayor que el resto.

Reporta la probabilidad de que cada candidato gane, los percentiles de la diferencia final, un intervalo de confianza del 95 % y un histograma de la distribución simulada. Usa los datos del corte del 11/06/2026 a las 13:20.

## Limitaciones

- **Homogeneidad dentro de cada región.** Ambas proyecciones suponen que las actas pendientes de una región votan igual que las ya contadas. Las actas de zonas rurales o alejadas suelen llegar más tarde y pueden votar distinto.
- **Votos por acta promedio.** Se usa el promedio regional de votos válidos por acta, aunque el tamaño de las mesas varía dentro de cada región.
- **Calibración de la simulación.** Las tasas históricas de anulación están expresadas sobre el total de actas de cada elección, pero el modelo las aplica solo sobre las actas en revisión del JEE, que son un subconjunto. Esto probablemente subestima la tasa de anulación dentro de ese grupo.
- **Anulaciones proporcionales.** El análisis de punto de quiebre y la simulación suponen que las actas anuladas tienen la misma distribución de votos que el resto de su región.
- **Datos fijos en la simulación.** `onpe_probabilidad.py` usa valores de un momento concreto del conteo, no consulta la API.
- **Endpoints no documentados.** La API de la ONPE no es pública oficialmente; los endpoints estaban activos durante el conteo y pueden haber cambiado.

## Datos incluidos

- `data/onpe_historial.csv`: evolución del resultado nacional, una fila por consulta, con marca de tiempo completa.
- `data/snapshots/onpe_regional_HHMMSS.csv`: resultados por departamento en cada consulta. El nombre indica la hora de la captura.

La API solo muestra el estado actual del conteo, así que estos snapshots son el único registro de cómo fue evolucionando.

## Instalación y uso

```bash
pip install -r requirements.txt
```

```bash
# Monitoreo regional: una consulta, en modo continuo o filtrando una región
python onpe_analisis_electoral.py
python onpe_analisis_electoral.py --intervalo 90
python onpe_analisis_electoral.py --region Junín --sin-graficos

# Proyección ponderada con sensibilidad del exterior
python onpe_proyeccion.py

# Punto de quiebre por actas en el JEE
python onpe_impugnados.py

# Simulación Monte Carlo
python onpe_probabilidad.py
```

## Tecnologías

Python · pandas · NumPy · SciPy · Matplotlib · curl_cffi · tabulate · colorama

## Fuente de datos

Resultados oficiales publicados por la [ONPE](https://resultadosegundavuelta.onpe.gob.pe/) (Oficina Nacional de Procesos Electorales del Perú). Este proyecto es independiente y no está afiliado a la ONPE ni a ninguna organización política.
