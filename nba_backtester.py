import pandas as pd
import json
import os
import time
import requests
from datetime import datetime, timedelta
import warnings

# Silenciamos advertencias para una terminal limpia
warnings.filterwarnings("ignore")

def get_games_for_date_espn(date_str):
    date_fmt = date_str.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json().get('events', [])
        except:
            if attempt < 2: time.sleep(10)
    return None

def audit_my_bets():
    print("📊 AUDITORÍA DE APUESTAS - V4.3")
    log_file = "predictions_history.csv"
    results_json = "results.json"

    if not os.path.exists(log_file):
        print("📭 No hay historial para auditar.")
        return

    df_log = pd.read_csv(log_file)
    
    # Intentar auditar juegos pendientes
    pending = df_log[df_log['Actual_Home'].isna()].copy()
    
    if not pending.empty:
        print(f"🔍 Auditando {len(pending)} juegos...")
        pending_dates = pending['Date'].unique()
        scores = {}

        for d in pending_dates:
            events = get_games_for_date_espn(d)
            if not events: continue
            for event in events:
                comp = event['competitions'][0]
                if comp['status']['type']['name'] == 'STATUS_FINAL':
                    for competitor in comp['competitors']:
                        tri = competitor['team']['abbreviation']
                        scores[(tri, d)] = int(competitor['score'])

        for idx, row in pending.iterrows():
            h_pts = scores.get((row['Home'], row['Date']))
            a_pts = scores.get((row['Away'], row['Date']))
            if h_pts is not None and a_pts is not None:
                df_log.loc[idx, 'Actual_Home'] = h_pts
                df_log.loc[idx, 'Actual_Away'] = a_pts
                print(f"✅ Juego Auditado: {row['Away']} @ {row['Home']}")
        
        # Guardar cambios en el CSV
        df_log.to_csv(log_file, index=False)
    else:
        print("✅ Todo está al día en el CSV.")

    # 🔥 LA CLAVE: Exportamos resultados SIEMPRE, haya juegos nuevos o no
    print("🚀 Actualizando results.json para el Dashboard...")
    # Limpiamos los que no tienen score real y tomamos los últimos 20
    history_to_show = df_log.dropna(subset=['Actual_Home']).tail(20).to_dict(orient='records')
    
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(history_to_show, f, indent=4, ensure_ascii=False)
    
    print(f"🎯 Auditoría finalizada. Mostrando {len(history_to_show)} resultados en la web.")

if __name__ == "__main__":
    audit_my_bets()