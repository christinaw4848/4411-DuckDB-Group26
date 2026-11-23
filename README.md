# 4411-DuckDB-Group26
We are performing a system analysis of DuckDB, a database management system. We created a small soccer-centred database to explore and evaluate some of its unique tools and features, including the following:
* Column-oriented storage manager
* Query optimizer
* Vectorized execution engine
* Indexing methods (min-max index and adaptive radix tree)
* Integration with CSV files

We also compare DuckDB to another relational database management system, SQLite, in a case study to highlight the advantages and disadvantages of each system, the primary uses for each and their contrasting workloads, and how their tools and features compare.

The following datasets and sources were used for the indicated CSV files that our database is built on:
* 2026WCmatches.csv: https://www.kaggle.com/datasets/mann14/2026-fifa-world-cup/data
* 2026WCteams.csv: https://www.kaggle.com/datasets/mann14/2026-fifa-world-cup/data
* fifa_world_cup_2026_player_performance.csv: https://www.kaggle.com/datasets/rauffauzanrambe/fifa-world-cup-2026-player-performance-dataset 
* wc_records.csv: https://www.foxsports.com/soccer/fifa-world-cup/history 
* wc2026_team_stats_combined.csv: https://www.kaggle.com/datasets/colinc88/fifa-world-cup-2026-complete-team-statistics


Run
```
pip install -r requirements.txt
```
to ensure all dependencies are installed before running the code.

Run 
```
python duckdb_data.py
```
to make sure the database tables are created correctly.
