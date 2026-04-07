import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import joblib

# 1. Cargar datos
df = pd.read_csv("nba_games_cleaned.csv")

# ⚡ FILTRO ERA MODERNA: Solo usar datos de 2022 en adelante.
# El problema es que datos de 2015-2021 incluyen a los Spurs de Popovich, Celtics y
# Raptors defensivos que jugaban partidos de ~175 pts totales. El modelo aprendía que
# DEF_EFF_EWMA bajo (buena defensa) = juego de 135 pts, que ya no aplica en la NBA 2022+.
df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
df = df[df['GAME_DATE'] >= '2022-10-01']
print(f"Datos filtrados a era moderna (2022+): {len(df)} registros")

# 2. El "Truco del Matchup" (CORREGIDO)
def create_matchups(df):
    df['IS_HOME'] = df['MATCHUP'].str.contains('vs.').astype(int)
    
    home_games = df[df['IS_HOME'] == 1].copy()
    away_games = df[df['IS_HOME'] == 0].copy()
    
    # --- AQUÍ ESTABA EL DETALLE ---
    # Tenemos que decirle explícitamente qué columnas nuevas queremos jalar y cómo renombrarlas
    home_cols = {
        'TEAM_NAME': 'HOME_TEAM', 'PTS': 'HOME_PTS', 
        'PTS_SEASON_AVG': 'HOME_SEASON_AVG', 'PTS_EWMA': 'HOME_EWMA',
        'DEF_SEASON_AVG': 'HOME_DEF_AVG', 'IS_B2B': 'HOME_B2B',
        '3P_PCT_EWMA': 'HOME_3P_PCT_EWMA', # <-- Nueva
        'DEF_EFF_EWMA': 'HOME_DEF_EFF_EWMA' # <-- Nueva
    }
    
    away_cols = {
        'TEAM_NAME': 'AWAY_TEAM', 'PTS': 'AWAY_PTS', 
        'PTS_SEASON_AVG': 'AWAY_SEASON_AVG', 'PTS_EWMA': 'AWAY_EWMA',
        'DEF_SEASON_AVG': 'AWAY_DEF_AVG', 'IS_B2B': 'AWAY_B2B',
        '3P_PCT_EWMA': 'AWAY_3P_PCT_EWMA', # <-- Nueva
        'DEF_EFF_EWMA': 'AWAY_DEF_EFF_EWMA' # <-- Nueva
    }
    
    home_games = home_games.rename(columns=home_cols)
    away_games = away_games.rename(columns=away_cols)
    
    # Columnas que vamos a mantener en el merge
    keys_home = ['GAME_ID', 'GAME_DATE'] + list(home_cols.values())
    keys_away = ['GAME_ID'] + list(away_cols.values())
    
    matchups = pd.merge(home_games[keys_home], away_games[keys_away], on='GAME_ID')
    
    matchups['TOTAL_PTS'] = matchups['HOME_PTS'] + matchups['AWAY_PTS']

    # === FEATURES DE INTERACCIÓN OFENSA-DEFENSA ===
    # El Random Forest no modela interacciones automáticamente.
    # Le damos la info pre-calculada: cuánto debería anotar cada equipo
    # considerando la DEFENSA del rival específico.
    # Fórmula: avg entre lo que el atacante suele hacer y lo que el defensor suele PERMITIR.
    matchups['EXPECTED_HOME_PTS'] = (matchups['HOME_EWMA'] + matchups['AWAY_DEF_EFF_EWMA']) / 2
    matchups['EXPECTED_AWAY_PTS'] = (matchups['AWAY_EWMA'] + matchups['HOME_DEF_EFF_EWMA']) / 2
    matchups['EXPECTED_TOTAL']    = matchups['EXPECTED_HOME_PTS'] + matchups['EXPECTED_AWAY_PTS']

    return matchups

print("Preparando matchups con variables de triples y defensa...")
data = create_matchups(df)

# 3. Definir las features (ahora sí están en el DataFrame 'data')
features = [
    # Contexto ofensivo de cada equipo
    'HOME_SEASON_AVG', 'HOME_EWMA', 'HOME_B2B', 'HOME_3P_PCT_EWMA',
    'AWAY_SEASON_AVG', 'AWAY_EWMA', 'AWAY_B2B', 'AWAY_3P_PCT_EWMA',
    # Interacción ofensa-defensa (la defensa queda implícita aquí)
    # No usamos HOME_DEF_AVG ni DEF_EFF_EWMA directamente porque sus valores
    # absolutos codígos eras pasadas (ej: Spurs 2016 = 103 pts permitidos = juego bajo).
    # EXPECTED_TOTAL ya captura la relación ofensa-rivale de forma relativa.
    'EXPECTED_HOME_PTS', 'EXPECTED_AWAY_PTS', 'EXPECTED_TOTAL',
]

X = data[features]
y = data['TOTAL_PTS']

# 4. Entrenamiento
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Entrenando al 'Cerebro' mejorado...")
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Evaluación
predictions = model.predict(X_test)
error = mean_absolute_error(y_test, predictions)

print("-" * 30)
print(f"Modelo Entrenado. Nuevo Error promedio: {error:.2f} puntos.")
joblib.dump(model, 'nba_model_v1.pkl')
print("¡Modelo guardado con éxito!")