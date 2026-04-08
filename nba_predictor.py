import pandas as pd
import joblib
import numpy as np
import json
import time
import os
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2
import warnings

HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.nba.com/',
    'Connection': 'keep-alive',
}

def get_todays_games():
    print("🏀 PROCESANDO CARTELERA Y EXPORTANDO A LA WEB...")
    
    # Intentar 3 veces con paciencia
    for attempt in range(3):
        try:
            print(f"📡 Conectando con la NBA (Intento {attempt + 1})...")
            sb = scoreboardv2.ScoreboardV2(
                league_id='00', 
                timeout=60, 
                headers=HEADERS # <--- Aquí está el truco
            )
            return sb.get_data_frames()[1]
        except Exception as e:
            print(f"⚠️ Intento {attempt + 1} falló. Reintentando en 10 seg...")
            time.sleep(10)
    
    return None

# Silenciamos advertencias para una terminal y logs limpios
warnings.filterwarnings("ignore")

# 1. DICCIONARIO MAESTRO DE EQUIPOS (Failsafe para errores de la API a medianoche)
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
    # Cargamos el cerebro (XGBoost/Random Forest)
    model = joblib.load('nba_model_v1.pkl')
    # Cargamos la refinería de datos
    df_history = pd.read_csv("nba_games_cleaned.csv")
    df_history['TEAM_ABBREVIATION'] = df_history['TEAM_ABBREVIATION'].str.strip()
    
    # Mapeo de nombres para estilo Google (LAL -> Lakers)
    team_map = df_history.drop_duplicates('TEAM_ABBREVIATION').set_index('TEAM_ABBREVIATION')['TEAM_NAME'].to_dict()
    
    def simplify_name(tri):
        if not tri: return "N/A"
        full_name = team_map.get(tri.strip(), tri)
        return full_name.split(' ')[-1] if full_name else tri

    print("✅ Sistema listo, Carlos. El Oráculo está en línea.\n")
except Exception as e:
    print(f"❌ Error crítico al iniciar: {e}")
    exit()

def convert_to_mexico_time(et_time_str, game_date):
    """Convierte horario ET (NY) a Horario de México Centro (CDMX)."""
    try:
        time_clean = et_time_str.lower().replace('et', '').strip()
        et_time = datetime.strptime(time_clean, "%I:%M %p")
        # CDMX no cambia horario. USA sí. Ajuste: Abr-Oct = 2h, Resto = 1h.
        offset = 2 if (game_date.month >= 4 and game_date.month <= 10) else 1
        mx_time = et_time - timedelta(hours=offset)
        return mx_time.strftime("%I:%M %p") + " (MX)"
    except:
        return et_time_str

def log_to_csv(home, away, h_p, a_p, total, date_str):
    """Guarda la predicción para ser auditada por el Backtester."""
    log_file = "predictions_history.csv"
    new_data = pd.DataFrame([{
        'Date': date_str, 'Home': home, 'Away': away,
        'Pred_Home': h_p, 'Pred_Away': a_p, 'Pred_Total': total,
        'Pred_Spread': round(h_p - a_p, 2), 'Actual_Home': np.nan, 'Actual_Away': np.nan
    }])
    if not os.path.isfile(log_file):
        new_data.to_csv(log_file, index=False)
    else:
        new_data.to_csv(log_file, mode='a', header=False, index=False)

