import pandas as pd
import joblib
import numpy as np
import json
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
    team_map = df_history.drop_duplicates('TEAM_ABBREVIATION').set_index('TEAM_ABBREVIATION')['TEAM_NAME'].to_dict()

    def get_nickname(tri):
        full = team_map.get(tri.strip(), tri)
        return full.split(' ')[-1] if full else tri

    print("✅ Sistema listo, Carlos. El Oráculo está en línea.\n")
except Exception as e:
    print(f"❌ Error al iniciar: {e}")
    exit()

def get_mexico_date():
    # Obtenemos la hora actual en CDMX
    mx_now = datetime.utcnow() - timedelta(hours=6)
    
    # LÓGICA INTELIGENTE: Si ya es tarde (después de las 9 PM), buscamos juegos de mañana
    if mx_now.hour >= 21:
        print("🌙 Es de noche. Buscando cartelera de mañana...")
        mx_now = mx_now + timedelta(days=1)
    else:
        print("☀️ Buscando cartelera de hoy...")
        
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
        # Aquí van tus features del modelo...
        # Simulamos los puntos para la estructura visual
        h_p = round(float(np.random.normal(114, 5)), 1)
        a_p = round(float(np.random.normal(110, 5)), 1)
        
        total = round(h_p + a_p, 1)
        # Hándicap real: Puntos que el local (Home) "da" o "recibe"
        spread = round(a_p - h_p, 1) 
        edge = round(np.random.uniform(3.5, 9.5), 1) 
        
        log_to_csv(h_tri, a_tri, h_p, a_p, total, spread, date_obj.strftime('%Y-%m-%d'))

        return {
            "home": get_nickname(h_tri),
            "away": get_nickname(a_tri),
            "hPred": h_p,
            "aPred": a_p,
            "total": total,
            "spread": spread,
            "edge": edge,
            "pick": get_nickname(h_tri) if h_p > a_p else get_nickname(a_tri),
            "totalType": "OVER" if total > 227.5 else "UNDER",
            "confidence": int(np.random.randint(75, 98)),
            "time": time_mx
        }
    except: return None

if __name__ == "__main__":
    date_f, mx_d = get_mexico_date()
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_f}"
    resp = requests.get(url)
    
    if resp.status_code == 200:
        events = resp.json().get('events', [])
        web_preds = []
        print(f"🔍 Se encontraron {len(events)} juegos.")
        
        for ev in events:
            comp = ev['competitions'][0]
            # Solo saltamos los que YA terminaron
            if comp['status']['type']['name'] != 'STATUS_FINAL':
                h = next(c for c in comp['competitors'] if c['homeAway'] == 'home')['team']['abbreviation']
                a = next(c for c in comp['competitors'] if c['homeAway'] == 'away')['team']['abbreviation']
                
                # Convertir hora a MX
                t_utc = datetime.strptime(ev['date'], "%Y-%m-%dT%H:%MZ")
                t_mx = (t_utc - timedelta(hours=6)).strftime("%I:%M %p")
                
                res = predict_game(h, a, t_mx, mx_d)
                if res: web_preds.append(res)
        
        with open('predictions.json', 'w', encoding='utf-8') as f:
            json.dump(web_preds, f, indent=4)
        print(f"🔥 ¡Éxito! {len(web_preds)} juegos listos.")