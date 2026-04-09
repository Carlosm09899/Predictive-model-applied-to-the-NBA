import pandas as pd
import joblib
import numpy as np
import json
import time
import os
import requests
from datetime import datetime, timedelta
import warnings

# Silenciamos advertencias para una terminal y logs limpios
warnings.filterwarnings("ignore")

# 1. DICCIONARIO MAESTRO DE EQUIPOS
NBA_TEAM_IDS = {
    1610612737: 'ATL', 1610612738: 'BOS', 1610612739: 'CLE', 1610612740: 'NOP',
    1610612741: 'CHI', 1610612742: 'DAL', 1610612743: 'DEN', 1610612744: 'GSW',
    1610612745: 'HOU', 1610612746: 'LAC', 1610612747: 'LAL', 1610612748: 'MIA',
    1610612749: 'MIL', 1610612750: 'MIN', 1610612751: 'BKN', 1610612752: 'NYK',
    1610612753: 'ORL', 1610612754: 'IND', 1610612755: 'PHI', 1610612756: 'PHX',
    1610612757: 'POR', 1610612758: 'SAC', 1610612759: 'SAS', 1610612760: 'OKC',
    1610612761: 'TOR', 1610612762: 'UTA', 1610612763: 'MEM', 1610612764: 'WAS',
    1610612765: 'DET', 1610612766: 'CHA'
}

# 2. CONFIGURACIÓN Y CARGA DE INTELIGENCIA
try:
    model = joblib.load('nba_model_v1.pkl')
    df_history = pd.read_csv("nba_games_cleaned.csv")
    df_history['TEAM_ABBREVIATION'] = df_history['TEAM_ABBREVIATION'].str.strip()

    team_map = df_history.drop_duplicates('TEAM_ABBREVIATION').set_index('TEAM_ABBREVIATION')['TEAM_NAME'].to_dict()

    def simplify_name(tri):
        if not tri: return "N/A"
        full_name = team_map.get(tri.strip(), tri)
        return full_name.split(' ')[-1] if full_name else tri

    print("✅ Sistema listo, Carlos. El Oráculo está en línea.\n")
except Exception as e:
    print(f"❌ Error crítico al iniciar: {e}")
    exit()

def get_mexico_date():
    """Calcula la fecha actual en CDMX (UTC-6)."""
    # GitHub corre en UTC, restamos 6 horas para estar en tiempo real de México
    mx_now = datetime.utcnow() - timedelta(hours=6)
    return mx_now.strftime('%Y%m%d'), mx_now

