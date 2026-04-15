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
    """Obtiene los resultados detallados (incluyendo cuartos) de ESPN."""
    date_fmt = date_str.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"

    for attempt in range(3):
        try:
            print(f"📡 Buscando detalles del {date_str} (Intento {attempt + 1})...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('events', [])
        except Exception as e:
            print(f"⚠️ Error el {date_str}: {e}")
            if attempt < 2: time.sleep(5)
    return []

def audit_my_bets():
    print("📊 AUDITORÍA MAESTRA - EL ORÁCULO DE CARLOS V5.5")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    log_file = "predictions_history.csv"
    results_json = "results.json"

    if not os.path.exists(log_file):
        print("📭 No hay historial en CSV para auditar.")
        return

    df_log = pd.read_csv(log_file)
    
    # Buscamos juegos pendientes de resultado final
    pending_mask = df_log['Actual_Home'].isna() | (df_log['Actual_Home'] == 0)
    pending = df_log[pending_mask].copy()

    if pending.empty:
        print("✅ Todo está al día. Refrescando Dashboard...")
    else:
        print(f"🔍 Auditando {len(pending)} juegos pendientes por periodos...")
        
        name_map = {'GSW': 'GS', 'BKN': 'BKN', 'PHX': 'PHX', 'NYK': 'NY', 'SAS': 'SA', 'NOP': 'NO', 'UTA': 'UTA', 'CHA': 'CHA'}
        pending_dates = pending['Date'].unique()
        
        # Diccionario para guardar todo el desglose: (Equipo, Fecha) -> {final, Q1, Q2, Q3, Q4}
        all_stats = {} 

        for d in pending_dates:
            events = get_games_for_date_espn(d)
            for event in events:
                comp = event['competitions'][0]
                if comp['status']['type']['name'] == 'STATUS_FINAL':
                    for competitor in comp['competitors']:
                        raw_tri = competitor['team']['abbreviation']
                        mapped_tri = name_map.get(raw_tri, raw_tri)
                        
                        # Extraemos marcadores por cuarto (Linescores)
                        ls = competitor.get('linescores', [])
                        q_pts = [int(q.get('value', 0)) for q in ls]
                        
                        # Aseguramos que tenemos al menos 4 cuartos
                        while len(q_pts) < 4: q_pts.append(0)
                        
                        all_stats[(mapped_tri, d)] = {
                            'final': int(competitor.get('score', 0)),
                            'q1': q_pts[0], 'q2': q_pts[1], 'q3': q_pts[2], 'q4': q_pts[3]
                        }

        # Actualizamos el DataFrame con la lógica de "Hits"
        for idx, row in pending.iterrows():
            d, h_tri, a_tri = row['Date'], row['Home'], row['Away']
            h_real = all_stats.get((h_tri, d))
            a_real = all_stats.get((a_tri, d))

            if h_real and a_real:
                # 1. Auditoría de Mercados Finales
                df_log.loc[idx, 'Actual_Home'] = h_real['final']
                df_log.loc[idx, 'Actual_Away'] = a_real['final']
                
                # Moneyline Hit
                real_win = "H" if h_real['final'] > a_real['final'] else "A"
                pred_win = "H" if row['Pred_Home'] > row['Pred_Away'] else "A"
                df_log.loc[idx, 'ML_Hit'] = 1 if real_win == pred_win else 0

                # 2. Auditoría de Periodos (Comparando vs quien dijimos que ganaba cada uno)
                # Nota: El CSV debe tener columnas 'Pred_Q1_Winner', etc. o inferimos del marcador predicho
                
                # Función auxiliar para checar el hit del periodo
                def check_p(real_h_pts, real_a_pts, pred_winner_name):
                    real_winner = h_tri if real_h_pts > real_a_pts else a_tri
                    # Si hubo empate en el cuarto, lo damos por perdido para ser conservadores
                    if real_h_pts == real_a_pts: return 0
                    return 1 if real_winner == pred_winner_name else 0

                # Estos nombres de columnas deben coincidir con lo que guarda tu Predictor
                df_log.loc[idx, 'Q1_Hit'] = check_p(h_real['q1'], a_real['q1'], row.get('Pred_Q1_Winner', 'N/A'))
                df_log.loc[idx, 'Q2_Hit'] = check_p(h_real['q2'], a_real['q2'], row.get('Pred_Q2_Winner', 'N/A'))
                df_log.loc[idx, 'Q3_Hit'] = check_p(h_real['q3'], a_real['q3'], row.get('Pred_Q3_Winner', 'N/A'))
                df_log.loc[idx, 'Q4_Hit'] = check_p(h_real['q4'], a_real['q4'], row.get('Pred_Q4_Winner', 'N/A'))
                
                # Mitades
                df_log.loc[idx, '1H_Hit'] = check_p(h_real['q1']+h_real['q2'], a_real['q1']+a_real['q2'], row.get('Pred_1H_Winner', 'N/A'))
                
                print(f"✅ Auditado Completo: {a_tri} @ {h_tri} ({d})")

        df_log.to_csv(log_file, index=False)

    # EXPORTACIÓN FINAL PARA EL DASHBOARD
    df_web = df_log.copy().replace({np.nan: None})
    recent_results = df_web.dropna(subset=['Actual_Home']).tail(25).to_dict(orient='records')
    
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent_results, f, indent=4, ensure_ascii=False)

    print(f"🚀 Dashboard actualizado con {len(recent_results)} auditorías detalladas.")

if __name__ == "__main__":
    audit_my_bets()