def predict_game(home_tri, away_tri, time_mx, date_obj):
    """Genera la predicción completa con análisis de valor."""
    try:
        # Variables exactas del entrenamiento (Features)
        features = ['HOME_PTS_SEASON_AVG', 'HOME_PTS_EWMA', 'HOME_DEF_SEASON_AVG', 'HOME_IS_B2B', 
                    'HOME_3P_PCT_EWMA', 'HOME_DEF_EFF_EWMA', 'AWAY_PTS_SEASON_AVG', 'AWAY_PTS_EWMA', 
                    'AWAY_DEF_SEASON_AVG', 'AWAY_IS_B2B', 'AWAY_3P_PCT_EWMA', 'AWAY_DEF_EFF_EWMA']
        
        # Validar existencia de datos
        if home_tri not in df_history['TEAM_ABBREVIATION'].values or \
           away_tri not in df_history['TEAM_ABBREVIATION'].values:
            return None

        h_stats = df_history[df_history['TEAM_ABBREVIATION'] == home_tri].iloc[-1]
        a_stats = df_history[df_history['TEAM_ABBREVIATION'] == away_tri].iloc[-1]

        # Construir vector de entrada
        x = pd.DataFrame([[
            h_stats['PTS_SEASON_AVG'], h_stats['PTS_EWMA'], h_stats['DEF_SEASON_AVG'], h_stats.get('IS_B2B', 0),
            h_stats['3P_PCT_EWMA'], h_stats['DEF_EFF_EWMA'],
            a_stats['PTS_SEASON_AVG'], a_stats['PTS_EWMA'], a_stats['DEF_SEASON_AVG'], a_stats.get('IS_B2B', 0),
            a_stats['3P_PCT_EWMA'], a_stats['DEF_EFF_EWMA']
        ]], columns=features)

        # Predecir
        preds = model.predict(x)[0]
        h_p, a_p = round(float(preds[0]), 1), round(float(preds[1]), 1)
        total = round(h_p + a_p, 1)
        spread = round(h_p - a_p, 1)
        
        # Guardar en CSV para auditoría
        log_to_csv(home_tri, away_tri, h_p, a_p, total, date_obj.strftime('%Y-%m-%d'))

        # Retornar objeto para la Web (JSON)
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
            "edgeTotal": round(np.random.uniform(2, 12), 1), # Se calculará con odds reales en Fase 3
            "confidence": int(np.random.randint(65, 98))     # Se calculará con varianza en Fase 3
        }
    except:
        return None

if __name__ == "__main__":
    print("🏀 PROCESANDO CARTELERA Y EXPORTANDO A LA WEB...")
    
    # Lógica de búsqueda (si es noche, busca mañana)
    now = datetime.now()
    search_date = now if now.hour < 22 else now + timedelta(days=1)
    date_str = search_date.strftime('%Y-%m-%d')
    
    try:
        sb = scoreboardv2.ScoreboardV2(game_date=date_str)
        frames = sb.get_data_frames()
        header = frames[0]
        line_score = frames[1] if len(frames) > 1 else pd.DataFrame()
        
        web_predictions = []
        print(f"🔍 Fecha: {date_str} | Juegos encontrados: {len(header)}")

        for _, row in header.iterrows():
            # Recuperación robusta de equipos
            h_tri = row.get('HOME_TEAM_ABBREVIATION') or NBA_TEAM_IDS.get(row.get('HOME_TEAM_ID'))
            a_tri = row.get('VISITOR_TEAM_ABBREVIATION') or NBA_TEAM_IDS.get(row.get('VISITOR_TEAM_ID'))
            
            status = str(row.get('GAME_STATUS_TEXT', '')).strip()
            if "Final" not in status and h_tri and a_tri:
                time_mx = convert_to_mexico_time(status, search_date)
                
                # Predecir
                res = predict_game(h_tri.strip(), a_tri.strip(), time_mx, search_date)
                if res:
                    web_predictions.append(res)
                    print(f"✅ Pick generado: {res['away']} @ {res['home']}")

        # 🚀 EXPORTACIÓN FINAL A JSON PARA EL DASHBOARD
        with open('predictions.json', 'w', encoding='utf-8') as f:
            json.dump(web_predictions, f, indent=4, ensure_ascii=False)
            
        print(f"\n🔥 ¡Éxito! Se exportaron {len(web_predictions)} juegos.")
        print(f"📂 Archivos actualizados: 'predictions.json' y 'predictions_history.csv'")
        print("💻 Abre tu 'nba_dashboard.html' para ver los resultados.")

    except Exception as e:
        print(f"❌ Error en la API: {e}")