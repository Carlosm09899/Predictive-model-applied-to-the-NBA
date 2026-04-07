import pandas as pd
import numpy as np

def create_matchup_data():
    print("🏗️  Iniciando la construcción del set de entrenamiento 'Cara a Cara'...")
    
    try:
        # Cargamos la base de datos refinada por el data_processing.py
        df = pd.read_csv("nba_games_cleaned.csv")
    except FileNotFoundError:
        print("❌ Error: No se encontró 'nba_games_cleaned.csv'. Corre primero data_processing.py")
        return

    # 1. Identificar Local y Visitante
    # En la NBA API: 'vs.' indica que el equipo es LOCAL, '@' indica que es VISITANTE
    home_df = df[df['MATCHUP'].str.contains('vs.')].copy()
    away_df = df[df['MATCHUP'].str.contains('@')].copy()

    # 2. Definir las columnas que queremos transformar
    # Estas son las "Features" que el modelo usará para aprender
    stats_cols = [
        'PTS_SEASON_AVG', 'PTS_EWMA', 'DEF_SEASON_AVG', 
        'IS_B2B', '3P_PCT_EWMA', 'DEF_EFF_EWMA'
    ]

    # 3. Renombrar columnas para evitar colisiones al unir (Merge)
    home_rename = {col: f'HOME_{col}' for col in stats_cols}
    # Especial para el target de entrenamiento
    home_rename['PTS'] = 'HOME_PTS_ACTUAL' 
    
    away_rename = {col: f'AWAY_{col}' for col in stats_cols}
    # Especial para el target de entrenamiento
    away_rename['PTS'] = 'AWAY_PTS_ACTUAL'

    home_df = home_df.rename(columns=home_rename)
    away_df = away_df.rename(columns=away_rename)

    # 4. Seleccionar columnas necesarias para el entrenamiento
    cols_to_keep_home = ['GAME_ID', 'TOTAL_PTS', 'HOME_PTS_ACTUAL'] + list(home_rename.values())
    cols_to_keep_away = ['GAME_ID', 'AWAY_PTS_ACTUAL'] + list(away_rename.values())

    # 5. EL MATCHUP: Unir local y visitante en una sola fila por GAME_ID
    print("🤝 Uniendo estadísticas de Local y Visitante...")
    final_df = pd.merge(
        home_df[cols_to_keep_home], 
        away_df[cols_to_keep_away], 
        on='GAME_ID'
    )

    # Limpieza final: Eliminar columnas duplicadas si las hay
    final_df = final_df.loc[:, ~final_df.columns.duplicated()]

    # 6. Guardar el archivo maestro para el Trainer V3
    final_df.to_csv("nba_train_set.csv", index=False)
    
    print("-" * 35)
    print(f"✅ ¡Set de entrenamiento listo para XGBoost!")
    print(f"📦 Total de enfrentamientos: {len(final_df)}")
    print(f"📂 Archivo generado: 'nba_train_set.csv'")
    print("-" * 35)

if __name__ == "__main__":
    create_matchup_data()