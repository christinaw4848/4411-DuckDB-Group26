import duckdb
import time
import json
import os
import tempfile

TABLE = "players"

def get_all_optimizers_except(db: duckdb.DuckDBPyConnection, allowed: list[str]) -> str:
    if not allowed:
        return db.sql("SELECT string_agg(name, ',') FROM duckdb_optimizers()").fetchall()[0][0]
    allowed_str = ", ".join(f"'{opt}'" for opt in allowed)
    return db.sql(f"""
        SELECT string_agg(name, ',')
        FROM duckdb_optimizers()
        WHERE name NOT IN ({allowed_str})
    """).fetchall()[0][0]
    
def performance_analysis(sql: str, enabled_optimizers, runs: int = 10) -> dict:
    db = duckdb.connect("soccer_database.duckdb", read_only=True)

    # Configure optimizers
    db.execute("PRAGMA enable_optimizer;")
    db.execute("SET disabled_optimizers = '';")  # Reset to default
    if enabled_optimizers == "NONE":
         db.execute("PRAGMA disable_optimizer;")
    elif enabled_optimizers != "ALL":
        disabled_optimizers = get_all_optimizers_except(db, enabled_optimizers)
        db.execute(f"SET disabled_optimizers = '{disabled_optimizers}';")

    db.execute("PRAGMA explain_output = 'optimized_only';")    
    plan = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]

    # Measure execution time
    db.execute(sql).fetchall()  # Warm-up run
    t0 = time.perf_counter()
    for _ in range(runs):
        db.execute(sql).fetchall()
    avg_ms = ((time.perf_counter() - t0) / runs) * 1000
    
    # Measure resource usage
    fd, profile_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        db.execute("PRAGMA enable_profiling = 'json';")
        db.execute("PRAGMA profiling_mode = 'detailed';")
        db.execute(f"PRAGMA profiling_output = '{profile_path}';")
        
        db.execute(sql).fetchall()
        db.execute("PRAGMA disable_profiling;")
        
        with open(profile_path, "r") as f:
            raw_prof = json.load(f)
    finally:
        if os.path.exists(profile_path):
            os.remove(profile_path)

    # Helper to safely extract metrics
    def get_metric(node, key_names, agg="max"):
        vals = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in key_names and isinstance(v, (int, float)):
                    vals.append(v)
                elif isinstance(v, (dict, list)):
                    sub = get_metric(v, key_names, agg)
                    if sub is not None:
                        vals.append(sub)
        elif isinstance(node, list):
            for item in node:
                sub = get_metric(item, key_names, agg)
                if sub is not None:
                    vals.append(sub)
        if not vals:
            return 0
        return sum(vals) if agg == "sum" else max(vals)

    peak_mem = get_metric(
        raw_prof,
        {"system_peak_buffer_memory", "total_memory_allocated", "peak_memory"},
        agg="max",
    )
    temp_disk = get_metric(
        raw_prof,
        {"system_peak_temp_dir_size", "temp_dir_size"},
        agg="max",
    )
    intermediate_rows = get_metric(
        raw_prof,
        {"intermediate_rows"},
        agg="sum",
    )

    db.close()
    
    return {
        "plan": plan,
        "ms": avg_ms,
        "peak_mem_mb": peak_mem / (1024 * 1024),
        "temp_disk_mb": temp_disk / (1024 * 1024),
        "intermediate_rows": int(intermediate_rows),
    }


def print_results(title: str, sql: str, after_optimizers):
    print("=" * 50)
    print(f"Test: {title}")
    
    before = performance_analysis(sql, enabled_optimizers="NONE")
    after = performance_analysis(sql, enabled_optimizers=after_optimizers)

    print(f"{'Metric':<24} | {'BEFORE (Off)':<15} | {'AFTER (On)':<15} | {'Change'}")
    print("-" * 72)
    print(f"{'Average Latency (ms)':<24} | {before['ms']:>15.2f} | {after['ms']:>15.2f} | {before['ms']/max(after['ms'], 1e-6):.2f}x faster")
    
    buffer = after['peak_mem_mb'] - before['peak_mem_mb']
    if buffer != 0:
        print(f"{'Peak Buffer Memory (MB)':<24} | {before['peak_mem_mb']:>15.2f} | {after['peak_mem_mb']:>15.2f} | {after['peak_mem_mb'] - before['peak_mem_mb']:+.2f} MB")
    
    spill = after['temp_disk_mb'] - before['temp_disk_mb']
    if spill != 0:
        print(f"{'Temp Disk Spill (MB)':<24} | {before['temp_disk_mb']:>15.2f} | {after['temp_disk_mb']:>15.2f} | {after['temp_disk_mb'] - before['temp_disk_mb']:+.2f} MB")
    
    rows = before['intermediate_rows'] - after['intermediate_rows']
    if rows != 0:
        print(f"{'Intermediate Rows':<24} | {before['intermediate_rows']:>15,d} | {after['intermediate_rows']:>15,d} | {before['intermediate_rows'] - after['intermediate_rows']:-,d}")
    
    print("\n[Plan BEFORE]")
    print(before["plan"])
    print("\n[Plan AFTER]")
    print(after["plan"])


# Example 1: Analysis of DuckDB's expression rewriter optimization, comparing execution time with and without the expression rewriter optimizer

