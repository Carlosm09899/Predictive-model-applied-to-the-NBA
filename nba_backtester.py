import pandas as pd
import json
import os
import time
import requests
from datetime import datetime, timedelta
import warnings
import numpy as np

# Silenciamos advertencias
warnings.filterwarnings("ignore")

def get_games_for_date_espn(date_str):
    """Obtiene los resultados de una fecha usando la API de ESPN."""
    # Convertimos YYYY-MM-DD a YYYYMMDD
    date_fmt = date_str.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"

    for attempt in range(3):
        try:
            print(f"📡 Buscando resultados para el {date_str} (Intento {attempt + 1})...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            events = data.get('events', [])
            if not events:
                print(f"ℹ️ No hubo juegos registrados el día {date_str}.")
            return events
        except Exception as e:
            print(f"⚠️ Error el {date_str}: {e}")
            if attempt < 2:
                time.sleep(5)
    return []

def audit_my_bets():
    print("📊 AUDITORÍA DE APUESTAS - EL ORÁCULO DE CARLOS V4.4")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    log_file = "predictions_history.csv"
    results_json = "results.json"

    if not os.path.exists(log_file):
        print("📭 No hay historial en CSV para auditar.")
        return

    df_log = pd.read_csv(log_file)
    
    # Buscamos juegos que no tengan resultado real registrado (NaN o 0)
    pending_mask = df_log['Actual_Home'].isna() | (df_log['Actual_Home'] == 0)
    pending = df_log[pending_mask].copy()

    if pending.empty:
        print("✅ Todo está al día. No hay juegos pendientes de resultados.")
    else:
        print(f"🔍 Encontrados {len(pending)} juegos pendientes en el historial.")
        
        # Diccionario de mapeo para que ESPN y tu CSV se entiendan
        name_map = {
            'GSW': 'GS', 'BKN': 'BKN', 'PHX': 'PHX', 'NYK': 'NY', 
            'SAS': 'SA', 'NOP': 'NO', 'UTA': 'UTA', 'CHA': 'CHA'
        }

        # Agrupamos por fecha para hacer menos llamadas a la API
        pending_dates = pending['Date'].unique()
        all_scores = {} # (Equipo_Mapeado, Fecha) -> Puntos

        for d in pending_dates:
            events = get_games_for_date_espn(d)
            for event in events:
                comp = event['competitions'][0]
                if comp['status']['type']['name'] == 'STATUS_FINAL':
                    for competitor in comp['competitors']:
                        raw_tri = competitor['team']['abbreviation']
                        # Mapeamos el nombre para que coincida con tu CSV
                        mapped_tri = name_map.get(raw_tri, raw_tri)
                        try:
                            pts = int(competitor['score'])
                            all_scores[(mapped_tri, d)] = pts
                        except:
                            continue

        # Actualizamos el DataFrame
        total_updated = 0
        for idx, row in pending.iterrows():
            d_pred = row['Date']
            h_tri = row['Home']
            a_tri = row['Away']

            actual_h = all_scores.get((h_tri, d_pred))
            actual_a = all_scores.get((a_tri, d_pred))

            if actual_h is not None and actual_a is not None:
                # 1. Moneyline
                pred_win = "H" if row['Pred_Home'] > row['Pred_Away'] else "A"
                real_win = "H" if actual_h > actual_a else "A"
                ml_hit = 1 if pred_win == real_win else 0
                
                # 2. Hándicap (Spread)
                pred_spread = row['Pred_Away'] - row['Pred_Home']
                real_spread = actual_a - actual_h
                spread_hit = 1 if abs(pred_spread - real_spread) <= 6.5 else 0
                
                # 3. Total
                pred_total = row.get('Pred_Total', row['Pred_Home'] + row['Pred_Away'])
                real_total = actual_h + actual_a
                total_hit = 1 if abs(pred_total - real_total) <= 8.5 else 0

                # Guardar en el log
                df_log.loc[idx, 'Actual_Home'] = actual_h
                df_log.loc[idx, 'Actual_Away'] = actual_a
                df_log.loc[idx, 'ML_Hit'] = ml_hit
                df_log.loc[idx, 'Spread_Hit'] = spread_hit
                df_log.loc[idx, 'Total_Hit'] = total_hit
                
                total_updated += 1
                print(f"✅ Resultado capturado: {a_tri} {actual_a} @ {h_tri} {actual_h} ({d_pred})")

        # Guardamos el CSV físico
        df_log.to_csv(log_file, index=False)
        print(f"\n📝 CSV actualizado: {total_updated} juegos nuevos auditados.")

    # --- SIEMPRE EXPORTAR RESULTS.JSON ---
    # Limpiamos NaNs para que el Dashboard no truene
    df_web = df_log.copy()
    df_web = df_web.replace({np.nan: None})
    
    # Tomamos los últimos 30 resultados reales para que la tabla esté llena
    recent_results = df_web.dropna(subset=['Actual_Home']).tail(30).to_dict(orient='records')
    
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent_results, f, indent=4, ensure_ascii=False)

    print(f"🚀 Dashboard listo: '{results_json}' actualizado con {len(recent_results)} juegos.")

if __name__ == "__main__":
    audit_my_bets()
