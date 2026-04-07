import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime, timedelta

def audit_my_bets():
    print("📋 AUDITORÍA DE APUESTAS - EL ORÁCULO DE CARLOS\n")
    
    try:
        df_log = pd.read_csv("predictions_history.csv")
    except:
        print("📭 No hay historial de predicciones para auditar.")
        return

    # Solo auditamos filas que no tengan resultados reales todavía
    pending = df_log[df_log['Actual_Home'].isna()].copy()
    
    if pending.empty:
        print("✅ Todas las apuestas registradas ya están auditadas.")
        return

    print(f"🔍 Buscando resultados reales para {len(pending)} juegos...")

    # Traemos los juegos de la liga de los últimos 2 días
    game_finder = leaguegamefinder.LeagueGameFinder(season_nullable='2025-26')
    actual_games = game_finder.get_data_frames()[0]
    
    # Limpiamos fechas de la API
    actual_games['GAME_DATE'] = pd.to_datetime(actual_games['GAME_DATE'])

    hits = 0
    total_games = 0

    for idx, row in pending.iterrows():
        # Buscamos el juego real por equipo y fecha
        match = actual_games[
            (actual_games['TEAM_ABBREVIATION'] == row['Home']) & 
            (actual_games['GAME_DATE'].dt.strftime('%Y-%m-%d') == row['Date'])
        ]

        if not match.empty:
            actual_h = match.iloc[0]['PTS']
            # El oponente está en la misma fecha con el mismo Matchup
            actual_a = actual_games[
                (actual_games['GAME_ID'] == match.iloc[0]['GAME_ID']) & 
                (actual_games['TEAM_ABBREVIATION'] == row['Away'])
            ].iloc[0]['PTS']

            # Actualizamos el log
            df_log.loc[idx, 'Actual_Home'] = actual_h
            df_log.loc[idx, 'Actual_Away'] = actual_a
            
            # --- Métrica de Éxito ---
            win_pred = row['Home'] if row['Pred_Home'] > row['Pred_Away'] else row['Away']
            win_real = row['Home'] if actual_h > actual_a else row['Away']
            
            is_hit = "✅" if win_pred == win_real else "❌"
            if win_pred == win_real: hits += 1
            total_games += 1

            error_total = abs((actual_h + actual_a) - row['Pred_Total'])
            
            print(f"🏟️  {row['Away']} @ {row['Home']} | {is_hit}")
            print(f"   Pred: {row['Pred_Total']} | Real: {actual_h + actual_a} (Error: {error_total} pts)")
            print("-" * 40)

    # Guardar resultados finales
    df_log.to_csv("predictions_history.csv", index=False)
    
    if total_games > 0:
        accuracy = (hits / total_games) * 100
        print(f"\n📊 RESUMEN DE LA JORNADA:")
        print(f"🎯 Efectividad de Ganador: {accuracy:.2f}%")
        print(f"💰 ROI Teórico: Pendiente de integrar momios de Playdoit.")

if __name__ == "__main__":
    audit_my_bets()