"""
data_fetcher.py — Descarga histórica de juegos NBA via ESPN API
Uso: python data_fetcher.py
Genera: nba_games_raw.csv

NOTA: Este script se ejecuta localmente una vez para generar/actualizar
el CSV de datos históricos. NO se ejecuta en GitHub Actions.
"""
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def fetch_games_for_date(date_str):
    """Obtiene los juegos finalizados de una fecha específica (YYYY-MM-DD)."""
    date_fmt = date_str.replace('-', '')
    url = f"{ESPN_BASE}?dates={date_fmt}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get('events', [])
    except Exception as e:
        print(f"  ⚠️ Error en {date_str}: {e}")
        return []

def parse_events(events, date_str):
    """Extrae filas de datos de los eventos ESPN al formato del CSV."""
    rows = []
    for event in events:
        competition = event['competitions'][0]
        status_name = competition['status']['type']['name']

        # Solo juegos terminados
        if status_name != 'STATUS_FINAL':
            continue

        game_id = event['id']
        season_type = event.get('seasonType', {}).get('type', 2)
        # Solo temporada regular (type=2) y playoffs (type=3)
        if season_type not in (2, 3):
            continue

        competitors = competition['competitors']
        home_c = next((c for c in competitors if c['homeAway'] == 'home'), None)
        away_c = next((c for c in competitors if c['homeAway'] == 'away'), None)

        if not home_c or not away_c:
            continue

        season_year = event.get('season', {}).get('year', 2025)
        season_id = f"2{season_year - 1}{str(season_year)[-2:]}"

        for c in [home_c, away_c]:
            team = c['team']
            stats = {s['name']: s.get('displayValue', '0') for s in c.get('statistics', [])}

            def safe_float(val, default=0.0):
                try:
                    return float(str(val).replace('%', '').strip())
                except:
                    return default

            try:
                pts = int(c.get('score', 0))
            except:
                pts = 0

            # Determinar el rival
            opponent = away_c if c['homeAway'] == 'home' else home_c
            try:
                opp_pts = int(opponent.get('score', 0))
            except:
                opp_pts = 0

            wl = 'W' if pts > opp_pts else 'L'

            rows.append({
                'SEASON_ID': season_id,
                'TEAM_ID': team.get('id', ''),
                'TEAM_ABBREVIATION': team.get('abbreviation', ''),
                'TEAM_NAME': team.get('displayName', ''),
                'GAME_ID': game_id,
                'GAME_DATE': date_str,
                'MATCHUP': f"{team.get('abbreviation','')} {'vs.' if c['homeAway']=='home' else '@'} {opponent['team'].get('abbreviation','')}",
                'WL': wl,
                'PTS': pts,
                'OPP_PTS': opp_pts,
                'FG3_PCT': safe_float(stats.get('threePointFieldGoalPct', 0)) / 100,
            })
    return rows

def fetch_historical_data(start_date='2022-10-01', end_date=None):
    """Descarga todos los juegos desde start_date hasta end_date."""
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    all_rows = []
    total_days = (end - current).days + 1
    day_count = 0

    print(f"🏀 Descargando datos ESPN desde {start_date} hasta {end_date}...")
    print(f"   Total de días a consultar: {total_days}\n")

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        events = fetch_games_for_date(date_str)
        rows = parse_events(events, date_str)

        if rows:
            all_rows.extend(rows)
            print(f"  ✅ {date_str} — {len(rows)//2} juegos finalizados")
        
        day_count += 1
        if day_count % 50 == 0:
            print(f"  📊 Progreso: {day_count}/{total_days} días procesados...")

        current += timedelta(days=1)
        time.sleep(0.3)  # Gentil con la API de ESPN

    if not all_rows:
        print("❌ No se obtuvieron datos.")
        return

    df = pd.DataFrame(all_rows)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE').reset_index(drop=True)

    # Verificar y calcular OPP_PTS doble (por si acaso)
    df.to_csv("nba_games_raw.csv", index=False)

    print(f"\n✅ ¡Listo! Datos guardados en 'nba_games_raw.csv'.")
    print(f"   Total de registros (filas por equipo): {len(df)}")
    print(f"   Juegos únicos: {df['GAME_ID'].nunique()}")
    print(f"   Rango: {df['GAME_DATE'].min().date()} → {df['GAME_DATE'].max().date()}")

if __name__ == "__main__":
    # Ajusta el rango según necesites
    fetch_historical_data(start_date='2022-10-01')