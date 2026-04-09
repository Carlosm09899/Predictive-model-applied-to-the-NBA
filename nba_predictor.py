import pandas as pd
import joblib
import numpy as np
import json
import os
import requests
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# 1. CARGA DE INTELIGENCIA Y MAPEO
try:
    model = joblib.load('nba_model_v1.pkl')
    df_history = pd.read_csv("nba_games_cleaned.csv")
    df_history['TEAM_ABBREVIATION'] = df_history['TEAM_ABBREVIATION'].str.strip()
    team_map = df_history.drop_duplicates('TEAM_ABBREVIATION').set_index('TEAM_ABBREVIATION')['TEAM_NAME'].to_dict()

    def get_nickname(tri):
        full = team_map.get(tri.strip(), tri)
        return full.split(' ')[-1] # Nuggets, Lakers, etc.

    print("✅ Sistema listo, Carlos. El Oráculo está en línea.\n")
except Exception as e:
    print(f"❌ Error: {e}")
    exit()

def get_mexico_date():
    mx_now = datetime.utcnow() - timedelta(hours=6)
    return mx_now.strftime('%Y%m%d'), mx_now

def log_to_csv(h_tri, a_tri, h_p, a_p, total, spread, date_str):
    log_file = "predictions_history.csv"
    new_data = pd.DataFrame([{
        'Date': date_str, 'Home': h_tri, 'Away': a_tri,
        'Pred_Home': h_p, 'Pred_Away': a_p, 'Pred_Total': total,
        'Pred_Spread': spread, 'Actual_Home': np.nan, 'Actual_Away': np.nan
    }])
    if not os.path.isfile(log_file):
        new_data.to_csv(log_file, index=False)
    else:
        df_ex = pd.read_csv(log_file)
        if not ((df_ex['Date'] == date_str) & (df_ex['Home'] == h_tri)).any():
            new_data.to_csv(log_file, mode='a', header=False, index=False)

def predict_game(h_tri, a_tri, time_mx, date_obj):
    try:
        # Aquí va la carga de tus features reales para el model.predict
        # Por ahora generamos la estructura que el front necesita ver
        h_p = round(float(np.random.normal(115, 4)), 1)
        a_p = round(float(np.random.normal(110, 4)), 1)
        
        total = round(h_p + a_p, 1)
        spread = round(a_p - h_p, 1) # Hándicap para el local (Línea de apuesta)
        edge = round(np.random.uniform(2.5, 9.5), 1) # Ventaja detectada
        
        log_to_csv(h_tri, a_tri, h_p, a_p, total, spread, date_obj.strftime('%Y-%m-%d'))

        return {
            "home": get_nickname(h_tri),
            "away": get_nickname(a_tri),
            "hPred": h_p,
            "aPred": a_p,
            "total": total,
            "spread": spread, # HÁNDICAP
            "edge": edge,     # EDGE VALUE
            "pick": get_nickname(h_tri) if h_p > a_p else get_nickname(a_tri),
            "totalType": "OVER" if total > 225.5 else "UNDER",
            "confidence": int(np.random.randint(70, 98)),
            "time": time_mx
        }
    except: return None

if __name__ == "__main__":
    date_f, mx_d = get_mexico_date()
    resp = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_f}")
    if resp.status_code == 200:
        events = resp.json().get('events', [])
        web_preds = []
        for ev in events:
            comp = ev['competitions'][0]
            if comp['status']['type']['name'] != 'STATUS_FINAL':
                h = next(c for c in comp['competitors'] if c['homeAway'] == 'home')['team']['abbreviation']
                a = next(c for c in comp['competitors'] if c['homeAway'] == 'away')['team']['abbreviation']
                t_mx = (datetime.strptime(ev['date'], "%Y-%m-%dT%H:%MZ") - timedelta(hours=6)).strftime("%I:%M %p")
                res = predict_game(h, a, t_mx, mx_d)
                if res: web_preds.append(res)
        
        with open('predictions.json', 'w', encoding='utf-8') as f:
            json.dump(web_preds, f, indent=4)