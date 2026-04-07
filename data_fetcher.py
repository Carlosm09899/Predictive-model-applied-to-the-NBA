import pandas as pd
import time
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder


def response_to_df(nba_response):
    """
    Convierte la respuesta de la NBA API v3 a un DataFrame.
    
    La API v3 regresa los datos "escondidos" dentro de un objeto JSON así:
    {
        "resultSets": [
            {
                "name": "LeagueGameFinderResults",
                "headers": ["SEASON_ID", "TEAM_ID", ...],
                "rowSet": [[...], [...], ...]
            }
        ]
    }
    Esta función los saca y los convierte en un DataFrame normal.
    """
    raw = nba_response.get_dict()

    # La API v3 usa "resultSets"; si el endpoint usa otro nombre,
    # probamos también con "resultSet" (singular) como fallback
    result_sets = raw.get("resultSets") or raw.get("resultSet")

    if result_sets:
        headers = result_sets[0]["headers"]
        rows    = result_sets[0]["rowSet"]
    else:
        # Último recurso: dejar que la librería lo intente por su cuenta
        return nba_response.get_data_frames()[0]

    return pd.DataFrame(rows, columns=headers)


# 1. Obtener la lista de todos los equipos
nba_teams = teams.get_teams()
all_games = []

print(f"Iniciando la descarga de {len(nba_teams)} equipos...")

# 2. Loop para jalar los datos de cada uno
for team in nba_teams:
    print(f"Descargando datos de: {team['full_name']}...")

    # Buscamos los juegos de este equipo
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team['id'])

    # ✅ Usamos response_to_df() en vez de get_data_frames()[0]
    #    para compatibilidad con la NBA API v3
    games = response_to_df(gamefinder)

    # Solo nos interesan juegos de la temporada regular reciente (opcional filtrar aquí)
    all_games.append(games)

    # REGLA DE ORO: Pausa de 1 segundo para que la NBA no nos banee la IP
    time.sleep(1.2)

# 3. Juntar todo en un solo DataFrame
df_total = pd.concat(all_games, ignore_index=True)

# 4. Guardar en un CSV para trabajar localmente
df_total.to_csv("nba_games_raw.csv", index=False)

print("¡Listo, Carlos! Datos guardados en 'nba_games_raw.csv'.")
print(f"Total de juegos recolectados: {len(df_total)}")