import pandas as pd
import numpy as np

def process_data():
    print("🚀 Iniciando la refinería de datos...")
    
    # 1. Cargar datos crudos
    try:
        df = pd.read_csv("nba_games_raw.csv")
    except FileNotFoundError:
        print("❌ Error: No se encontró 'nba_games_raw.csv'.")
        return

    # Limpieza inicial
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(by=['GAME_DATE'])

    # ==========================================
    # 🔍 PASO CRUCIAL: CREAR OPP_PTS (Puntos del Rival)
    # ==========================================
    print("⚔️ Cruzando datos para encontrar los puntos del rival...")
    
    # Cada juego tiene 2 filas (una por equipo). 
    # Agrupamos por GAME_ID y volteamos los puntos para que el equipo A vea los de B.
    df = df.sort_values(['GAME_ID', 'TEAM_ID'])
    df['OPP_PTS'] = df.groupby('GAME_ID')['PTS'].transform(lambda x: x.iloc[::-1].values if len(x)==2 else np.nan)
    
    # Quitamos juegos incompletos (donde no se encontró al rival)
    df = df.dropna(subset=['OPP_PTS'])

    # 3. Ingeniería de Características (Features)
    print("📊 Calculando promedios y EWMA...")
    
    df = df.sort_values(['TEAM_ID', 'GAME_DATE'])
    
    # --- PROMEDIOS DE TEMPORADA ---
    # Shift() es vital para no usar datos del juego que queremos predecir
    df['PTS_SEASON_AVG'] = df.groupby(['TEAM_ID', 'SEASON_ID'])['PTS'].transform(lambda x: x.shift().expanding().mean())
    df['DEF_SEASON_AVG'] = df.groupby(['TEAM_ID', 'SEASON_ID'])['OPP_PTS'].transform(lambda x: x.shift().expanding().mean())

    # --- EWMA (Rachas recientes) ---
    df['PTS_EWMA'] = df.groupby(['TEAM_ID', 'SEASON_ID'])['PTS'].transform(lambda x: x.shift().ewm(span=10).mean())
    df['DEF_EWMA'] = df.groupby(['TEAM_ID', 'SEASON_ID'])['OPP_PTS'].transform(lambda x: x.shift().ewm(span=10).mean())
    
    df['3P_PCT_EWMA'] = df.groupby(['TEAM_ID', 'SEASON_ID'])['FG3_PCT'].transform(lambda x: x.shift().ewm(span=10).mean())
    df['DEF_EFF_EWMA'] = df.groupby(['TEAM_ID', 'SEASON_ID'])['OPP_PTS'].transform(lambda x: x.shift().ewm(span=10).mean())

    # --- DESCANSO Y B2B ---
    df['DAYS_REST'] = df.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
    df['IS_B2B'] = np.where(df['DAYS_REST'] <= 1, 1, 0)

    # --- EL TARGET (Lo que queremos predecir) ---
    df['TOTAL_PTS'] = df['PTS'] + df['OPP_PTS']
    
    # 4. Limpieza final
    df_cleaned = df.dropna(subset=['PTS_SEASON_AVG', 'PTS_EWMA', 'TOTAL_PTS'])

    # 5. Guardar
    df_cleaned.to_csv("nba_games_cleaned.csv", index=False)
    
    print("-" * 30)
    print(f"✅ Refinería terminada.")
    print(f"🏀 Promedio de TOTAL_PTS: {df_cleaned['TOTAL_PTS'].mean():.2f}")
    print("-" * 30)

if __name__ == "__main__":
    process_data()