# 🏀 NBA Score Predictor — El Oráculo

> **Modelo de Machine Learning que predice el marcador final de los partidos de la NBA en tiempo real.**  
> Construido con datos reales de la NBA API v3, ingeniería de features avanzada y un Random Forest entrenado solo con la era moderna del baloncesto (2022+).

---

## ¿Qué hace este proyecto?

El Oráculo descarga la cartelera del día directamente desde la NBA, calcula estadísticas avanzadas de cada equipo y predice el marcador, el total de puntos y el ganador probable de cada partido — todo de forma automática.

No es solo un modelo de juguete. Tiene auditoría de predicciones, historial de aciertos y un pipeline completo de datos que va desde los servidores de la NBA hasta un dashboard web funcional.

---

## ⚙️ Pipeline Completo

```
[NBA API v3]
     │
     ▼
data_fetcher.py          ← Descarga todos los juegos de los 30 equipos
     │
     ▼
data_processing.py       ← Limpia y crea las features (EWMA, B2B, DEF_EFF, 3P%)
     │
     ▼
prepare_training_data.py ← Construye el dataset de matchups (Local vs Visitante)
     │
     ▼
model_trainer.py         ← Entrena el Random Forest (filtrado a era 2022+)
     │
     ▼
nba_predictor.py         ← Lee la cartelera del día y exporta predicciones.json
     │
     ▼
index.html               ← Dashboard web que muestra los picks del día
```

---

## 🧠 Features del Modelo

El modelo no solo mira cuántos puntos anota un equipo — incorpora la interacción **ofensa vs. defensa rival** para estimar puntos esperados de forma relativa al contexto del partido.

| Feature | Descripción |
|---|---|
| `PTS_SEASON_AVG` | Promedio de puntos anotados en la temporada (rolling) |
| `PTS_EWMA` | Media móvil exponencial de los últimos 10 juegos |
| `DEF_SEASON_AVG` | Promedio de puntos **permitidos** en la temporada |
| `DEF_EFF_EWMA` | Eficiencia defensiva reciente (EWMA) |
| `3P_PCT_EWMA` | Porcentaje de triples reciente |
| `IS_B2B` | Flag si el equipo juega en back-to-back |
| `EXPECTED_HOME_PTS` | `(HOME_EWMA + AWAY_DEF_EFF_EWMA) / 2` |
| `EXPECTED_AWAY_PTS` | `(AWAY_EWMA + HOME_DEF_EFF_EWMA) / 2` |
| `EXPECTED_TOTAL` | Suma de los puntos esperados de ambos equipos |

> **¿Por qué filtrar a 2022+?**  
> Los datos históricos de equipos como los Spurs de Popovich o los Raptors campeones distorsionaban al modelo — esos equipos jugaban partidos de ~175 pts totales que hoy simplemente no existen. Filtrar a la era moderna hace el modelo mucho más preciso.

---

## 🔁 Auditoría Automática — `nba_backtester.py`

Cada predicción generada se guarda en `predictions_history.csv`. El backtester cruza esas predicciones con los resultados reales de la NBA y calcula:

- ✅ Efectividad de predicción del ganador
- 📉 Error promedio en el total de puntos
- 📊 Historial completo por partido

---

## 🚀 Cómo correrlo

### 1. Instala dependencias

```bash
pip install nba_api pandas numpy scikit-learn joblib
```

### 2. Descarga los datos (solo la primera vez o para actualizar)

```bash
python data_fetcher.py
```

### 3. Procesa y limpia los datos

```bash
python data_processing.py
python prepare_training_data.py
```

### 4. Entrena el modelo

```bash
python model_trainer.py
```

### 5. Genera las predicciones del día

```bash
python nba_predictor.py
```

### 6. Abre el Dashboard

Abre `index.html` en tu navegador. Ya aparecen los picks del día cargados desde `predictions.json`.

---

## 📁 Estructura del Proyecto

```
📦 NBA-Predictor/
 ├── data_fetcher.py           # Descarga datos crudos de la NBA API v3
 ├── data_processing.py        # Limpieza y feature engineering
 ├── prepare_training_data.py  # Construcción del dataset de matchups
 ├── model_trainer.py          # Entrenamiento del Random Forest
 ├── nba_predictor.py          # Predictor diario + exportación a JSON
 ├── nba_backtester.py         # Auditoría de predicciones pasadas
 ├── nba_games_raw.csv         # Datos crudos descargados de la API
 ├── nba_games_cleaned.csv     # Datos procesados con todas las features
 ├── nba_train_set.csv         # Dataset final para entrenamiento
 ├── nba_model_v1.pkl          # Modelo entrenado (serializado)
 ├── predictions.json          # Picks del día (leídos por el dashboard)
 ├── predictions_history.csv   # Historial de predicciones para auditoría
 └── index.html                # Dashboard web
```

---

## 🛠️ Stack Tecnológico

- **Python 3.10+**
- **[nba_api](https://github.com/swar/nba_api)** — NBA API v3 wrapper
- **pandas & numpy** — Procesamiento de datos
- **scikit-learn** — Random Forest Regressor
- **joblib** — Serialización del modelo
- **HTML / CSS / JS** — Dashboard web sin dependencias externas

---

## 🗺️ Roadmap

- [x] Pipeline completo de datos (fetch → clean → train → predict)
- [x] Dashboard web con predicciones del día
- [x] Auditoría automática de picks anteriores
- [x] Compatibilidad con NBA API v3
- [ ] Integrar momios reales de casas de apuestas (Fase 3)
- [ ] Calcular confianza real basada en varianza del modelo
- [ ] Despliegue automático con GitHub Actions (correr el predictor cada mañana)
- [ ] Notificaciones vía Telegram Bot

---

## ⚠️ Disclaimer

Este proyecto es **exclusivamente con fines educativos y de investigación en Machine Learning**. Las predicciones no garantizan resultados. Apostar con dinero real siempre conlleva riesgo.

---

<div align="center">
  <sub>Hecho con 🏀 y mucho café por Carlos</sub>
</div>