# Queries that test five different rewrite rules of DuckDB's expression rewriter
queries = {
    "1: Distributivity Rule": f"""
        SELECT count(*)
        FROM {TABLE} AS p1
        JOIN {TABLE} AS p2 ON p1.match_id = p2.match_id
        WHERE (
            REGEXP_MATCHES(REPEAT(CAST(p1.nationality AS VARCHAR), 20), '.*Brazil.*')
            AND p1.total_passes > 30 
            AND p2.pass_accuracy > 0.85
        )
        OR (
            REGEXP_MATCHES(REPEAT(CAST(p1.nationality AS VARCHAR), 20), '.*Brazil.*')
            AND p1.goals >= 1
        )
    """,
    "2: Case Simplification Rule": f"""
        SELECT sum(
            CASE
                WHEN 4 = 5 THEN LENGTH(UPPER(LOWER(REVERSE(REPEAT(CAST(p1.player_name AS VARCHAR), 80)))))
                ELSE (p1.tournament_rating * 10)
            END
        )
        FROM {TABLE} AS p1
        JOIN {TABLE} AS p2 ON p1.match_id = p2.match_id
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

for name, sql in queries.items():
    print_results(name, sql, after_optimizers=["expression_rewriter"])

# db.execute("PRAGMA explain_output = 'optimized_only';")

# for rule_name, sql in queries.items():
#     print("=" * 50)
#     print(f"RULE {rule_name}")

#     # Before: Disable expression_rewriter
#     # db.execute("SET disabled_optimizers = 'expression_rewriter';")
#     db.execute("PRAGMA disable_optimizer;")

#     plan_before = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
#     ms_before = avg_ms(sql)

#     # After: Enable expression_rewriter (maybe also switch '' with all_except_rewriter to run it on its own??)
#     # db.execute("SET disabled_optimizers = '';")
#     db.execute("PRAGMA enable_optimizer;")
#     db.execute(f"SET disabled_optimizers = '{rewriter_disabled}'")
#     plan_after = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
#     ms_after = avg_ms(sql)

#     print(
#         f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)"
#     )
#     print("\n[Plan BEFORE]")
#     print(plan_before)
#     print("\n[Plan AFTER]")
#     print(plan_after)

# Example 2: Filter pullup/filter pushdown optimziation, comparing execution time with and without the filter pull and push optimizers
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

for name, sql in queries.items():
    print_results(name, sql, after_optimizers=["filter_pullup", "filter_pushdown"])


# db.execute("PRAGMA explain_output = 'optimized_only';")

# for rule_name, sql in queries.items():
#     print("=" * 50)
#     print(f"{rule_name}")

#     # Before: Disable all optimizers
#     db.execute("PRAGMA disable_optimizer;")
#     plan_before = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
#     ms_before = avg_ms(sql)

#     # After: Enable pullup and pushdown optimizers
#     db.execute("PRAGMA enable_optimizer;")
#     db.execute(f"SET disabled_optimizers = '{filter_disabled}'")
#     plan_after = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
#     ms_after = avg_ms(sql)

#     print(
#         f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)"
#     )
#     print("\n[Plan BEFORE]")
#     print(plan_before)
#     print("\n[Plan AFTER]")
#     print(plan_after)


# Example 3: Join reordering optimization
queries = {
    "Join Reordering Example: ": f"""
    SELECT COUNT(*)
    FROM {TABLE} AS p1
    JOIN {TABLE} AS p2 
        ON p1.team = p2.team
        AND p1.tournament_stage = p2.tournament_stage
    JOIN (SELECT player_id FROM {TABLE} LIMIT 5) AS p3 
        ON p2.player_id = p3.player_id
    """,
}

for name, sql in queries.items():
    print_results(name, sql, after_optimizers=["join_order"])


# Example 4: Disable and re-enable all optimizers and run a query with each to see the effect on execution time
queries = {
    "All Optimizers Example 1: ": f"""
        SELECT player_name, goals
        FROM (
            SELECT player_name, goals, team,
            LENGTH(UPPER(LOWER(REVERSE(REPEAT(CAST(player_name AS VARCHAR), 150))))) AS clean_name
        FROM {TABLE}
        ) AS all_cols
    WHERE team = 'Brazil'
    """,  
    "All Optimizers Example 2: ": f"""
        SELECT p1.team, 
        AVG(p1.offensive_contribution + p1.defensive_contribution) AS avg_contribution
        FROM {TABLE} AS p1
        JOIN {TABLE} AS p2 ON p1.player_id = p2.player_id
        WHERE p1.tournament_rating > 5.0 AND p1.tournament_rating < 5.0
        GROUP BY p1.team
        ORDER BY avg_contribution DESC
    """,   
    "All Optimizers Example 3: ": f"""
        SELECT p1.player_name, p2.match_id, p3.team
        FROM {TABLE} AS p1
        LEFT JOIN {TABLE} AS p2 
            ON p1.match_id = p2.match_id
        JOIN (
            SELECT DISTINCT team
            FROM {TABLE}
            WHERE team = 'Canada'
        ) AS p3 ON p2.team = p3.team;
    """,  
}

for name, sql in queries.items():
    print_results(name, sql, after_optimizers="ALL")


# for rule_name, sql in queries.items():
#     print("=" * 50)
#     print(f"{rule_name}")

#     # Before: All optimizers disabled
#     db.execute("PRAGMA disable_optimizer;")
#     plan_before = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
#     ms_before = avg_ms(sql)

#     # After: All optimizers enabled
#     db.execute("PRAGMA enable_optimizer;")
#     plan_after = db.sql(f"EXPLAIN {sql}").fetchall()[0][1]
#     ms_after = avg_ms(sql)

#     print(
#         f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)"
#     )
#     print("\n[Plan BEFORE]")
#     print(plan_before)
#     print("\n[Plan AFTER]")
#     print(plan_after)