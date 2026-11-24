import csv
import sqlite3
from pathlib import Path


base_dir = Path(__file__).resolve().parent
db = sqlite3.connect(base_dir / "soccer_database.db")
cursor = db.cursor()


def read_csv(relative_path):
    with open(base_dir / relative_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


cursor.execute("""
    CREATE TABLE IF NOT EXISTS WorldCupRecords (
        year INTEGER PRIMARY KEY,
        team TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS WorldCup2026Teams (
        team TEXT PRIMARY KEY,
        "group" TEXT,
        confederation TEXT,
        host_nation TEXT,
        world_cup_debut TEXT,
        eliminated_round TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS WorldCup2026Matches (
        match_id INTEGER PRIMARY KEY,
        date TEXT,
        stage TEXT,
        "group" TEXT,
        team_1 TEXT,
        team_2 TEXT,
        score_1 INTEGER,
        score_2 INTEGER,
        winner TEXT,
        decided_by_penalties TEXT,
        notes TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS WorldCup2026TeamStats (
        team TEXT PRIMARY KEY,
        goals INTEGER,
        assists INTEGER,
        attempts_at_goal INTEGER,
        attempts_on_target INTEGER,
        attempts_off_target INTEGER,
        attempts_at_goal_conversion_rate_pc REAL,
        attempts_inside_the_penalty_area INTEGER,
        attempts_outside_the_penalty_area INTEGER,
        headed_attempts_at_goal INTEGER,
        xg REAL,
        xg_efficiency TEXT,
        corners INTEGER,
        possession_control_pc REAL,
        own_goals INTEGER,
        goals_conceded INTEGER,
        forced_turnovers INTEGER,
        ball_recovery_time REAL,
        defensive_pressures_applied INTEGER,
        defensive_pressures_directly_applied INTEGER,
        fouls_against INTEGER,
        fouls_for INTEGER,
        yellow_cards INTEGER,
        red_cards INTEGER,
        indirect_red_cards INTEGER,
        offsides INTEGER,
        passes INTEGER,
        passes_completed INTEGER,
        passing_accuracy_pc REAL,
        crosses INTEGER,
        crossing_accuracy_pc REAL,
        take_ons_completed INTEGER,
        defensive_line_breaks_attempted INTEGER,
        defensive_line_breaks_acc_pc REAL,
        switches_of_play_attempted INTEGER,
        switches_of_play_acc_pc REAL,
        clean_sheets INTEGER,
        goalkeeper_goals_conceded INTEGER,
        goalkeeper_saves INTEGER,
        goalkeeper_actions_inside_the_penalty_area INTEGER,
        goalkeeper_actions_outside_the_penalty_area INTEGER,
        offers_to_receive INTEGER,
        offers_in_behind INTEGER,
        offers_in_between INTEGER,
        offers_in_front INTEGER,
        offers_inside_team_shape INTEGER,
        offers_outside_team_shape INTEGER,
        receptions_in_behind INTEGER,
        receptions_between_midfield_and_defensive_line INTEGER,
        receptions_under_pressure INTEGER,
        average_speed REAL,
        high_speed_running REAL,
        sprints INTEGER,
        total_distance REAL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT,
        player_name TEXT,
        age INTEGER,
        nationality TEXT,
        team TEXT,
        jersey_number INTEGER,
        position TEXT,
        height_cm INTEGER,
        weight_kg INTEGER,
        preferred_foot TEXT,
        club_name TEXT,
        market_value_eur REAL,
        match_id TEXT,
        match_date TEXT,
        stadium TEXT,
        city TEXT,
        opponent_team TEXT,
        tournament_stage TEXT,
        match_result TEXT,
        goals_team INTEGER,
        goals_opponent INTEGER,
        minutes_played INTEGER,
        goals INTEGER,
        assists INTEGER,
        shots INTEGER,
        shots_on_target INTEGER,
        expected_goals_xg REAL,
        expected_assists_xa REAL,
        key_passes INTEGER,
        successful_passes INTEGER,
        total_passes INTEGER,
        pass_accuracy REAL,
        dribbles_attempted INTEGER,
        successful_dribbles INTEGER,
        crosses INTEGER,
        successful_crosses INTEGER,
        tackles INTEGER,
        interceptions INTEGER,
        clearances INTEGER,
        blocks INTEGER,
        aerial_duels_won INTEGER,
        aerial_duels_lost INTEGER,
        recoveries INTEGER,
        defensive_actions INTEGER,
        fouls_committed INTEGER,
        fouls_suffered INTEGER,
        yellow_cards INTEGER,
        red_cards INTEGER,
        offsides INTEGER,
        saves INTEGER,
        save_percentage REAL,
        punches INTEGER,
        clean_sheet INTEGER,
        goals_conceded INTEGER,
        penalty_saves INTEGER,
        distance_covered_km REAL,
        sprint_distance_km REAL,
        top_speed_kmh REAL,
        accelerations INTEGER,
        decelerations INTEGER,
        stamina_score REAL,
        player_rating REAL,
        performance_score REAL,
        offensive_contribution REAL,
        defensive_contribution REAL,
        possession_impact REAL,
        pressure_resistance REAL,
        creativity_score REAL,
        consistency_score REAL,
        clutch_performance_score REAL,
        total_goals_tournament INTEGER,
        total_assists_tournament INTEGER,
        total_minutes_tournament INTEGER,
        player_of_match_awards INTEGER,
        tournament_rating REAL,
        PRIMARY KEY (player_id, match_id)
    )
""")

# Insert rows into the tables from CSV files
def insert_rows(table, columns, rows):
    if not rows:
        raise ValueError(f"No data rows found for {table}")

    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [tuple(row[column] for column in columns) for row in rows]
    cursor.executemany(
        f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({placeholders})',
        values,
    )

# Set the expected headers for each CSV file and validate them against the actual headers read from the files
# Raise ValueError if the headers do not match the expected headers for each table
record_headers, record_rows = read_csv("data/wc_records.csv")
if set(record_headers or []) != {"Year", "Team"}:
    raise ValueError("World Cup records CSV headers do not match: " + str(record_headers))
record_rows = [{"year": row["Year"], "team": row["Team"]} for row in record_rows]

team_headers, team_rows = read_csv("data/2026WCteams.csv")
team_columns = ["team", "group", "confederation", "host_nation", "world_cup_debut", "eliminated_round"]
if set(team_headers or []) != set(team_columns):
    raise ValueError("2026 teams CSV headers do not match: " + str(team_headers))

match_headers, match_rows = read_csv("data/2026WCmatches.csv")
match_columns = [
    "match_id", "date", "stage", "group", "team_1", "team_2", "score_1",
    "score_2", "winner", "decided_by_penalties", "notes",
]
if set(match_headers or []) != set(match_columns):
    raise ValueError("2026 matches CSV headers do not match: " + str(match_headers))

team_stats_headers, team_stats_rows = read_csv("data/wc2026_team_stats_combined.csv")
team_stats_columns = [
    "team", "goals", "assists", "attempts_at_goal", "attempts_on_target",
    "attempts_off_target", "attempts_at_goal_conversion_rate_pc",
    "attempts_inside_the_penalty_area", "attempts_outside_the_penalty_area",
    "headed_attempts_at_goal", "xg", "xg_efficiency", "corners",
    "possession_control_pc", "own_goals", "goals_conceded", "forced_turnovers",
    "ball_recovery_time", "defensive_pressures_applied",
    "defensive_pressures_directly_applied", "fouls_against", "fouls_for",
    "yellow_cards", "red_cards", "indirect_red_cards", "offsides", "passes",
    "passes_completed", "passing_accuracy_pc", "crosses", "crossing_accuracy_pc",
    "take_ons_completed", "defensive_line_breaks_attempted",
    "defensive_line_breaks_acc_pc", "switches_of_play_attempted",
    "switches_of_play_acc_pc", "clean_sheets", "goalkeeper_goals_conceded",
    "goalkeeper_saves", "goalkeeper_actions_inside_the_penalty_area",
    "goalkeeper_actions_outside_the_penalty_area", "offers_to_receive",
    "offers_in_behind", "offers_in_between", "offers_in_front",
    "offers_inside_team_shape", "offers_outside_team_shape",
    "receptions_in_behind", "receptions_between_midfield_and_defensive_line",
    "receptions_under_pressure", "average_speed", "high_speed_running",
    "sprints", "total_distance",
]
team_stats_csv_columns = [
    "Team", "Goals", "Assists", "AttemptsAtGoal", "AttemptsOnTarget",
    "AttemptsOffTarget", "AttemptsAtGoalConversionRatePC",
    "AttemptsInsideThePenaltyArea", "AttemptsOutsideThePenaltyArea",
    "HeadedAttemptsAtGoal", "xG", "xGEfficiency", "Corners",
    "PossessionControlPC", "OwnGoals", "GoalsConceded", "ForcedTurnovers",
    "BallRecoveryTime", "DefensivePressuresApplied",
    "DefensivePressuresDirectlyApplied", "FoulsAgainst", "FoulsFor",
    "YellowCards", "RedCards", "IndirectRedCards", "Offsides", "Passes",
    "PassesCompleted", "PassingAccuracyPC", "Crosses", "CrossingAccuracyPC",
    "TakeOnsCompleted", "DefensiveLineBreaksAttempted",
    "DefensiveLineBreaksAccPC", "SwitchesOfPlayAttempted",
    "SwitchesOfPlayAccPC", "CleanSheets", "GoalsCondeded",
    "GoalkeeperSaves", "GoalkeeperActionsInsideThePenaltyArea",
    "GoalkeeperActionsOutsideThePenaltyArea", "OffersToReceive",
    "OffersInBehind", "OffersInBetween", "OffersInFront",
    "OffersInsideTeamShape", "OffersOutsideTeamShape",
    "ReceptionsInBehind", "ReceptionsBetweenMidfieldAndDefensiveLine",
    "ReceptionsUnderPressure", "AverageSpeed", "HighSpeedRunning",
    "Sprints", "TotalDistance",
]
if team_stats_headers != team_stats_csv_columns:
    raise ValueError(
        "Team stats CSV headers do not match the table schema: "
        + str(team_stats_headers)
    )
team_stats_map = dict(zip(team_stats_headers, team_stats_columns))
team_stats_rows = [
    {team_stats_map[csv_column]: value for csv_column, value in row.items()}
    for row in team_stats_rows
]

player_headers, player_rows = read_csv("data/fifa_world_cup_2026_player_performance.csv")
player_columns = [
    "player_id", "player_name", "age", "nationality", "team", "jersey_number",
    "position", "height_cm", "weight_kg", "preferred_foot", "club_name",
    "market_value_eur", "match_id", "match_date", "stadium", "city",
    "opponent_team", "tournament_stage", "match_result", "goals_team",
    "goals_opponent", "minutes_played", "goals", "assists", "shots",
    "shots_on_target", "expected_goals_xg", "expected_assists_xa", "key_passes",
    "successful_passes", "total_passes", "pass_accuracy", "dribbles_attempted",
    "successful_dribbles", "crosses", "successful_crosses", "tackles",
    "interceptions", "clearances", "blocks", "aerial_duels_won",
    "aerial_duels_lost", "recoveries", "defensive_actions", "fouls_committed",
    "fouls_suffered", "yellow_cards", "red_cards", "offsides", "saves",
    "save_percentage", "punches", "clean_sheet", "goals_conceded",
    "penalty_saves", "distance_covered_km", "sprint_distance_km", "top_speed_kmh",
    "accelerations", "decelerations", "stamina_score", "player_rating",
    "performance_score", "offensive_contribution", "defensive_contribution",
    "possession_impact", "pressure_resistance", "creativity_score",
    "consistency_score", "clutch_performance_score", "total_goals_tournament",
    "total_assists_tournament", "total_minutes_tournament",
    "player_of_match_awards", "tournament_rating",
]
if set(player_headers or []) != set(player_columns):
    raise ValueError("Player performance CSV headers do not match the table schema")

for table in (
    "WorldCupRecords",
    "WorldCup2026Teams",
    "WorldCup2026Matches",
    "WorldCup2026TeamStats",
    "players",
):
    cursor.execute(f'DELETE FROM "{table}"')

# Insert rows into the tables from CSV files
insert_rows("WorldCupRecords", ["year", "team"], record_rows)
insert_rows("WorldCup2026Teams", team_columns, team_rows)
insert_rows("WorldCup2026Matches", match_columns, match_rows)
insert_rows("WorldCup2026TeamStats", team_stats_columns, team_stats_rows)
insert_rows("players", player_columns, player_rows)

# Check that all tables were successfully created
cursor.execute("SELECT * FROM WorldCupRecords LIMIT 5")
for row in cursor.fetchall():
    print(row)
    
cursor.execute("SELECT * FROM WorldCup2026Teams LIMIT 5")
for row in cursor.fetchall():
    print(row)

cursor.execute("SELECT * FROM WorldCup2026Matches LIMIT 5")
for row in cursor.fetchall():
    print(row)
    
cursor.execute("SELECT * FROM WorldCup2026TeamStats LIMIT 5")
for row in cursor.fetchall():
    print(row)

cursor.execute("SELECT * FROM players WHERE age>26 LIMIT 5")
for row in cursor.fetchall():
    print(row)

db.commit()
db.close()
