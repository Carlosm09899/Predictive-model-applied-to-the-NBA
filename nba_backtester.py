import pandas as pd
import json
import os
import time
from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime
import warnings

HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.nba.com/'
}

# Silenciamos advertencias para una terminal limpia
warnings.filterwarnings("ignore")

def audit_my_bets():
    print("📊 AUDITORÍA DE APUESTAS - EL ORÁCULO DE CARLOS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    log_file = "predictions_history.csv"
    results_json = "results.json"
    
    # 🛡️ SEGURO DE VIDA: Si el archivo results.json no existe, lo creamos vacío
    # Esto evita que GitHub Actions falle al intentar hacer 'git add results.json'
    if not os.path.exists(results_json):
        with open(results_json, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(log_file):
        print("📭 No hay historial en CSV para auditar.")
        return

    df_log = pd.read_csv(log_file)
    # Buscamos solo los que no tienen resultado real aún
    pending = df_log[df_log['Actual_Home'].isna()].copy()
    
    if pending.empty:
        print("✅ Todo está al día. No hay juegos pendientes de ayer.")
        return

    print(f"🔍 Buscando resultados reales para {len(pending)} juegos...")

    actual_games = None
    # REINTENTOS: Lo intentaremos hasta 3 veces si la API de la NBA está lenta
    for attempt in range(3):
        try:
            print(f"📡 Conectando con la NBA (Intento {attempt + 1})...")
            game_finder = leaguegamefinder.LeagueGameFinder(
                season_nullable='2025-26', 
                timeout=60,
                headers=HEADERS # <--- Agrega esto aquí también
            )
            actual_games = game_finder.get_data_frames()[0]
            break
        except Exception as e:
            print(f"⚠️ Error: {e}. Reintentando...")
            time.sleep(10)

    if actual_games is None:
        print("❌ La API de la NBA no respondió después de 3 intentos.")
        print("⏳ Se intentará de nuevo en la próxima ejecución automática.")
        return

    # Estandarizar fechas para que coincidan con tu historial
    actual_games['GAME_DATE'] = pd.to_datetime(actual_games['GAME_DATE']).dt.strftime('%Y-%m-%d')
    
    hits = 0
    total_audited = 0

    for idx, row in pending.iterrows():
        # Buscamos el equipo local en la fecha del juego
        match_h = actual_games[
            (actual_games['TEAM_ABBREVIATION'] == row['Home']) & 
            (actual_games['GAME_DATE'] == row['Date'])
        ]

        if not match_h.empty:
            game_id = match_h.iloc[0]['GAME_ID']
            actual_h_pts = match_h.iloc[0]['PTS']
            
            # Buscamos al rival usando el mismo ID de juego
            match_a = actual_games[
                (actual_games['GAME_ID'] == game_id) & 
                (actual_games['TEAM_ABBREVIATION'] == row['Away'])
            ]
            
            if not match_a.empty:
                actual_a_pts = match_a.iloc[0]['PTS']
                
                # EVALUACIÓN DE GANADOR (Moneyline)
                pred_win = row['Home'] if row['Pred_Home'] > row['Pred_Away'] else row['Away']
                real_win = row['Home'] if actual_h_pts > actual_a_pts else row['Away']
                
                if pred_win == real_win: 
                    hits += 1
                
                # Actualizar el registro en el CSV
                df_log.loc[idx, 'Actual_Home'] = actual_h_pts
                df_log.loc[idx, 'Actual_Away'] = actual_a_pts
                total_audited += 1
                status = "✅ HIT" if pred_win == real_win else "❌ MISS"
                print(f"{status}: {row['Away']} {actual_a_pts} @ {row['Home']} {actual_h_pts}")

    # Guardar el CSV con los nuevos datos reales
    df_log.to_csv(log_file, index=False)

    # 🚀 EXPORTAR PARA EL DASHBOARD WEB
    # Tomamos los últimos 15 resultados para la tabla de la página
    recent_results = df_log.dropna(subset=['Actual_Home']).tail(15).to_dict(orient='records')
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent_results, f, indent=4, ensure_ascii=False)

    if total_audited > 0:
        print(f"\n🎯 Sesión terminada. Efectividad: {(hits/total_audited)*100:.1f}%")
    else:
        print("\n⏳ Todavía no hay resultados finales oficiales para los juegos de hoy.")

if __name__ == "__main__":
    audit_my_bets()
