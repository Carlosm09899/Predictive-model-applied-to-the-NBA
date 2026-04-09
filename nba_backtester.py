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
    """Obtiene los resultados de una fecha usando la API de ESPN (sin bloqueos de IP)."""
    date_fmt = date_str.replace('-', '')  # YYYYMMDD
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_fmt}"

    for attempt in range(3):
        try:
            print(f"📡 Conectando con ESPN (Intento {attempt + 1})...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('events', [])
        except Exception as e:
            print(f"⚠️ Error: {e}. Reintentando...")
            if attempt < 2:
                time.sleep(10)
    return None

def audit_my_bets():
    print("📊 AUDITORÍA DE APUESTAS - EL ORÁCULO DE CARLOS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    log_file = "predictions_history.csv"
    results_json = "results.json"

    # 🛡️ SEGURO DE VIDA: Si el archivo results.json no existe, lo creamos vacío
    if not os.path.exists(results_json):
        with open(results_json, 'w', encoding='utf-8') as f:
            json.dump([], f)

    if not os.path.exists(log_file):
        print("📭 No hay historial en CSV para auditar.")
        return

    df_log = pd.read_csv(log_file)
    # Buscamos solo los que no tienen resultado real aún
    pending = df_log[df_log['Actual_Home'].isna()].copy()

    if pending.empty:
        print("✅ Todo está al día. No hay juegos pendientes de ayer.")
        return

    print(f"🔍 Buscando resultados reales para {len(pending)} juegos...")

    # Obtener todas las fechas únicas pendientes y traer los resultados de ESPN
    pending_dates = pending['Date'].unique()
    all_events = []
    for d in pending_dates:
        events = get_games_for_date_espn(d)
        if events is None:
            print(f"❌ No se pudo obtener datos de ESPN para {d} después de 3 intentos.")
            print("⏳ Se intentará de nuevo en la próxima ejecución automática.")
            return
        all_events.extend(events)

    if not all_events:
        print("⏳ Todavía no hay resultados disponibles en ESPN.")
        return

    # Construir un diccionario: (TEAM_ABB, DATE) -> puntos
    # para búsqueda rápida
    scores = {}  # key: (team_abbreviation, 'YYYY-MM-DD') -> pts
    for event in all_events:
        competition = event['competitions'][0]
        status_name = competition['status']['type']['name']
        # Solo juegos terminados
        if status_name != 'STATUS_FINAL':
            continue

        # Fecha del juego en formato YYYY-MM-DD (ESPN devuelve UTC)
        game_date_utc = event.get('date', '')
        try:
            game_date = datetime.strptime(game_date_utc, "%Y-%m-%dT%H:%MZ")
            # Ajustar a hora local (juegos de noche en ET son el día anterior en UTC)
            # ESPN suele tener la fecha correcta en el campo 'date' de cada competencia
            game_date_str = game_date.strftime('%Y-%m-%d')
        except:
            game_date_str = game_date_utc[:10]

        for competitor in competition['competitors']:
            tri = competitor['team']['abbreviation']
            try:
                pts = int(competitor['score'])
            except:
                pts = None
            if pts is not None:
                # Guardamos también con la fecha del día anterior por si hay desfase UTC
                scores[(tri, game_date_str)] = pts
                # Guardar también con la fecha ajustada -1 día (para juegos nocturnos)
                prev_date = (game_date - timedelta(hours=6)).strftime('%Y-%m-%d')
                scores[(tri, prev_date)] = pts

    hits = 0
    total_audited = 0

    for idx, row in pending.iterrows():
        date_pred = row['Date']
        h_tri = row['Home']
        a_tri = row['Away']

        actual_h_pts = scores.get((h_tri, date_pred))
        actual_a_pts = scores.get((a_tri, date_pred))

        if actual_h_pts is not None and actual_a_pts is not None:
            pred_win = h_tri if row['Pred_Home'] > row['Pred_Away'] else a_tri
            real_win = h_tri if actual_h_pts > actual_a_pts else a_tri

            if pred_win == real_win:
                hits += 1

            df_log.loc[idx, 'Actual_Home'] = actual_h_pts
            df_log.loc[idx, 'Actual_Away'] = actual_a_pts
            total_audited += 1
            status = "✅ HIT" if pred_win == real_win else "❌ MISS"
            print(f"{status}: {a_tri} {actual_a_pts} @ {h_tri} {actual_h_pts}")

    # Guardar el CSV con los nuevos datos reales
    df_log.to_csv(log_file, index=False)

    # 🚀 EXPORTAR PARA EL DASHBOARD WEB
    recent_results = df_log.dropna(subset=['Actual_Home']).tail(15).to_dict(orient='records')
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(recent_results, f, indent=4, ensure_ascii=False)

    if total_audited > 0:
        print(f"\n🎯 Sesión terminada. Efectividad: {(hits/total_audited)*100:.1f}%")
    else:
        print("\n⏳ Todavía no hay resultados finales oficiales para los juegos pendientes.")

if __name__ == "__main__":
    audit_my_bets()
