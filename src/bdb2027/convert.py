"""Convert the nine competition CSVs to Parquet.

Run:  python -m bdb2027.convert

Run against the real files on 2026-11-06: all nine converted and the row
counts matched the forum-reported ones. Some inferred dtypes differ from the
data dictionary (e.g. the NGS scores and pass_length come out as integers).

Null handling:
- "NA" is read as missing in every column EXCEPT player_play.lined_up_position,
  where the literal string "NA" marks a play killed by a pre-snap penalty
  (host, discussion 747108). It is kept as the string "NA" there.
- player_play.pass_result is a quoted "" in the raw CSV on non-dropback plays,
  and that survives as the empty string (never null) in Parquet. The host's
  dropback filter is therefore `pass_result != ""` here too (103,636 rows are
  empty). Other empty fields do become null.
"""

from __future__ import annotations

import csv
import sys
import time

import polars as pl

from . import paths

# Columns where the string "NA" is a real value, not a missing marker.
LITERAL_NA_COLUMNS = {"player_play": {"lined_up_position"}}

# Large files: give explicit dtypes instead of scanning every row to infer them.
GAME_TRACKING_SCHEMA = {
    "game_id": pl.Int64,
    "play_id": pl.Int64,
    "nfl_id": pl.Int64,
    "x": pl.Float64,
    "y": pl.Float64,
    "s": pl.Float64,
    "a": pl.Float64,
    "dis": pl.Float64,
    "o": pl.Float64,
    "dir": pl.Float64,
    "event": pl.String,
}

# Row counts reported in the forum (discussions 747108, 747584). Used as a
# sanity check only: a mismatch prints a warning.
EXPECTED_ROWS = {
    "combine_tracking": 463_189,
    "player_play": 314_197,
    "game_tracking_2023": 3_665_443,
    "game_tracking_2024": 7_827_944,
    "game_tracking_2025": 11_160_903,
}


def _header(path) -> list[str]:
    # utf-8-sig strips a byte-order mark if the file has one.
    with open(path, newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f))


def convert(table: str) -> None:
    src = paths.raw_csv(table)
    dst = paths.parquet(table)
    columns = _header(src)
    keep_literal = LITERAL_NA_COLUMNS.get(table, set())
    null_values = {c: "NA" for c in columns if c not in keep_literal}

    is_game_tracking = table.startswith("game_tracking_")
    lf = pl.scan_csv(
        src,
        null_values=null_values,
        schema_overrides=GAME_TRACKING_SCHEMA if is_game_tracking else None,
        infer_schema_length=10_000 if is_game_tracking else None,
        try_parse_dates=True,
    )

    start = time.time()
    dst.parent.mkdir(parents=True, exist_ok=True)
    lf.sink_parquet(dst, compression="zstd")

    out = pl.scan_parquet(dst)
    n = out.select(pl.len()).collect().item()
    print(f"\n{table}: {n:,} rows -> {dst.name} ({time.time() - start:.1f}s)")
    for name, dtype in out.collect_schema().items():
        print(f"    {name}: {dtype}")
    expected = EXPECTED_ROWS.get(table)
    if expected is not None and n != expected:
        print(f"    WARNING: expected {expected:,} rows (forum-reported count)")


def main() -> int:
    missing = [t for t in paths.TABLES if not paths.raw_csv(t).exists()]
    if missing:
        print(f"Missing CSVs in {paths.RAW_DIR}:")
        for t in missing:
            print(f"    {t}.csv")
        return 1
    for table in paths.TABLES:
        convert(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
