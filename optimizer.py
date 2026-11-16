import duckdb
import time

db = duckdb.connect("soccer_database.duckdb")


rel = db.table("players")

for col, dtype in zip(rel.columns, rel.dtypes):
    print(f"{col}: {dtype}")

TABLE = "players"


# Example 1: Analysis of DuckDB's expression rewriter optimization, comparing execution time with and without the expression rewriter optimizer

rewriter_disabled = db.sql("""
    SELECT string_agg(name, ',')
    FROM duckdb_optimizers()
    WHERE name != 'expression_rewriter'
""").fetchone()

# Queries that test five different rewrite rules of DuckDB's expression rewriter
queries = {
      "1: Distributivity Rule": f"""
        SELECT count(*)
        FROM {TABLE}
        WHERE (nationality LIKE '%Brazil%' AND total_passes > 30 AND pass_accuracy > 0.85)
           OR (nationality LIKE '%Brazil%' AND goals >= 1)
    """,

}

# db.execute(f"SET disabled_optimizers = '{disabled}'")
# db.execute("PRAGMA explain_output = 'optimized_only'")
# print(db.sql("EXPLAIN SELECT 2 + 2").fetchone()[1])



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
    db.execute("SET disabled_optimizers = 'expression_rewriter';")
    plan_before = db.sql(f"EXPLAIN {sql}").fetchone()
    ms_before = avg_ms(sql)

    # After: Enable expression_rewriter (maybe also switch '' with all_except_rewriter to run it on its own??)
    db.execute("SET disabled_optimizers = '';")
    plan_after = db.sql(f"EXPLAIN {sql}").fetchone()
    ms_after = avg_ms(sql)

    print(f"Time BEFORE: {ms_before:6.2f} ms | Time AFTER: {ms_after:6.2f} ms ({ms_before / ms_after:.2f}x)")
    print("\n[Plan BEFORE]")
    print(plan_before.strip())
    print("\n[Plan AFTER]")
    print(plan_after.strip())