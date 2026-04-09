import pandas as pd
import joblib
import numpy as np
import json
import time
import os
import requests
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# 1. CARGA DE INTELIGENCIA
try:
    model = joblib.load('nba_model_v1.pkl')
    df_history = pd.read_csv("nba_games_cleaned.csv")
    df_history['TEAM_ABBREVIATION'] = df_history['TEAM_ABBREVIATION'].str.strip()
    
    # Mapeo para sacar Nombres (Nuggets, Lakers, etc)
    team_map = df_history.drop_duplicates('TEAM_ABBREVIATION').set_index('TEAM_ABBREVIATION')['TEAM_NAME'].to_dict()

    def get_team_nickname(tri):
        full_name = team_map.get(tri.strip(), tri)
        return full_name.split(' ')[-1] # Retorna solo la última palabra (Nuggets)

    print("✅ Sistema listo, Carlos. El Oráculo está en línea.\n")
except Exception as e:
    print(f"❌ Error crítico al iniciar: {e}")
    exit()

def get_mexico_date():
    mx_now = datetime.utcnow() - timedelta(hours=6)
    return mx_now.strftime('%Y%m%d'), mx_now

def get_todays_games_espn(date_fmt):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"
    try:
        resp = requests.get(url, timeout=30)
        return resp.json()
    except:
        return None

def log_to_csv(home, away, h_p, a_p, total, date_str):
    log_file = "predictions_history.csv"
    new_data = pd.DataFrame([{
        'Date': date_str, 'Home': home, 'Away': away,
        'Pred_Home': h_p, 'Pred_Away': a_p, 'Pred_Total': total,
        'Actual_Home': np.nan, 'Actual_Away': np.nan
    }])
    if not os.path.isfile(log_file):
        new_data.to_csv(log_file, index=False)
    else:
        df_existing = pd.read_csv(log_file)
        exists = ((df_existing['Date'] == date_str) & (df_existing['Home'] == home)).any()
        if not exists: new_data.to_csv(log_file, mode='a', header=False, index=False)

def predict_game(h_tri, a_tri, time_mx, date_obj):
    try:
        # Aquí iría tu lógica de stats del modelo... 
        # (Usamos simulación para este bloque de estructura)
        h_stats = df_history[df_history['TEAM_ABBREVIATION'] == h_tri].iloc[-1]
        a_stats = df_history[df_history['TEAM_ABBREVIATION'] == a_tri].iloc[-1]
        
        # Simulamos predicción del modelo (Sustituir por model.predict)
        h_p = round(float(np.random.normal(114, 5)), 1)
        a_p = round(float(np.random.normal(110, 5)), 1)
        
        total = round(h_p + a_p, 1)
        edge = round(np.random.uniform(3, 11), 1)
        
        log_to_csv(h_tri, a_tri, h_p, a_p, total, date_obj.strftime('%Y-%m-%d'))

        return {
            "home": get_team_nickname(h_tri),
            "away": get_team_nickname(a_tri),
            "homeTri": h_tri,
            "awayTri": a_tri,
            "hPred": h_p,
            "aPred": a_p,
            "total": total,
            "spread": round(h_p - a_p, 1),
            "edge": edge,
            "pick": get_team_nickname(h_tri) if h_p > a_p else get_team_nickname(a_tri),
            "totalType": "OVER" if total > 228 else "UNDER",
            "confidence": int(np.random.randint(75, 98)),
            "time": time_mx
        }
    except: return None

if __name__ == "__main__":
    date_fmt, mx_date = get_mexico_date()
    data = get_todays_games_espn(date_fmt)
    if data:
        events = data.get('events', [])
        web_preds = []
        for event in events:
            comp = event['competitions'][0]
            if comp['status']['type']['name'] != 'STATUS_FINAL':
                h = next(c for c in comp['competitors'] if c['homeAway'] == 'home')['team']['abbreviation']
                a = next(c for c in comp['competitors'] if c['homeAway'] == 'away')['team']['abbreviation']
                # Ajuste de hora México
                t_utc = datetime.strptime(event['date'], "%Y-%m-%dT%H:%MZ")
                t_mx = (t_utc - timedelta(hours=6)).strftime("%I:%M %p")
                
                res = predict_game(h, a, t_mx, mx_date)
                if res: web_preds.append(res)
        
        with open('predictions.json', 'w', encoding='utf-8') as f:
            json.dump(web_preds, f, indent=4)
        print(f"✅ {len(web_preds)} juegos de hoy procesados.")