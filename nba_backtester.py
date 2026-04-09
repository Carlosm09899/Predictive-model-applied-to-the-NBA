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
    """Obtiene los resultados de una fecha usando la API de ESPN."""
    date_fmt = date_str.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"

    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('events', [])
        except Exception as e:
            if attempt < 2: time.sleep(10)
    return None

def audit_my_bets():
    print("📊 AUDITORÍA PRO: TRIPLE INDICADOR (ML, SPREAD, TOTAL)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    log_file = "predictions_history.csv"
    results_json = "results.json"

    if not os.path.exists(results_json):
        with open(results_json, 'w', encoding='utf-8') as f:
            json.dump([], f)

    if not os.path.exists(log_file):
        print("📭 No hay historial para auditar.")
        return

    df_log = pd.read_csv(log_file)
    pending = df_log[df_log['Actual_Home'].isna()].copy()

    if pending.empty:
        print("✅ Todo está al día.")
        return

    pending_dates = pending['Date'].unique()
    scores = {}

    for d in pending_dates:
        events = get_games_for_date_espn(d)
        if not events: continue
        
        for event in events:
            comp = event['competitions'][0]
            if comp['status']['type']['name'] != 'STATUS_FINAL': continue

            # Extraer equipos y scores
            for competitor in comp['competitors']:
                tri = competitor['team']['abbreviation']
                pts = int(competitor['score'])
                scores[(tri, d)] = pts

    total_audited = 0
    for idx, row in pending.iterrows():
        h_pts = scores.get((row['Home'], row['Date']))
        a_pts = scores.get((row['Away'], row['Date']))

        if h_pts is not None and a_pts is not None:
            # 1. Moneyline
            ml_hit = (row['Pred_Home'] > row['Pred_Away']) == (h_pts > a_pts)
            
            # 2. Hándicap (Spread) - Diferencia entre el margen real y el predicho
            real_margin = h_pts - a_pts
            pred_margin = row['Pred_Home'] - row['Pred_Away']
            spread_error = abs(real_margin - pred_margin)
            spread_hit = spread_error <= 6.5 # HIT si fallamos por menos de 6.5 pts
            
            # 3. Total (O/U)
            real_total = h_pts + a_pts
            total_error = abs(real_total - row['Pred_Total'])
            total_hit = total_error <= 8.5 # HIT si fallamos por menos de 8.5 pts

            # Guardar en DataFrame
            df_log.loc[idx, 'Actual_Home'] = h_pts
            df_log.loc[idx, 'Actual_Away'] = a_pts
            df_log.loc[idx, 'ML_Hit'] = int(ml_hit)
            df_log.loc[idx, 'Spread_Hit'] = int(spread_hit)
            df_log.loc[idx, 'Total_Hit'] = int(total_hit)
            
            total_audited += 1
            print(f"✅ Auditado: {row['Away']} @ {row['Home']} | ML: {'OK' if ml_hit else 'X'} | S: {spread_error:.1f} | T: {total_error:.1f}")

    df_log.to_csv(log_file, index=False)

    # Exportar para la web con el nuevo desglose
    recent = df_log.dropna(subset=['Actual_Home']).tail(15).to_dict(orient='records')
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent, f, indent=4, ensure_ascii=False)

    print(f"\n🎯 Sesión terminada. {total_audited} juegos procesados.")

if __name__ == "__main__":
    audit_my_bets()