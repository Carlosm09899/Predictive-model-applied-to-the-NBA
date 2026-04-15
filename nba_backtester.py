import pandas as pd
import json
import os
import time
import requests
from datetime import datetime, timedelta
import warnings
import numpy as np

# Silenciamos advertencias para una terminal limpia
warnings.filterwarnings("ignore")

def get_games_for_date_espn(date_str):
    """Obtiene los resultados detallados de ESPN."""
    date_fmt = date_str.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"

    for attempt in range(3):
        try:
            print(f"📡 Consultando ESPN: {date_str}...")
            resp = requests.get(url, timeout=25)
            resp.raise_for_status()
            return resp.json().get('events', [])
        except Exception as e:
            if attempt < 2: time.sleep(5)
    return []

def audit_my_bets():
    print("📊 AUDITORÍA MAESTRA - EL ORÁCULO DE CARLOS V5.6")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    log_file = "predictions_history.csv"
    results_json = "results.json"

    if not os.path.exists(log_file):
        print("📭 No existe el historial CSV.")
        return

    df_log = pd.read_csv(log_file)
    
    # 1. EVITAR EL BUCLE DEL PASADO
    # Solo intentaremos auditar juegos de los últimos 5 días para no trabarnos con errores viejos
    hace_5_dias = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    # Buscamos juegos pendientes que sean RECIENTES
    pending_mask = (df_log['Actual_Home'].isna() | (df_log['Actual_Home'] == 0)) & (df_log['Date'] >= hace_5_dias)
    pending = df_log[pending_mask].copy()

    if pending.empty:
        print("✅ No hay juegos recientes pendientes. Refrescando Dashboard...")
    else:
        print(f"🔍 Auditando {len(pending)} juegos de fechas recientes...")
        
        name_map = {
            'GSW': 'GS', 'BKN': 'BKN', 'PHX': 'PHX', 'NYK': 'NY', 'SAS': 'SA', 
            'NOP': 'NO', 'UTA': 'UTA', 'CHA': 'CHA', 'OKC': 'OKC', 'LAL': 'LAL'
        }
        
        pending_dates = pending['Date'].unique()
        all_stats = {} 

        for d in pending_dates:
            events = get_games_for_date_espn(d)
            for event in events:
                comp = event['competitions'][0]
                # Solo procesamos juegos terminados
                if comp['status']['type']['name'] in ['STATUS_FINAL', 'STATUS_FULL_TIME']:
                    for competitor in comp['competitors']:
                        raw_tri = competitor['team']['abbreviation']
                        mapped_tri = name_map.get(raw_tri, raw_tri)
                        
                        ls = competitor.get('linescores', [])
                        q_pts = [int(q.get('value', 0)) for q in ls]
                        while len(q_pts) < 4: q_pts.append(0)
                        
                        all_stats[(mapped_tri, d)] = {
                            'final': int(competitor.get('score', 0)),
                            'q1': q_pts[0], 'q2': q_pts[1], 'q3': q_pts[2], 'q4': q_pts[3]
                        }

        # Actualización de Hits
        updated_count = 0
        for idx, row in pending.iterrows():
            d, h_tri, a_tri = row['Date'], row['Home'], row['Away']
            h_real = all_stats.get((h_tri, d))
            a_real = all_stats.get((a_tri, d))

            if h_real and a_real:
                df_log.loc[idx, 'Actual_Home'] = h_real['final']
                df_log.loc[idx, 'Actual_Away'] = a_real['final']
                
                # ML Hit
                real_win = "H" if h_real['final'] > a_real['final'] else "A"
                pred_win = "H" if row['Pred_Home'] > row['Pred_Away'] else "A"
                df_log.loc[idx, 'ML_Hit'] = 1 if real_win == pred_win else 0

                # Auditoría de Periodos
                def get_h(h_p, a_p, period_key):
                    pred_winner = row.get(f'Pred_{period_key}_Winner')
                    if not pred_winner: return 0
                    real_winner = h_tri if h_p > a_p else a_tri
                    return 1 if real_winner == pred_winner else 0

                df_log.loc[idx, 'Q1_Hit'] = get_h(h_real['q1'], a_real['q1'], 'Q1')
                df_log.loc[idx, 'Q2_Hit'] = get_h(h_real['q2'], a_real['q2'], 'Q2')
                df_log.loc[idx, '1H_Hit'] = get_h(h_real['q1']+h_real['q2'], a_real['q1']+a_real['q2'], '1H')
                
                updated_count += 1
                print(f"✅ Auditado: {a_tri} @ {h_tri} ({d})")

        df_log.to_csv(log_file, index=False)
        print(f"📝 Se actualizaron {updated_count} resultados nuevos.")

    # --- EXPORTACIÓN ULTRA-LIMPIA ---
    # Convertimos todo lo que sea NaN a None (null en JSON) para no romper el HTML
    df_web = df_log.replace({np.nan: None})
    
    # Tomamos los últimos 25 juegos que SI tengan resultado real
    history_to_show = df_web[df_web['Actual_Home'].notna()].tail(25).to_dict(orient='records')
    
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(history_to_show, f, indent=4, ensure_ascii=False)

    print(f"🚀 Dashboard actualizado con {len(history_to_show)} juegos.")

if __name__ == "__main__":
    audit_my_bets()