import duckdb
import time

db = duckdb.connect("soccer_database.duckdb")

TABLE = "players"


# Example 1: Analysis of DuckDB's expression rewriter optimization, comparing execution time with and without the expression rewriter optimizer

rewriter_disabled = db.sql("""
    SELECT string_agg(name, ',')
    FROM duckdb_optimizers()
    WHERE name != 'expression_rewriter'
""").fetchall()[0][0]

# Queries that test five different rewrite rules of DuckDB's expression rewriter
queries = {
    "1: Distributivity Rule": f"""
        SELECT count(*)
        FROM {TABLE}
        WHERE (nationality LIKE '%Brazil%' AND total_passes > 30 AND pass_accuracy > 0.85)
           OR (nationality LIKE '%Brazil%' AND goals >= 1)
    """,
    "2: Case Simplification Rule": f"""
        SELECT sum(
            CASE
                WHEN 4 = 4 THEN (tournament_rating * 10)
                ELSE ROUND(total_minutes_tournament / 90)::int
            END
        )
        FROM {TABLE}
    """,
    "3: Move Constants Rule": f"""
        SELECT position, AVG(player_rating)
        FROM {TABLE}
        WHERE (minutes_played * 2) + 10 >= 150 AND market_value_eur - 1000000 > 5000000
        GROUP BY position
    """,
    "4: Ordered Aggregate Optimizer Rule": f"""
        SELECT AVG(pass_accuracy ORDER BY successful_passes DESC)
        FROM {TABLE}
    """,
    "5: Regex Optimization Rule": f"""
        SELECT COUNT(*), SUM(goals)
        FROM {TABLE}
        WHERE REGEXP_MATCHES(player_name, '^Lio')
        OR REGEXP_MATCHES(team, 'land$')
    """,
}



def avg_ms(sql: str, runs: int = 20) -> float:
    db.execute(sql).fetchall()  # Warm-up run
    t0 = time.perf_counter()
    for _ in range(runs):
        db.execute(sql).fetchall()
    return ((time.perf_counter() - t0) / runs) * 1000

db.execute("PRAGMA explain_output = 'optimized_only';")

for rule_name, sql in queries.items():
    print("=" * 50)
    print(f"RULE {rule_name}")

    # Before: Disable expression_rewriter
    # db.execute("SET disabled_optimizers = 'expression_rewriter';")
    db.execute("PRAGMA disable_optimizer;")

    plan_before = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
    ms_before = avg_ms(sql)

    # After: Enable expression_rewriter (maybe also switch '' with all_except_rewriter to run it on its own??)
    # db.execute("SET disabled_optimizers = '';")
    db.execute("PRAGMA enable_optimizer;")
    db.execute(f"SET disabled_optimizers = '{rewriter_disabled}'")
    plan_after = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
    ms_after = avg_ms(sql)

    print(
        f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)"
    )
    print("\n[Plan BEFORE]")
    print(plan_before)
    print("\n[Plan AFTER]")
    print(plan_after)

# Example 2: Filter pullup/filter pushdown optimziation, comparing execution time with and without the filter pull and push optimizers
filter_disabled = db.sql("""
    SELECT string_agg(name, ',')
    FROM duckdb_optimizers()
    WHERE name != 'filter_pullup' AND name != 'filter_pushdown'
""").fetchall()[0][0]

queries = {
    "Filter Pullup/Pushdown Example 1: ": f"""
        SELECT p1.player_name, p1.position, p1.yellow_cards, p1.red_cards, p2.player_name AS scorer
        FROM {TABLE} p1
        JOIN (
            SELECT DISTINCT tournament_stage, player_name
            FROM {TABLE}
            WHERE team = 'Spain' OR team = 'Canada'
            AND goals > 0
        ) p2 ON p1.tournament_stage = p2.tournament_stage
        WHERE p1.team = 'Spain' OR p1.team = 'Canada'
    """,    
    "Filter Pullup/Pushdown Example 2: ": f"""
        SELECT f.player_name, p.match_id, p.minutes_played, f.goals
        FROM {TABLE} AS p
        JOIN {TABLE} AS f 
            ON p.player_id = f.player_id
        WHERE f.position = 'Forward'
            AND f.player_id BETWEEN 'P00050' AND 'P00180'
            AND p.tournament_stage = 'Group Stage'
    """,    
}

db.execute("PRAGMA explain_output = 'optimized_only';")

for rule_name, sql in queries.items():
    print("=" * 50)
    print(f"{rule_name}")

    # Before: Disable all optimizers
    db.execute("PRAGMA disable_optimizer;")
    plan_before = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
    ms_before = avg_ms(sql)

    # After: Enable pullup and pushdown optimizers
    db.execute("PRAGMA enable_optimizer;")
    db.execute(f"SET disabled_optimizers = '{filter_disabled}'")
    plan_after = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
    ms_after = avg_ms(sql)

    print(
        f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)"
    )
    print("\n[Plan BEFORE]")
    print(plan_before)
    print("\n[Plan AFTER]")
    print(plan_after)

# Example 3: Disable and re-enable all optimizers and run a query with each to see the effect on execution time
queries = {
    "All Optimizers Example 1: ": f"""
        SELECT player_name, goals
        FROM (
        SELECT *
        FROM {TABLE}
        ) AS all_cols
        WHERE team = 'Brazil'
    """,  
    "All Optimizers Example 2: ": f"""
        SELECT team, 
        AVG(offensive_contribution + defensive_contribution) AS avg_contribution
        FROM {TABLE}
        WHERE tournament_rating > 5.0 AND tournament_rating < 5.0
        GROUP BY team
        ORDER BY avg_contribution DESC
    """,   
    "All Optimizers Example 3: ": f"""
        SELECT p1.player_name, p2.match_id, p3.team
        FROM {TABLE} AS p1
        JOIN {TABLE} AS p2 
            ON p1.match_id = p2.match_id
        JOIN (
            SELECT DISTINCT team
            FROM {TABLE}
            WHERE team = 'Canada'
        ) AS p3 ON p2.team = p3.team;
    """,  
}


for rule_name, sql in queries.items():
    print("=" * 50)
    print(f"{rule_name}")

    # Before: All optimizers disabled
    db.execute("PRAGMA disable_optimizer;")
    plan_before = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
    ms_before = avg_ms(sql)

    # After: All optimizers enabled
    db.execute("PRAGMA enable_optimizer;")
    plan_after = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
    ms_after = avg_ms(sql)

    print(
        f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)"
    )
    print("\n[Plan BEFORE]")
    print(plan_before)
    print("\n[Plan AFTER]")
    print(plan_after)