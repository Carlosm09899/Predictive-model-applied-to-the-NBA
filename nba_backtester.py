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
    """Obtiene los resultados de una fecha usando la API de ESPN (Más estable)."""
    # El formato esperado de date_str es YYYY-MM-DD
    date_fmt = date_str.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"

    for attempt in range(3):
        try:
            print(f"📡 Conectando con ESPN para resultados (Intento {attempt + 1})...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('events', [])
        except Exception as e:
            print(f"⚠️ Error en intento {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(10)
    return None

def audit_my_bets():
    print("📊 AUDITORÍA DE APUESTAS - EL ORÁCULO DE CARLOS V4.3")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    log_file = "predictions_history.csv"
    results_json = "results.json"

    # Verificamos si existe el historial
    if not os.path.exists(log_file):
        print("📭 No hay historial en CSV para auditar.")
        return

    # Cargamos el log maestro
    df_log = pd.read_csv(log_file)
    
    # Buscamos juegos que no tengan resultado real registrado
    pending = df_log[df_log['Actual_Home'].isna()].copy()

    if not pending.empty:
        print(f"🔍 Buscando resultados reales para {len(pending)} juegos pendientes...")
        pending_dates = pending['Date'].unique()
        scores = {} # Diccionario para búsqueda rápida: (Equipo, Fecha) -> Puntos

        for d in pending_dates:
            events = get_games_for_date_espn(d)
            if not events:
                continue

            for event in events:
                comp = event['competitions'][0]
                status = comp['status']['type']['name']
                
                # Solo auditamos juegos que ya terminaron oficialmente
                if status == 'STATUS_FINAL':
                    for competitor in comp['competitors']:
                        tri = competitor['team']['abbreviation']
                        try:
                            pts = int(competitor['score'])
                            scores[(tri, d)] = pts
                        except:
                            continue

        total_audited = 0
        for idx, row in pending.iterrows():
            d_pred = row['Date']
            h_tri = row['Home']
            a_tri = row['Away']

            actual_h = scores.get((h_tri, d_pred))
            actual_a = scores.get((a_tri, d_pred))

            if actual_h is not None and actual_a is not None:
                # 1. Moneyline Hit
                pred_win = "H" if row['Pred_Home'] > row['Pred_Away'] else "A"
                real_win = "H" if actual_h > actual_a else "A"
                ml_hit = 1 if pred_win == real_win else 0
                
                # 2. Hándicap (Spread) Hit
                # Diferencia entre nuestra predicción de margen y la realidad
                pred_spread = row['Pred_Away'] - row['Pred_Home']
                real_spread = actual_a - actual_h
                spread_hit = 1 if abs(pred_spread - real_spread) <= 6.5 else 0
                
                # 3. Total (O/U) Hit
                pred_total = row['Pred_Total']
                real_total = actual_h + actual_a
                total_hit = 1 if abs(pred_total - real_total) <= 8.5 else 0

                # Actualizamos las columnas en el DataFrame
                df_log.loc[idx, 'Actual_Home'] = actual_h
                df_log.loc[idx, 'Actual_Away'] = actual_a
                df_log.loc[idx, 'ML_Hit'] = ml_hit
                df_log.loc[idx, 'Spread_Hit'] = spread_hit
                df_log.loc[idx, 'Total_Hit'] = total_hit
                
                total_audited += 1
                print(f"✅ Auditado: {a_tri} @ {h_tri} | Real: {actual_a}-{actual_h}")

        # Guardamos el CSV actualizado (mantenemos NaNs aquí para pandas)
        df_log.to_csv(log_file, index=False)
        print(f"\n📝 CSV actualizado con {total_audited} resultados nuevos.")
    else:
        print("✅ No hay auditorías pendientes. Refrescando archivo web...")

    # --- LIMPIEZA DE NaNs PARA EL DASHBOARD ---
    # Esto es crítico para que el JSON.parse() en React no truene
    df_web = df_log.copy()
    df_web = df_web.replace({np.nan: None}) # Cambia NaNs por nulls reales de JSON
    
    # Tomamos los últimos 20 juegos con resultado real para la tabla de auditoría
    recent_results = df_web.dropna(subset=['Actual_Home']).tail(20).to_dict(orient='records')
    
    # Exportar a JSON (Sin permitir NaNs)
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent_results, f, indent=4, ensure_ascii=False)

    print(f"🚀 Dashboard actualizado: '{results_json}' listo con {len(recent_results)} juegos.")

if __name__ == "__main__":
    audit_my_bets()
