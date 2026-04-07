import pandas as pd
import json
import os
import time
from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime
import warnings

# Silenciamos advertencias
warnings.filterwarnings("ignore")

def audit_my_bets():
    print("📊 AUDITORÍA DE APUESTAS - EL ORÁCULO DE CARLOS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    log_file = "predictions_history.csv"
    results_json = "results.json"
    
    if not os.path.exists(log_file):
        print("📭 No hay historial para auditar.")
        return

    df_log = pd.read_csv(log_file)
    pending = df_log[df_log['Actual_Home'].isna()].copy()
    
    if pending.empty:
        print("✅ Todo está al día.")
        return

    print(f"🔍 Buscando resultados para {len(pending)} juegos...")

    actual_games = None
    # REINTENTOS: Lo intentaremos hasta 3 veces si la API falla
    for attempt in range(3):
        try:
            print(f"📡 Conectando con la NBA (Intento {attempt + 1})...")
            # Aumentamos el timeout a 60 segundos para ser más pacientes
            game_finder = leaguegamefinder.LeagueGameFinder(
                season_nullable='2025-26', 
                timeout=60 
            )
            actual_games = game_finder.get_data_frames()[0]
            break # Si funciona, salimos del bucle de reintentos
        except Exception as e:
            print(f"⚠️ Intento {attempt + 1} falló por timeout. Reintentando en 5 seg...")
            time.sleep(5)

    if actual_games is None:
        print("❌ La API de la NBA no responde. Lo intentaremos en la próxima ejecución automática.")
        return

    # Limpiar fechas
    actual_games['GAME_DATE'] = pd.to_datetime(actual_games['GAME_DATE']).dt.strftime('%Y-%m-%d')
    
    hits = 0
    total_audited = 0

    for idx, row in pending.iterrows():
        match_h = actual_games[
            (actual_games['TEAM_ABBREVIATION'] == row['Home']) & 
            (actual_games['GAME_DATE'] == row['Date'])
        ]

        if not match_h.empty:
            game_id = match_h.iloc[0]['GAME_ID']
            actual_h_pts = match_h.iloc[0]['PTS']
            
            match_a = actual_games[
                (actual_games['GAME_ID'] == game_id) & 
                (actual_games['TEAM_ABBREVIATION'] == row['Away'])
            ]
            
            if not match_a.empty:
                actual_a_pts = match_a.iloc[0]['PTS']
                
                # Evaluar Ganador
                pred_win = row['Home'] if row['Pred_Home'] > row['Pred_Away'] else row['Away']
                real_win = row['Home'] if actual_h_pts > actual_a_pts else row['Away']
                
                if pred_win == real_win: hits += 1
                
                # Actualizar DataFrame
                df_log.loc[idx, 'Actual_Home'] = actual_h_pts
                df_log.loc[idx, 'Actual_Away'] = actual_a_pts
                total_audited += 1
                print(f"✅ Auditado: {row['Away']} @ {row['Home']} -> {'HIT' if pred_win == real_win else 'MISS'}")

    # Guardar CSV actualizado
    df_log.to_csv(log_file, index=False)

    # 🚀 EXPORTAR PARA LA WEB (JSON)
    # Tomamos los últimos 10 resultados reales para mostrar en el Dashboard
    recent_results = df_log.dropna(subset=['Actual_Home']).tail(10).to_dict(orient='records')
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent_results, f, indent=4, ensure_ascii=False)

    if total_audited > 0:
        print(f"\n🎯 Auditoría finalizada. Efectividad esta sesión: {(hits/total_audited)*100:.1f}%")
    else:
        print("\n⏳ Aún no hay resultados finales para los juegos pendientes.")

if __name__ == "__main__":
    audit_my_bets()