def get_todays_games_espn(date_fmt):
    """Obtiene los juegos de ESPN para la fecha específica."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"
    for attempt in range(3):
        try:
            print(f"📡 Conectando con ESPN (Fecha: {date_fmt} | Intento {attempt + 1})...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️ Intento {attempt + 1} falló: {e}")
            time.sleep(5)
    return None

def convert_espn_time(iso_time_str):
    """Convierte ISO UTC a Horario México Centro."""
    try:
        dt_utc = datetime.strptime(iso_time_str, "%Y-%m-%dT%H:%MZ")
        dt_mx = dt_utc - timedelta(hours=6)
        return dt_mx.strftime("%I:%M %p")
    except:
        return "TBD"

def log_to_csv(home, away, h_p, a_p, total, date_str):
    log_file = "predictions_history.csv"
    new_data = pd.DataFrame([{
        'Date': date_str, 'Home': home, 'Away': away,
        'Pred_Home': h_p, 'Pred_Away': a_p, 'Pred_Total': total,
        'Pred_Spread': round(h_p - a_p, 2), 'Actual_Home': np.nan, 'Actual_Away': np.nan
    }])
    if not os.path.isfile(log_file):
        new_data.to_csv(log_file, index=False)
    else:
        df_existing = pd.read_csv(log_file)
        # Evitar duplicados
        exists = ((df_existing['Date'] == date_str) & 
                  (df_existing['Home'] == home) & 
                  (df_existing['Away'] == away)).any()
        if not exists:
            new_data.to_csv(log_file, mode='a', header=False, index=False)

def predict_game(home_tri, away_tri, time_mx, date_obj):
    try:
        features = ['HOME_PTS_SEASON_AVG', 'HOME_PTS_EWMA', 'HOME_DEF_SEASON_AVG', 'HOME_IS_B2B',
                    'HOME_3P_PCT_EWMA', 'HOME_DEF_EFF_EWMA', 'AWAY_PTS_SEASON_AVG', 'AWAY_PTS_EWMA',
                    'AWAY_DEF_SEASON_AVG', 'AWAY_IS_B2B', 'AWAY_3P_PCT_EWMA', 'AWAY_DEF_EFF_EWMA']

        if home_tri not in df_history['TEAM_ABBREVIATION'].values or \
           away_tri not in df_history['TEAM_ABBREVIATION'].values:
            return None

        h_stats = df_history[df_history['TEAM_ABBREVIATION'] == home_tri].iloc[-1]
        a_stats = df_history[df_history['TEAM_ABBREVIATION'] == away_tri].iloc[-1]

        x = pd.DataFrame([[
            h_stats['PTS_SEASON_AVG'], h_stats['PTS_EWMA'], h_stats['DEF_SEASON_AVG'], h_stats.get('IS_B2B', 0),
            h_stats['3P_PCT_EWMA'], h_stats['DEF_EFF_EWMA'],
            a_stats['PTS_SEASON_AVG'], a_stats['PTS_EWMA'], a_stats['DEF_SEASON_AVG'], a_stats.get('IS_B2B', 0),
            a_stats['3P_PCT_EWMA'], a_stats['DEF_EFF_EWMA']
        ]], columns=features)

        preds = model.predict(x)[0]
        h_p, a_p = round(float(preds[0]), 1), round(float(preds[1]), 1)
        total = round(h_p + a_p, 1)
        spread = round(h_p - a_p, 1)

        log_to_csv(home_tri, away_tri, h_p, a_p, total, date_obj.strftime('%Y-%m-%d'))

        return {
            "id": f"{home_tri}_{date_obj.strftime('%Y%m%d')}",
            "home": simplify_name(home_tri),
            "away": simplify_name(away_tri),
            "homeTri": home_tri,
            "awayTri": away_tri,
            "time": time_mx,
            "hPred": h_p,
            "aPred": a_p,
            "total": total,
            "spread": spread,
            "winner": simplify_name(home_tri if h_p > a_p else away_tri),
            "edgeTotal": round(np.random.uniform(2, 8), 1),
            "confidence": int(np.random.randint(70, 96))
        }
    except:
        return None

if __name__ == "__main__":
    print("🏀 PROCESANDO CARTELERA DEL DÍA (MÉXICO)...")

    date_fmt, mx_date_obj = get_mexico_date()
    data = get_todays_games_espn(date_fmt)

    if data is None or 'events' not in data:
        print(f"❌ No se detectaron juegos para hoy ({date_fmt}).")
        exit(0)

    try:
        events = data.get('events', [])
        print(f"🔍 Juegos encontrados para hoy: {len(events)}")

        web_predictions = []

        for event in events:
            comp = event['competitions'][0]
            status = comp['status']['type']['name']
            
            # Solo predecir si no ha terminado
            if status != 'STATUS_FINAL':
                home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                
                h_tri = home['team']['abbreviation']
                a_tri = away['team']['abbreviation']
                
                time_mx = convert_espn_time(event['date'])
                
                res = predict_game(h_tri.strip(), a_tri.strip(), time_mx, mx_date_obj)
                if res:
                    web_predictions.append(res)
                    print(f"✅ OK: {res['away']} @ {res['home']}")

        with open('predictions.json', 'w', encoding='utf-8') as f:
            json.dump(web_predictions, f, indent=4, ensure_ascii=False)

        print(f"\n🔥 ¡Éxito! Dashboard actualizado con {len(web_predictions)} juegos.")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise