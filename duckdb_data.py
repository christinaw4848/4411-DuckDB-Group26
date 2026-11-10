
import duckdb

db = duckdb.connect("soccer_database.duckdb")

# Create tables from CSVs

db.sql("CREATE TABLE IF NOT EXISTS WorldCupRecords AS SELECT * FROM read_csv('data/wc_records.csv');")
db.sql("SELECT * FROM WorldCupRecords LIMIT 5").show() # Check if the table was created successfully

db.sql("CREATE TABLE IF NOT EXISTS WorldCup2026Teams AS SELECT * FROM read_csv('data/2026WCteams.csv');")
db.sql("SELECT * FROM WorldCup2026Teams LIMIT 5").show() # Check if the table was created successfully

db.sql("CREATE TABLE IF NOT EXISTS WorldCup2026Matches AS SELECT * FROM read_csv('data/2026WCmatches.csv');")
db.sql("SELECT * FROM WorldCup2026Matches LIMIT 5").show() # Check if the table was created successfully

"""
base_path = "data/team_stats/"
files = [
    "wc2026_team_attacking.csv",
    "wc2026_team_defending.csv",
    "wc2026_team_discipline.csv",
    "wc2026_team_distribution.csv",
    "wc2026_team_goalkeeping.csv",
    "wc2026_team_movement.csv",
    "wc2026_team_physical.csv",
]
output_csv = f"{base_path}wc2026_team_stats_combined.csv"

# Initialize query string with first file and its alias
join_query = f"FROM read_csv('{base_path}{files[0]}') AS t0"

# Loop through remaining files and add a unique alias to each
for idx, file in enumerate(files[1:], start=1):
    join_query += f" NATURAL JOIN read_csv('{base_path}{file}') AS t{idx}"

# Export the joined data to new CSV file
db.execute(f"COPY (SELECT * {join_query}) TO '{output_csv}' (HEADER, DELIMITER ',');")
print(f"Successfully generated combined master file at: {output_csv}")
"""

db.sql("CREATE TABLE IF NOT EXISTS WorldCup2026TeamStats AS SELECT * FROM read_csv('data/wc2026_team_stats_combined.csv');")
db.sql("SELECT * FROM WorldCup2026TeamStats LIMIT 5").show() # Check if the table was created successfully



db.sql("CREATE TABLE IF NOT EXISTS players AS SELECT * FROM read_csv('data/fifa_world_cup_2026_player_performance.csv');")
db.sql("SELECT * FROM players WHERE age>26 LIMIT 5").show()
       

db.close()
