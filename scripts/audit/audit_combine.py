"""Audit of the Combine-side data (players, combine_results, combine_tracking).

Run from the repo root:  .venv\\Scripts\\python.exe scripts\\audit\\audit_combine.py
Writes reports/audit_combine.md. Only aggregates are written (no raw rows beyond tiny examples).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

from bdb2027 import paths

REPO = paths.REPO_ROOT
REPORT = REPO / "reports" / "audit_combine.md"
DT = 0.1                      # nominal sampling interval (s)
MOVE_THR = 0.5                # yd/s: "moving" threshold used for onset / stationary time
FIELD_X, FIELD_Y = 120.0, 53.333
TESTS = ["ten_yd_split", "forty", "vertical", "broad_jump", "three_cone", "short_shuttle", "bench_reps"]
MEAS = ["combine_height", "combine_weight", "hand_size", "arm_length", "wing_span"]
NGS = ["ngs_athleticism_score", "ngs_college_production_score", "ngs_final_score"]

OUT: list[str] = []


# ----------------------------------------------------------------------------- helpers
def h(level: int, text: str) -> None:
    OUT.append("\n" + "#" * level + " " + text + "\n")


def p(text: str = "") -> None:
    OUT.append(text + "\n")


def _fmt(v, nd=2):
    if v is None:
        return ""
    if isinstance(v, float):
        if v != v:
            return "nan"
        return f"{v:.{nd}f}"
    return str(v).replace("|", "/")


def tbl(df: pl.DataFrame, nd: int = 2) -> None:
    cols = df.columns
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.iter_rows():
        lines.append("| " + " | ".join(_fmt(v, nd) for v in r) + " |")
    OUT.append("\n".join(lines) + "\n")


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def q(col: str, qs=(0.25, 0.5, 0.75)):
    return [pl.col(col).quantile(v).alias(f"{col}_p{int(v * 100)}") for v in qs]


# ----------------------------------------------------------------------------- load
players = pl.read_parquet(paths.parquet("players"))
cr = pl.read_parquet(paths.parquet("combine_results"))
trk = pl.read_parquet(paths.parquet("combine_tracking")).with_row_index("row")
P = trk.filter(pl.col("entity_type") == "PLAYER")
B = trk.filter(pl.col("entity_type") == "BALL")

# one row per player with both position labels
pp = players.select("nfl_id", "display_name", "draft_year", "nfl_position", "draft_round", "draft_overall_pick").join(
    cr.select("nfl_id", pl.col("draft_year").alias("cr_draft_year"), "combine_position"), on="nfl_id", how="left"
)

# ----------------------------------------------------------------------------- per-frame table
F = P.sort("event_id", "time", "row", maintain_order=True).with_columns(
    pl.col("time").diff().over("event_id").dt.total_microseconds().alias("dt_us"),
    pl.col("x").diff().over("event_id").alias("dx"),
    pl.col("y").diff().over("event_id").alias("dy"),
    pl.int_range(pl.len()).over("event_id").alias("i"),
    pl.len().over("event_id").alias("n"),
)
F = F.with_columns(((pl.col("dx") ** 2 + pl.col("dy") ** 2).sqrt()).alias("step"))
F = F.with_columns(
    pl.col("step").shift(-1).over("event_id").alias("step_next"),
    pl.col("s").shift(1).over("event_id").alias("s_prev"),
    pl.col("s").shift(-1).over("event_id").alias("s_next"),
    (pl.col("x").shift(-1).over("event_id") - pl.col("x").shift(1).over("event_id")).alias("cdx"),
    (pl.col("y").shift(-1).over("event_id") - pl.col("y").shift(1).over("event_id")).alias("cdy"),
    pl.col("dt_us").shift(-1).over("event_id").alias("dt_next_us"),
)

# ----------------------------------------------------------------------------- per-attempt table
A = F.group_by("event_id").agg(
    pl.col("draft_year").first().alias("draft_year"),
    pl.col("nfl_id").first().alias("nfl_id"),
    pl.col("nfl_id").n_unique().alias("n_ids"),
    pl.col("drill_type").first().alias("drill_type"),
    pl.col("drill_type").n_unique().alias("n_dtype"),
    pl.col("drill_name").first().alias("drill_name"),
    pl.col("drill_name").n_unique().alias("n_dname"),
    pl.col("attempt").first().alias("attempt"),
    pl.col("attempt").n_unique().alias("n_att"),
    pl.col("draft_year").n_unique().alias("n_year"),
    pl.len().alias("frames"),
    pl.col("time").min().alias("t0"),
    pl.col("time").max().alias("t1"),
    pl.col("dis").sum().alias("sum_dis"),
    pl.col("step").sum().alias("sum_xy"),
    (pl.col("s").sum() * DT).alias("sum_s"),
    pl.col("x").first().alias("x_first"),
    pl.col("y").first().alias("y_first"),
    pl.col("x").last().alias("x_last"),
    pl.col("y").last().alias("y_last"),
    pl.col("x").min().alias("x_min"),
    pl.col("x").max().alias("x_max"),
    pl.col("y").min().alias("y_min"),
    pl.col("y").max().alias("y_max"),
    pl.col("step").max().alias("step_max"),
    pl.col("i").filter(pl.col("s") >= MOVE_THR).min().alias("first_move"),
    pl.col("i").filter(pl.col("s") >= MOVE_THR).max().alias("last_move"),
    (pl.col("s").first() >= MOVE_THR).alias("starts_moving"),
).with_columns(
    ((pl.col("t1") - pl.col("t0")).dt.total_microseconds() / 1e6).alias("dur"),
    (pl.col("first_move") * DT).alias("lead_s"),
    ((pl.col("frames") - 1 - pl.col("last_move")) * DT).alias("trail_s"),
    ((pl.col("x_last") - pl.col("x_first")) ** 2 + (pl.col("y_last") - pl.col("y_first")) ** 2).sqrt().alias("net_disp"),
)
A = A.join(pp.select("nfl_id", "nfl_position", "combine_position"), on="nfl_id", how="left")
N_EVENTS = A.height

POS_ORDER = ["WR", "TE", "OL", "DL", "DB"]


def canon(name: str) -> str:
    """Map clear renames between years onto one canonical drill_name (used only for cross-year pooling)."""
    return {
        "LINE": "LINE_DRILL",
        "PASS_PRO_MIRROR_DRILL": "PASS_PRO-MIRROR_DRILL",
        "OVER_THE_SHOULDER_ADJUST": "OVER_SHOULDER_ADJUST",
        "SPEED_OUT_LEFT": "SPEED_OUT_ROUTE_LEFT",
    }.get(name, name)


A = A.with_columns(pl.col("drill_name").map_elements(canon, return_dtype=pl.String).alias("drill_canon"))


# ============================================================================= A. cohort
def sec_A():
    h(2, "A. Cohort")
    p(f"players rows: {players.height}; distinct nfl_id: {players['nfl_id'].n_unique()}. "
      f"combine_results rows: {cr.height}; distinct nfl_id: {cr['nfl_id'].n_unique()}. "
      f"Distinct nfl_id in PLAYER tracking: {P['nfl_id'].n_unique()}.")
    h(3, "A1. nfl_position x draft_year (players table)")
    t = players.group_by("nfl_position", "draft_year").len().pivot(on="draft_year", index="nfl_position", values="len").fill_null(0)
    t = t.select("nfl_position", *sorted([c for c in t.columns if c != "nfl_position"])).with_columns(
        pl.sum_horizontal(pl.exclude("nfl_position")).alias("total")).sort("total", descending=True)
    tbl(t)
    h(3, "A2. combine_position x draft_year (combine_results)")
    t = cr.group_by("combine_position", "draft_year").len().pivot(on="draft_year", index="combine_position", values="len").fill_null(0)
    t = t.select("combine_position", *sorted([c for c in t.columns if c != "combine_position"])).with_columns(
        pl.sum_horizontal(pl.exclude("combine_position")).alias("total")).sort("total", descending=True)
    tbl(t)
    h(3, "A3. Mismatch checks players vs combine_results vs tracking")
    ids_p, ids_c, ids_t = set(players["nfl_id"]), set(cr["nfl_id"]), set(P["nfl_id"])
    ids_b = set(B["nfl_id"])
    j = players.select("nfl_id", pl.col("draft_year").alias("py")).join(cr.select("nfl_id", pl.col("draft_year").alias("cy")), on="nfl_id")
    ty = P.group_by("nfl_id").agg(pl.col("draft_year").n_unique().alias("n_years"), pl.col("draft_year").first().alias("ty"))
    jt = players.select("nfl_id", pl.col("draft_year").alias("py")).join(ty, on="nfl_id")
    p(f"- in players not in combine_results: {len(ids_p - ids_c)}; in combine_results not in players: {len(ids_c - ids_p)}")
    p(f"- in tracking(PLAYER) not in players: {len(ids_t - ids_p)}; players with no PLAYER tracking: {len(ids_p - ids_t)}")
    p(f"- BALL-row nfl_ids not in players: {len(ids_b - ids_p)}")
    p(f"- draft_year differs players vs combine_results: {j.filter(pl.col('py') != pl.col('cy')).height} of {j.height}")
    p(f"- draft_year differs players vs tracking: {jt.filter(pl.col('py') != pl.col('ty')).height}; players with >1 draft_year in tracking: {jt.filter(pl.col('n_years') > 1).height}")
    p(f"- duplicate nfl_id in players: {players.height - players['nfl_id'].n_unique()}; in combine_results: {cr.height - cr['nfl_id'].n_unique()}")
    p(f"- null combine_position: {cr['combine_position'].null_count()}; null nfl_position: {players['nfl_position'].null_count()}")
    h(3, "A4. nfl_position (rows) x combine_position (cols), player counts")
    t = pp.group_by("nfl_position", "combine_position").len().pivot(on="combine_position", index="nfl_position", values="len").fill_null(0)
    cols = [c for c in POS_ORDER if c in t.columns] + [c for c in t.columns if c not in POS_ORDER + ["nfl_position"]]
    tbl(t.select("nfl_position", *cols).sort("nfl_position"))
    h(3, "A5. Drafted vs undrafted, by combine_position")
    t = pp.group_by("combine_position").agg(
        pl.len().alias("players"),
        pl.col("draft_overall_pick").is_not_null().sum().alias("drafted"),
        pl.col("draft_overall_pick").is_null().sum().alias("undrafted"),
        *[(pl.col("draft_round") == r).sum().alias(f"R{r}") for r in range(1, 8)],
        pl.col("draft_overall_pick").median().alias("median_pick"),
    ).sort("players", descending=True)
    tbl(t)
    p("By nfl_position:")
    t = pp.group_by("nfl_position").agg(
        pl.len().alias("players"),
        pl.col("draft_overall_pick").is_not_null().sum().alias("drafted"),
        pl.col("draft_overall_pick").is_null().sum().alias("undrafted"),
        *[(pl.col("draft_round") == r).sum().alias(f"R{r}") for r in range(1, 8)],
    ).sort("players", descending=True)
    tbl(t)
    p(f"Sanity: draft_round null count {players['draft_round'].null_count()} vs draft_overall_pick null {players['draft_overall_pick'].null_count()}; "
      f"max draft_round {players['draft_round'].max()}.")
    t = pp.group_by("draft_year").agg(pl.len().alias("players"), pl.col("draft_overall_pick").is_null().sum().alias("undrafted"))
    tbl(t.sort("draft_year"))


# ============================================================================= B. opt-outs
def sec_B():
    h(2, "B. Opt-outs (share of players with a non-null value)")
    cols = MEAS + TESTS + NGS
    overall = pl.DataFrame({"column": cols, "non_null_share": [1 - cr[c].null_count() / cr.height for c in cols],
                            "non_null_n": [cr.height - cr[c].null_count() for c in cols]})
    tbl(overall, 3)
    p("By combine_position (non-null share; n in the header row of the next table):")
    t = cr.group_by("combine_position").agg(pl.len().alias("n"), *[pl.col(c).is_not_null().mean().alias(c) for c in cols]).sort("n", descending=True)
    tbl(t, 2)
    p("By draft_year (non-null share):")
    t = cr.group_by("draft_year").agg(pl.len().alias("n"), *[pl.col(c).is_not_null().mean().alias(c) for c in cols]).sort("draft_year")
    tbl(t, 2)
    p("Number of the 7 physical tests (ten_yd_split, forty, vertical, broad_jump, three_cone, short_shuttle, bench_reps) completed, distribution:")
    k = cr.with_columns(pl.sum_horizontal([pl.col(c).is_not_null().cast(pl.Int32) for c in TESTS]).alias("k"))
    tbl(k.group_by("k").len().sort("k"))
    p("Joint pattern: forty present but ten_yd_split missing, or the reverse: "
      f"{cr.filter(pl.col('forty').is_not_null() & pl.col('ten_yd_split').is_null()).height} / "
      f"{cr.filter(pl.col('forty').is_null() & pl.col('ten_yd_split').is_not_null()).height}.")


# ============================================================================= C. drill inventory
def comp_str(df: pl.DataFrame, col: str) -> pl.DataFrame:
    return df


def sec_C():
    h(2, "C. Drill inventory (PLAYER rows)")
    p("Position labels below are combine_position of the athlete (from combine_results). Attempts/player columns: number of players with exactly 1, 2, 3, 4+ attempts of that drill_name. "
      "median_dur_s = last minus first timestamp; median_frames = rows per attempt. Raw drill_name strings are used (they change between years, see C2).")
    # per player-drill attempt counts
    pdc = A.group_by("draft_year", "drill_type", "drill_name", "nfl_id").agg(pl.len().alias("k"), pl.col("combine_position").first().alias("cp"))
    for dtype in sorted(A["drill_type"].unique().to_list()):
        h(3, f"C1. {dtype}")
        sub = A.filter(pl.col("drill_type") == dtype)
        base = sub.group_by("drill_name", "draft_year").agg(
            pl.len().alias("attempts"),
            pl.col("nfl_id").n_unique().alias("players"),
            pl.col("dur").median().alias("median_dur_s"),
            pl.col("frames").median().alias("median_frames"),
        )
        dist = pdc.filter(pl.col("drill_type") == dtype).group_by("drill_name", "draft_year").agg(
            (pl.col("k") == 1).sum().alias("p_1"), (pl.col("k") == 2).sum().alias("p_2"),
            (pl.col("k") == 3).sum().alias("p_3"), (pl.col("k") >= 4).sum().alias("p_4plus"),
            pl.col("k").max().alias("max_att"),
        )
        pos = pdc.filter(pl.col("drill_type") == dtype).group_by("drill_name", "draft_year", "cp").len().sort("len", descending=True).group_by(
            ["drill_name", "draft_year"], maintain_order=True).agg(
            pl.concat_str([pl.col("cp").fill_null("?"), pl.lit(":"), pl.col("len").cast(pl.String)]).str.join(", ").alias("positions"))
        t = base.join(dist, on=["drill_name", "draft_year"]).join(pos, on=["drill_name", "draft_year"]).sort("drill_name", "draft_year")
        tbl(t, 2)

    h(3, "C2. Drill availability and naming across draft years (attempts per drill_name; blank = absent)")
    t = A.group_by("drill_type", "drill_name", "draft_year").len().pivot(on="draft_year", index=["drill_type", "drill_name"], values="len")
    t = t.select("drill_type", "drill_name", *[c for c in ["2023", "2024", "2025"] if c in t.columns]).sort("drill_type", "drill_name")
    t = t.with_columns(pl.sum_horizontal([pl.col(c).is_not_null().cast(pl.Int32) for c in ["2023", "2024", "2025"]]).alias("years_present"))
    tbl(t.with_columns(pl.when(pl.col("years_present") < 3).then(pl.lit("NOT IN ALL 3 YEARS")).otherwise(pl.lit("")).alias("flag")))
    p("Likely renames (same drill, different string): LINE (2023) -> LINE_DRILL (2024-25); PASS_PRO_MIRROR_DRILL (2023) -> PASS_PRO-MIRROR_DRILL (2024-25); "
      "OVER_THE_SHOULDER_ADJUST (2023 TE) -> OVER_SHOULDER_ADJUST (2024-25); SPEED_OUT_LEFT (2024 WR) -> SPEED_OUT_ROUTE_LEFT (2023, 2025 WR). SHORT_ZONE_BREAKS (2023-24, DL/LB) vs SHORT_ZONE_BREAK_FLAT_WHEEL / _FORWARD / _INSIDE (2025 DL only) "
      "is a split, not a rename. These mappings are my inference from the names and the position mix, not verified against any documentation.")
    h(3, "C2b. After merging the four likely renames: drill availability by year (attempts)")
    t = A.group_by("drill_type", "drill_canon", "draft_year").agg(pl.len().alias("att"), pl.col("nfl_id").n_unique().alias("pl"))
    t = t.with_columns((pl.col("att").cast(pl.String) + " / " + pl.col("pl").cast(pl.String)).alias("v")).pivot(on="draft_year", index=["drill_type", "drill_canon"], values="v").sort("drill_type", "drill_canon")
    p("Cells are attempts / players.")
    tbl(t)

    h(3, "C3. Players with any tracking per drill_type, by combine_position")
    tot = pp.group_by("combine_position").len().rename({"len": "all_players"})
    t = A.group_by("combine_position", "drill_type").agg(pl.col("nfl_id").n_unique().alias("pl")).pivot(on="drill_type", index="combine_position", values="pl").fill_null(0)
    t = tot.join(t, on="combine_position", how="left").sort("all_players", descending=True)
    tbl(t)
    p("Same, by nfl_position:")
    tot = pp.group_by("nfl_position").len().rename({"len": "all_players"})
    t = A.group_by("nfl_position", "drill_type").agg(pl.col("nfl_id").n_unique().alias("pl")).pivot(on="drill_type", index="nfl_position", values="pl").fill_null(0)
    tbl(tot.join(t, on="nfl_position", how="left").sort("all_players", descending=True))
    p("Same, by combine_position x draft_year (players with a SKILL_DRILLS_* type matching their position / all players):")
    own = {"WR": "SKILL_DRILLS_WR", "TE": "SKILL_DRILLS_TE", "OL": "SKILL_DRILLS_OL", "DL": "SKILL_DRILLS_DL", "DB": "SKILL_DRILLS_DB"}
    rows = []
    for pos, dt_ in own.items():
        for yr in (2023, 2024, 2025):
            n_all = pp.filter((pl.col("combine_position") == pos) & (pl.col("draft_year") == yr)).height
            n_tr = A.filter((pl.col("combine_position") == pos) & (pl.col("draft_year") == yr) & (pl.col("drill_type") == dt_))["nfl_id"].n_unique()
            rows.append((pos, yr, n_all, n_tr))
    tbl(pl.DataFrame(rows, schema=["combine_position", "draft_year", "all_players", "with_own_skill_drills"], orient="row"))
    p("Skill-drill type vs the athlete's combine_position (players), to see any cross-over (e.g. LB drills):")
    t = A.filter(pl.col("drill_type").str.starts_with("SKILL")).group_by("drill_type", "combine_position").agg(pl.col("nfl_id").n_unique().alias("pl")).sort("drill_type", "pl", descending=[False, True])
    tbl(t)

    h(3, "C4. Players with >= 2 attempts of the same drill_name (test-retest candidates)")
    p("Counted within the player's own draft year, so raw drill_name is correct. Columns per drill: players with >=1 attempt / players with >=2 attempts.")
    pd = A.group_by("nfl_id", "drill_type", "drill_name").agg(pl.len().alias("k"), pl.col("combine_position").first().alias("cp"), pl.col("drill_canon").first().alias("dc"), pl.col("attempt").n_unique().alias("na"))
    t = pd.group_by("drill_type", "dc").agg(
        pl.len().alias("players_ge1"), (pl.col("k") >= 2).sum().alias("players_ge2"), (pl.col("k") >= 3).sum().alias("players_ge3"),
        pl.col("k").max().alias("max_attempts"),
    ).sort("drill_type", "dc")
    tbl(t)
    p("By combine_position x drill_type (players with >=2 attempts of at least one drill_name in that type, and total players in the type):")
    t = pd.group_by("cp", "drill_type").agg(pl.col("nfl_id").n_unique().alias("players"), pl.col("nfl_id").filter(pl.col("k") >= 2).n_unique().alias("players_with_a_repeated_drill"))
    tbl(t.sort("drill_type", "cp"))
    p("Players with >=2 attempts of the same drill_name for each position, by drill (restricted to drills with >=10 such players):")
    t = pd.filter(pl.col("k") >= 2).group_by("cp", "drill_type", "dc").agg(pl.len().alias("players_ge2")).filter(pl.col("players_ge2") >= 10).sort("cp", "drill_type", "players_ge2", descending=[False, False, True])
    tbl(t)
    p("Distribution of attempts per player for the three non-skill tests:")
    t = pd.filter(pl.col("drill_type").is_in(["FORTY_YARD_DASH", "THREE_CONE_DRILL", "SHORT_SHUTTLE"])).group_by("drill_type", "k").len().pivot(on="k", index="drill_type", values="len").fill_null(0)
    tbl(t.select("drill_type", *sorted([c for c in t.columns if c != "drill_type"], key=int)))


def sec_C5():
    h(3, "C5. Are two attempts of the same drill_name the same condition? (start-position check)")
    p("For players with exactly 2 tracked attempts of a drill_name: distance between the two first-frame positions and between the two last-frame positions. "
      "Large start distances indicate the two attempts are different reps (e.g. left vs right side), so they are not test-retest repeats. Drills with >= 8 such players.")
    g = A.sort("t0").group_by("nfl_id", "drill_type", "drill_name").agg(
        pl.len().alias("k"), pl.col("x_first"), pl.col("y_first"), pl.col("x_last"), pl.col("y_last"), pl.col("drill_canon").first().alias("dc")).filter(pl.col("k") == 2)
    g = g.with_columns(
        ((pl.col("x_first").list.get(0) - pl.col("x_first").list.get(1)) ** 2 + (pl.col("y_first").list.get(0) - pl.col("y_first").list.get(1)) ** 2).sqrt().alias("d_start"),
        ((pl.col("x_last").list.get(0) - pl.col("x_last").list.get(1)) ** 2 + (pl.col("y_last").list.get(0) - pl.col("y_last").list.get(1)) ** 2).sqrt().alias("d_end"))
    t = g.group_by("drill_type", "dc").agg(pl.len().alias("pairs"), pl.col("d_start").median().alias("start_dist_med"), (pl.col("d_start") > 3).mean().alias("share_start_gt3yd"),
                                           pl.col("d_end").median().alias("end_dist_med")).filter(pl.col("pairs") >= 8).sort("drill_type", "share_start_gt3yd", descending=[False, True])
    tbl(t, 2)
    p("Reading: share_start_gt3yd near 1 = the two reps start in different places (different side/variant); near 0 = repeated from the same mark (a genuine repeat, though the end positions can still differ).")


# ============================================================================= D. missing
def sec_D():
    h(2, "D. Players without tracking, or missing a 40 / 3-cone / shuttle in tracking")
    have = A.group_by("nfl_id").agg(
        (pl.col("drill_type") == "FORTY_YARD_DASH").any().alias("t40"),
        (pl.col("drill_type") == "THREE_CONE_DRILL").any().alias("t3c"),
        (pl.col("drill_type") == "SHORT_SHUTTLE").any().alias("tss"),
        pl.col("drill_type").str.starts_with("SKILL").any().alias("tskill"),
    )
    d = pp.join(have, on="nfl_id", how="left").join(cr.select("nfl_id", "forty", "three_cone", "short_shuttle"), on="nfl_id", how="left")
    d = d.with_columns(pl.col(["t40", "t3c", "tss", "tskill"]).fill_null(False))
    d = d.with_columns((~(pl.col("t40") | pl.col("t3c") | pl.col("tss") | pl.col("tskill"))).alias("none"))
    agg = lambda key: d.group_by(key).agg(
        pl.len().alias("players"),
        pl.col("none").sum().alias("no_tracking_at_all"),
        (~pl.col("t40")).sum().alias("no_tracked_40"),
        (~pl.col("t3c")).sum().alias("no_tracked_3cone"),
        (~pl.col("tss")).sum().alias("no_tracked_shuttle"),
        (~pl.col("tskill")).sum().alias("no_skill_drills"),
        (pl.col("t40") & pl.col("t3c") & pl.col("tss")).sum().alias("has_all_three"),
        (~pl.col("t40") & ~pl.col("t3c") & ~pl.col("tss")).sum().alias("none_of_three"),
    ).sort("players", descending=True)
    p("By combine_position:")
    tbl(agg("combine_position"))
    p("By nfl_position:")
    tbl(agg("nfl_position"))
    p("By draft_year:")
    tbl(agg("draft_year").sort("draft_year"))
    h(3, "D2. Agreement between official test availability (combine_results non-null) and tracked attempts")
    rows = []
    for name, tr, off in [("forty", "t40", "forty"), ("three_cone", "t3c", "three_cone"), ("short_shuttle", "tss", "short_shuttle")]:
        o = pl.col(off).is_not_null()
        rows.append((name, d.filter(o & pl.col(tr)).height, d.filter(o & ~pl.col(tr)).height, d.filter(~o & pl.col(tr)).height, d.filter(~o & ~pl.col(tr)).height))
    tbl(pl.DataFrame(rows, schema=["test", "official_and_tracked", "official_not_tracked", "tracked_not_official", "neither"], orient="row"))
    p(f"Players in `players` with no PLAYER tracking at all: {d.filter(pl.col('none')).height} of {d.height}. Every cohort player has at least one SKILL_DRILLS_* attempt: {d.filter(pl.col('tskill')).height} of {d.height}.")


# ============================================================================= E. quality
def sec_E():
    h(2, "E. Tracking quality (PLAYER rows only)")
    h(3, "E1. Sampling interval")
    ordered_ok = (F.group_by("event_id").agg((pl.col("row").diff() > 0).all().alias("rowsorted"))["rowsorted"]).all()
    file_sorted = trk.filter(pl.col("entity_type") == "PLAYER").with_columns(pl.col("time").diff().over("event_id").dt.total_microseconds().alias("d0"))
    p(f"PLAYER rows: {P.height}; attempts: {N_EVENTS}. Rows of each attempt contiguous in file? "
      f"{trk.filter(pl.col('entity_type')=='PLAYER').group_by('event_id').agg((pl.col('row').max() - pl.col('row').min() + 1 == pl.len()).alias('c'))['c'].all()}. "
      f"Time non-decreasing in file order within every attempt? {not (file_sorted['d0'] < 0).any()} (negative diffs: {(file_sorted['d0'] < 0).sum()}).")
    d = F.filter(pl.col("dt_us").is_not_null())
    p(f"Frame-to-frame diffs: {d.height}. Exactly 100000 us: {(d['dt_us'] == 100000).sum()}; within +-1 ms of 100 ms: {((d['dt_us'] - 100000).abs() <= 1000).sum()}; "
      f"zero (duplicate timestamps): {(d['dt_us'] == 0).sum()}; negative: {(d['dt_us'] < 0).sum()}.")
    vc = d.group_by((pl.col("dt_us") / 1000).round(0).alias("dt_ms")).len().sort("len", descending=True).head(12)
    p("Most common dt (ms):")
    tbl(vc)
    gaps = d.filter(pl.col("dt_us") > 100000 + 1000)
    p(f"Gaps (dt > 101 ms): {gaps.height} frames in {gaps['event_id'].n_unique()} attempts; max gap {(gaps['dt_us'].max() or 0) / 1e6:.2f} s. "
      f"Attempts with any non-100ms diff: {d.filter((pl.col('dt_us') - 100000).abs() > 1000)['event_id'].n_unique()}.")
    full = A.with_columns((((pl.col("frames") - 1) * DT - pl.col("dur")).abs() < 1e-3).alias("regular"))
    p(f"Attempts where (frames-1)*0.1 == last-first timestamp (i.e. regular, gap-free, no duplicates): {full['regular'].sum()} of {N_EVENTS}.")
    p("Frame count / duration per drill_type (attempts):")
    t = A.group_by("drill_type").agg(pl.len().alias("attempts"), pl.col("frames").min().alias("frames_min"), pl.col("frames").median().alias("frames_med"), pl.col("frames").max().alias("frames_max"),
                                     pl.col("dur").min().alias("dur_min"), pl.col("dur").median().alias("dur_med"), pl.col("dur").max().alias("dur_max"),
                                     (pl.col("frames") < 20).sum().alias("lt_2s")).sort("drill_type")
    tbl(t)
    p("Do timestamps carry sub-100ms jitter? Distinct values of (time microsecond-of-second mod 100000):")
    p(str(F.select((pl.col("time").dt.microsecond() % 100000).n_unique()).item()) + " distinct values.")

    h(3, "E2. Null rates")
    cols = ["x", "y", "s", "a", "dis", "dir", "time", "attempt", "nfl_id", "drill_name", "drill_type"]
    t = pl.DataFrame({"column": cols, "null_n": [P[c].null_count() for c in cols], "null_rate": [P[c].null_count() / P.height for c in cols]})
    tbl(t, 5)
    p("Null rate by drill_type for numeric columns (only non-zero cells informative):")
    t = P.group_by("drill_type").agg(pl.len().alias("rows"), *[pl.col(c).is_null().mean().alias(c) for c in ["x", "y", "s", "a", "dis", "dir"]]).sort("drill_type")
    tbl(t, 5)
    p(f"Non-finite values (NaN/inf) in x,y,s,a,dis,dir: {sum(P[c].is_nan().sum() + P[c].is_infinite().sum() for c in ['x','y','s','a','dis','dir'])}.")
    nd = F.filter(pl.col("dir").is_null())
    if nd.height:
        p(f"Rows with null dir: {nd.height}; their median s = {nd['s'].median():.3f}; share with i==0: {(nd['i'] == 0).mean():.3f}.")

    h(3, "E3. Ranges and percentiles of s and a by drill_type")
    def pct_tbl(col):
        return F.group_by("drill_type").agg(
            pl.col(col).count().alias("n"), pl.col(col).min().alias("min"),
            pl.col(col).quantile(0.01).alias("p01"), pl.col(col).quantile(0.50).alias("p50"), pl.col(col).quantile(0.99).alias("p99"),
            pl.col(col).quantile(0.999).alias("p99.9"), pl.col(col).max().alias("max"),
        ).sort("drill_type")
    p("s (yd/s):")
    tbl(pct_tbl("s"), 2)
    p("a (yd/s^2):")
    tbl(pct_tbl("a"), 2)
    p("dis (yd per frame):")
    tbl(pct_tbl("dis"), 3)
    p("Plausibility flags per drill_type: frames with s>10, s>12; |a|>10, |a|>15; a<0; implied x/y step speed >12 yd/s (position jumps); attempts affected in parentheses.")
    FS = F
    t = FS.group_by("drill_type").agg(
        pl.len().alias("frames"),
        (pl.col("s") > 10).sum().alias("s_gt10"), (pl.col("s") > 12).sum().alias("s_gt12"), pl.col("event_id").filter(pl.col("s") > 12).n_unique().alias("att_s_gt12"),
        (pl.col("a").abs() > 10).sum().alias("abs_a_gt10"), (pl.col("a").abs() > 15).sum().alias("abs_a_gt15"), pl.col("event_id").filter(pl.col("a").abs() > 15).n_unique().alias("att_a_gt15"),
        (pl.col("a") < 0).sum().alias("a_lt0"),
        ((pl.col("step") / DT) > 12).sum().alias("xy_speed_gt12"), pl.col("event_id").filter((pl.col("step") / DT) > 12).n_unique().alias("att_xy_gt12"),
    ).sort("drill_type")
    tbl(t)
    p("Single worst values (s max, a max) with drill_type, no identifiers:")
    tbl(F.sort("s", descending=True).head(3).select("drill_type", "s", "a", "dis"), 3)

    h(3, "E4. Does s agree with speed from x/y differences?")
    p("Speed from x/y: v_back = step(t-1 -> t)/0.1, v_fwd = step(t -> t+1)/0.1, v_ctr = |pos(t+1) - pos(t-1)|/0.2. Only frames with regular 100 ms spacing on both sides. "
      "'ratio' is median s/v; 'MAE' is mean |s - v| in yd/s; corr is Pearson.")
    G = F.filter((pl.col("dt_us") == 100000) & (pl.col("dt_next_us") == 100000)).with_columns(
        (pl.col("step") / DT).alias("v_back"), (pl.col("step_next") / DT).alias("v_fwd"),
        ((pl.col("cdx") ** 2 + pl.col("cdy") ** 2).sqrt() / (2 * DT)).alias("v_ctr"),
    )

    def agree(g: pl.DataFrame, label: str):
        rows = []
        for v in ["v_back", "v_fwd", "v_ctr"]:
            gg = g.filter(pl.col(v).is_not_null())
            rows.append((label, v, gg.height, gg.select(pl.corr("s", v)).item(), (gg["s"] - gg[v]).abs().mean(), (gg["s"] / gg[v].clip(lower_bound=0.5)).median()))
        return rows

    rows = agree(G, "ALL")
    rows += agree(G.filter(pl.col("s") > 2), "ALL moving (s>2)")
    for dtn in sorted(A["drill_type"].unique().to_list()):
        rows += agree(G.filter((pl.col("drill_type") == dtn) & (pl.col("s") > 2)), dtn + " (s>2)")
    tbl(pl.DataFrame(rows, schema=["subset", "v_def", "n", "corr", "MAE", "ratio_median"], orient="row"), 3)
    p("Same for `dis` (yd per frame) vs step lengths: ratio = median dis/step for frames with step>0.1 yd (moving):")
    rows = []
    for dtn in ["ALL"] + sorted(A["drill_type"].unique().to_list()):
        gg = G if dtn == "ALL" else G.filter(pl.col("drill_type") == dtn)
        gg = gg.filter(pl.col("step") > 0.1)
        gb = gg.select(pl.corr("dis", "step").alias("c_back"), (pl.col("dis") / pl.col("step")).median().alias("r_back"))
        gf = gg.filter(pl.col("step_next") > 0.1).select(pl.corr("dis", "step_next").alias("c_fwd"), (pl.col("dis") / pl.col("step_next")).median().alias("r_fwd"))
        rows.append((dtn, gg.height, gb["c_back"][0], gb["r_back"][0], gf["c_fwd"][0], gf["r_fwd"][0],
                     gg.select((pl.col("dis") / (pl.col("s") * DT)).median()).item()))
    tbl(pl.DataFrame(rows, schema=["subset", "n", "corr_dis_stepback", "ratio_dis/stepback", "corr_dis_stepfwd", "ratio_dis/stepfwd", "ratio_dis/(s*0.1)"], orient="row"), 3)

    h(3, "E4b. What is `dis`? Scaling of dis against speed")
    p("If dis were a per-frame distance it would equal s*0.1. Median dis/(s*0.1) by speed bin (frames with s>0.5), all drill types pooled, then a log-log fit dis = k * s^b:")
    gs = F.filter(pl.col("s") > 0.5).with_columns(((pl.col("s") // 2) * 2).alias("s_bin"))
    tbl(gs.group_by("s_bin").agg(pl.len().alias("frames"), (pl.col("dis") / (pl.col("s") * DT)).median().alias("median_dis_over_s0.1"),
                                 (pl.col("dis") / (pl.col("s") ** 2)).median().alias("median_dis_over_s2")).sort("s_bin"), 4)
    gq = gs.filter(pl.col("dis") > 0)
    ls, ld = np.log(gq["s"].to_numpy()), np.log(gq["dis"].to_numpy())
    bfit, afit = np.polyfit(ls, ld, 1)
    p(f"Log-log fit over {len(ls)} frames: dis ~ {np.exp(afit):.4f} * s^{bfit:.2f}, R^2 = {np.corrcoef(ls, ld)[0, 1] ** 2:.3f}. "
      "A slope near 2 would mean dis behaves like speed squared, i.e. it is not a distance and under-reads progressively more at low speeds (inference from the fit, not documented).")
    p("Median dis/(s*0.1) per drill_type (moving frames): " + ", ".join(f"{r['drill_type']}={r['m']:.2f}" for r in gs.group_by("drill_type").agg((pl.col("dis") / (pl.col("s") * DT)).median().alias("m")).sort("drill_type").to_dicts()))

    h(3, "E5. Is a signed?")
    G2 = G.with_columns(((pl.col("s_next") - pl.col("s_prev")) / (2 * DT)).alias("dsdt"))
    p(f"Frames with a<0: {(F['a'] < 0).sum()} of {F['a'].count()} (min a = {F['a'].min():.3f}). "
      f"Corr(a, ds/dt)= {G2.select(pl.corr('a','dsdt')).item():.3f}; Corr(a, |ds/dt|)= {G2.select(pl.corr('a', pl.col('dsdt').abs())).item():.3f}.")
    dec = G2.filter(pl.col("dsdt") < -3)
    acc = G2.filter(pl.col("dsdt") > 3)
    p(f"Frames clearly decelerating (ds/dt < -3 yd/s^2, n={dec.height}): median a = {dec['a'].median():.2f}, share a<0 = {(dec['a'] < 0).mean():.3f}. "
      f"Clearly accelerating (ds/dt > 3, n={acc.height}): median a = {acc['a'].median():.2f}.")

    h(3, "E6. Does dir agree with x/y displacement direction?")
    p("dir is compared with the bearing of the centred displacement (t-1 -> t+1) for frames with s>2 yd/s and regular spacing. "
      "Candidate bearings: atan2(sx*dx, sy*dy) or atan2(sy*dy, sx*dx) with sign flips sx,sy in {+1,-1}; reported: median and p90 of absolute circular difference (deg), share within 15 deg, and median signed difference.")
    g = G.filter((pl.col("s") > 2) & pl.col("dir").is_not_null() & (pl.col("v_ctr") > 1))
    dxa, dya, dr = g["cdx"].to_numpy(), g["cdy"].to_numpy(), g["dir"].to_numpy()
    rows = []
    best = None
    for order in ("atan2(dx,dy)", "atan2(dy,dx)"):
        for sx in (1, -1):
            for sy in (1, -1):
                b = np.degrees(np.arctan2(sx * dxa, sy * dya) if order == "atan2(dx,dy)" else np.arctan2(sy * dya, sx * dxa)) % 360
                diff = (dr - b + 180) % 360 - 180
                ad = np.abs(diff)
                row = (f"{order}, sx={sx:+d}, sy={sy:+d}", float(np.median(ad)), float(np.percentile(ad, 90)), float((ad < 15).mean()), float(np.median(diff)))
                rows.append(row)
                if best is None or row[1] < best[1]:
                    best = row
    tbl(pl.DataFrame(rows, schema=["convention", "median_abs_diff", "p90_abs_diff", "share_within_15", "median_signed_diff"], orient="row").sort("median_abs_diff"), 2)
    p(f"Best convention: {best[0]} (n frames = {g.height}).")
    # per drill_type with best convention
    order = "atan2(dx,dy)" if best[0].startswith("atan2(dx,dy)") else "atan2(dy,dx)"
    sx = 1 if "sx=+1" in best[0] else -1
    sy = 1 if "sy=+1" in best[0] else -1
    b = np.degrees(np.arctan2(sx * dxa, sy * dya) if order == "atan2(dx,dy)" else np.arctan2(sy * dya, sx * dxa)) % 360
    ad = np.abs((dr - b + 180) % 360 - 180)
    gg = g.with_columns(pl.Series("ad", ad))
    p("By drill_type under the best convention:")
    tbl(gg.group_by("drill_type").agg(pl.len().alias("n"), pl.col("ad").median().alias("median_abs_diff"), pl.col("ad").quantile(0.9).alias("p90"), (pl.col("ad") < 15).mean().alias("share_within_15")).sort("drill_type"), 2)
    p("Range of dir: min "
      f"{F['dir'].min():.2f}, max {F['dir'].max():.2f}.")

    h(3, "E7. Stationary time at start and end of attempts (s < 0.5 yd/s)")
    p("lead = time before the first frame with s>=0.5; trail = time after the last frame with s>=0.5. Seconds. "
      "starts_moving = first frame already has s>=0.5. never_moves = no frame with s>=0.5.")
    t = A.group_by("drill_type").agg(
        pl.len().alias("attempts"),
        pl.col("dur").median().alias("dur_med"),
        pl.col("lead_s").quantile(0.25).alias("lead_p25"), pl.col("lead_s").median().alias("lead_med"), pl.col("lead_s").quantile(0.75).alias("lead_p75"), pl.col("lead_s").quantile(0.9).alias("lead_p90"), pl.col("lead_s").max().alias("lead_max"),
        pl.col("trail_s").quantile(0.25).alias("trail_p25"), pl.col("trail_s").median().alias("trail_med"), pl.col("trail_s").quantile(0.75).alias("trail_p75"), pl.col("trail_s").quantile(0.9).alias("trail_p90"), pl.col("trail_s").max().alias("trail_max"),
        pl.col("starts_moving").mean().alias("starts_moving"),
        pl.col("first_move").is_null().sum().alias("never_moves"),
        ((pl.col("lead_s") + pl.col("trail_s")) / pl.col("dur")).median().alias("stationary_share_med"),
    ).sort("drill_type")
    tbl(t, 2)
    t = A.filter(pl.col("drill_type").is_in(["FORTY_YARD_DASH", "THREE_CONE_DRILL", "SHORT_SHUTTLE"])).group_by("drill_type", "draft_year").agg(
        pl.len().alias("attempts"), pl.col("lead_s").median().alias("lead_med"), pl.col("trail_s").median().alias("trail_med"), pl.col("dur").median().alias("dur_med"), pl.col("starts_moving").mean().alias("starts_moving")).sort("drill_type", "draft_year")
    p("The three standard tests by draft year:")
    tbl(t, 2)

    h(3, "E8. Duplicate trajectories and coordinate sanity")
    sig = F.group_by("event_id").agg(pl.col("x").round(3).cast(pl.String).str.join(",").alias("sig"))
    dups = sig.group_by("sig").len().filter(pl.col("len") > 1)
    p(f"Attempts with an x-trajectory identical (3 dp) to another attempt: {dups['len'].sum() if dups.height else 0} in {dups.height} groups.")
    oob = F.group_by("drill_type").agg(
        (pl.col("x") < 0).sum().alias("x<0"), (pl.col("x") > FIELD_X).sum().alias("x>120"), (pl.col("y") < 0).sum().alias("y<0"), (pl.col("y") > FIELD_Y).sum().alias("y>53.33"),
        pl.col("x").min().alias("x_min"), pl.col("x").max().alias("x_max"), pl.col("y").min().alias("y_min"), pl.col("y").max().alias("y_max"), pl.len().alias("frames")).sort("drill_type")
    tbl(oob)
    p(f"Time stamps by year: " + "; ".join(f"{r['draft_year']}: {r['a']:%Y-%m-%d} to {r['b']:%Y-%m-%d} ({r['days']} distinct dates)" for r in F.group_by("draft_year").agg(pl.col("time").min().alias("a"), pl.col("time").max().alias("b"), pl.col("time").dt.date().n_unique().alias("days")).sort("draft_year").to_dicts()))


def sec_E9():
    h(3, "E9. Implausible or truncated attempts in the three standard tests")
    p("Duration (last - first timestamp) and path length (sum of x/y steps) percentiles, and counts outside rough plausible bounds "
      "(40: dur 4.2-7.5 s; shuttle: 3.0-8.0 s; 3-cone: 5.5-11.0 s; these bounds are my judgment, not from the host).")
    bounds = {"FORTY_YARD_DASH": (4.2, 7.5), "SHORT_SHUTTLE": (3.0, 8.0), "THREE_CONE_DRILL": (5.5, 11.0)}
    rows = []
    for dtn, (lo, hi) in bounds.items():
        g = A.filter(pl.col("drill_type") == dtn)
        rows.append((dtn, g.height, g["dur"].min(), g["dur"].quantile(0.05), g["dur"].median(), g["dur"].quantile(0.95), g["dur"].max(),
                     g["sum_xy"].quantile(0.05), g["sum_xy"].median(), g["sum_xy"].quantile(0.95),
                     g.filter((pl.col("dur") < lo) | (pl.col("dur") > hi)).height, g.filter(pl.col("dur") < lo).height, g.filter(pl.col("dur") > hi).height))
    tbl(pl.DataFrame(rows, schema=["drill_type", "attempts", "dur_min", "dur_p5", "dur_med", "dur_p95", "dur_max", "xy_p5", "xy_med", "xy_p95", "outside_bounds", "too_short", "too_long"], orient="row"), 2)
    p("Nominal geometry for reference (my knowledge, not from the files): 5-10-5 shuttle is about 20 yd of path and 3-cone about 25-30 yd; tracked paths are shorter (see xy_med), "
      "consistent with 10 Hz sampling/smoothing cutting corners and/or incomplete capture; this is an inference.")
    p("By draft_year, share of the standard-test attempts outside the bounds:")
    t = A.filter(pl.col("drill_type").is_in(list(bounds))).with_columns(
        pl.when(pl.col("drill_type") == "FORTY_YARD_DASH").then((pl.col("dur") < 4.2) | (pl.col("dur") > 7.5))
        .when(pl.col("drill_type") == "SHORT_SHUTTLE").then((pl.col("dur") < 3.0) | (pl.col("dur") > 8.0))
        .otherwise((pl.col("dur") < 5.5) | (pl.col("dur") > 11.0)).alias("odd"))
    tbl(t.group_by("drill_type", "draft_year").agg(pl.len().alias("attempts"), pl.col("odd").sum().alias("outside"), pl.col("odd").mean().alias("share")).sort("drill_type", "draft_year"), 3)


# ============================================================================= F. attempts / events
def sec_F():
    h(2, "F. attempt numbering and event integrity")
    p(f"Attempts (event_id) with >1 distinct nfl_id: {A.filter(pl.col('n_ids') > 1).height}; >1 drill_type: {A.filter(pl.col('n_dtype') > 1).height}; "
      f">1 drill_name: {A.filter(pl.col('n_dname') > 1).height}; >1 attempt value: {A.filter(pl.col('n_att') > 1).height}; >1 draft_year: {A.filter(pl.col('n_year') > 1).height}.")
    be = B.group_by("event_id").agg(pl.col("nfl_id").n_unique().alias("bn"), pl.col("nfl_id").first().alias("bid"), pl.len().alias("bframes"))
    chk = be.join(A.select("event_id", pl.col("nfl_id").alias("pid"), "frames"), on="event_id", how="left")
    p(f"BALL events: {be.height}; BALL events with no PLAYER rows for same event_id: {chk['pid'].null_count()}; BALL events whose BALL nfl_id differs from the PLAYER nfl_id: {chk.filter(pl.col('bid') != pl.col('pid')).height}; "
      f"BALL events with >1 distinct nfl_id: {be.filter(pl.col('bn') > 1).height}; BALL frame count == PLAYER frame count: {chk.filter(pl.col('bframes') == pl.col('frames')).height} of {chk.height}.")
    # attempt numbering
    for key_label, key in [("(nfl_id, drill_type, drill_name)", ["nfl_id", "drill_type", "drill_name"]), ("(nfl_id, drill_type)", ["nfl_id", "drill_type"])]:
        g = A.group_by(key).agg(pl.len().alias("events"), pl.col("attempt").n_unique().alias("na"), pl.col("attempt").min().alias("amin"), pl.col("attempt").max().alias("amax"), pl.col("draft_year").first().alias("dy"))
        g = g.with_columns(
            (pl.col("amin") == 1).alias("starts1"),
            ((pl.col("amax") - pl.col("amin") + 1) == pl.col("na")).alias("contig"),
            (pl.col("na") == pl.col("events")).alias("unique_per_event"),
        )
        h(3, f"F1. Attempt numbering keyed by {key_label}")
        tbl(g.group_by("dy").agg(pl.len().alias("groups"), pl.col("starts1").mean().alias("starts_at_1"), pl.col("contig").mean().alias("contiguous"), pl.col("unique_per_event").mean().alias("no_dup_attempt_numbers"),
                                 pl.col("amax").max().alias("max_attempt")).sort("dy"), 3)
        bad = g.filter(~(pl.col("starts1") & pl.col("contig") & pl.col("unique_per_event")))
        p(f"Groups violating (starts at 1, contiguous, unique): {bad.height} of {g.height}.")
        if bad.height:
            tbl(bad.group_by("dy").agg(pl.len().alias("bad_groups"), (~pl.col("starts1")).sum().alias("not_start_1"), (~pl.col("contig")).sum().alias("gaps"), (~pl.col("unique_per_event")).sum().alias("duplicate_numbers")).sort("dy"))
            if "drill_name" in key:
                tbl(bad.group_by("drill_type").agg(pl.len().alias("bad_groups")).sort("drill_type"))
        p("Attempt value distribution (events): " + ", ".join(f"{r['attempt']}:{r['len']}" for r in A.group_by("attempt").len().sort("attempt").to_dicts()))
    h(3, "F1b. Which grouping does `attempt` count within? (match with chronological rank)")
    r = A.sort("nfl_id", "t0").with_columns(
        (pl.int_range(pl.len()).over("nfl_id") + 1).alias("r_player"),
        (pl.int_range(pl.len()).over(["nfl_id", "drill_type"]) + 1).alias("r_type"),
        (pl.int_range(pl.len()).over(["nfl_id", "drill_type", "drill_name"]) + 1).alias("r_name"))
    p("Share of attempts whose `attempt` equals the chronological rank (by t0) within the given grouping:")
    tbl(r.group_by("draft_year").agg((pl.col("attempt") == pl.col("r_player")).mean().alias("player_all_drills"),
                                      (pl.col("attempt") == pl.col("r_type")).mean().alias("player_x_drill_type"),
                                      (pl.col("attempt") == pl.col("r_name")).mean().alias("player_x_drill_name")).sort("draft_year"), 3)
    key = {2023: "drill_name", 2024: "drill_name", 2025: "drill_type"}
    rows = []
    for yr, k in key.items():
        g = A.filter(pl.col("draft_year") == yr).group_by(["nfl_id", k]).agg(pl.col("attempt").min().alias("amin"), pl.col("attempt").max().alias("amax"), pl.col("attempt").n_unique().alias("na"), pl.len().alias("ev"))
        miss = (g["amin"] - 1) + (g["amax"] - g["amin"] + 1 - g["na"])
        rows.append((yr, k, g.height, int((miss > 0).sum()), int(miss.sum()), int((g["na"] != g["ev"]).sum())))
    p("Using the best-fitting grouping for each year (2023/2024: player x drill_name; 2025: player x drill_type), how many groups have attempt numbers missing "
      "(start above 1 or internal gaps, i.e. an earlier/inner attempt is absent from the file) and how many attempt numbers are missing in total:")
    tbl(pl.DataFrame(rows, schema=["draft_year", "grouping", "groups", "groups_with_missing", "missing_attempt_numbers", "groups_with_duplicate_numbers"], orient="row"))
    p("Interpretation (inference): in 2023/2024 `attempt` restarts at 1 for each drill_name; in 2025 it is a running count within the player's drill_type "
      "(e.g. one OL player has attempts 1-8 across seven different OL drill_names). So `attempt==2` means 'second repetition' only for 2023/24; in 2025 order by time instead.")
    h(3, "F2. Does attempt order agree with chronological order?")
    g = A.sort("nfl_id", "drill_type", "drill_name", "attempt").with_columns(
        (pl.col("t0").diff().over(["nfl_id", "drill_type", "drill_name"]).dt.total_seconds()).alias("gap_s"))
    g = g.filter(pl.col("gap_s").is_not_null())
    p(f"Consecutive attempt pairs of same player+drill: {g.height}; with later attempt number starting earlier in time: {(g['gap_s'] < 0).sum()}; "
      f"median gap between attempts: {g['gap_s'].median():.1f} s; by drill_type median gap (s):")
    tbl(g.group_by("drill_type").agg(pl.len().alias("pairs"), pl.col("gap_s").median().alias("median_gap_s"), (pl.col("gap_s") < 0).sum().alias("out_of_order")).sort("drill_type"))
    p("Only one attempt-number per event is expected, and the 40/3-cone/shuttle usually have 1-3 attempts; see C4 for distribution.")
    p("event_id string formats by year (length, shape of first chars; pattern only):")
    tbl(A.group_by("draft_year").agg(pl.col("event_id").str.len_chars().min().alias("len_min"), pl.col("event_id").str.len_chars().max().alias("len_max"),
                                     pl.col("event_id").str.contains(r"^\d{14}_\d+_\d+$").mean().alias("share_timestamp_style"),
                                     pl.col("event_id").str.contains(r"^[0-9a-f]{24}-\d{4}$").mean().alias("share_hex_year_style")).sort("draft_year"), 3)


# ============================================================================= G. forum checks
def first_crossing(t, dist, target):
    """time (s) at which dist (monotone-ish radial distance array) first >= target, linear interpolated; nan if never."""
    idx = np.where(dist >= target)[0]
    if len(idx) == 0:
        return float("nan")
    k = idx[0]
    if k == 0:
        return t[0]
    f = (target - dist[k - 1]) / max(dist[k] - dist[k - 1], 1e-9)
    return t[k - 1] + f * (t[k] - t[k - 1])


def forty_times(thr: float):
    """per 40 attempt, times (s) measured three ways. Radial: first time the Euclidean distance from the onset position (first frame with s>=thr)
    reaches 10 / 40 yd. X-crossing: first time x reaches 20 / 50 (i.e. 10 / 40 yd past a start line at x=10), measured from the first frame of the
    recording ('f') or from the onset frame ('o')."""
    rows = []
    nan = float("nan")
    for ev, g in F.filter(pl.col("drill_type") == "FORTY_YARD_DASH").partition_by("event_id", as_dict=True, maintain_order=True).items():
        ev = ev[0]
        g = g.sort("time")
        te = g["time"].dt.epoch("us").to_numpy().astype(float)
        t = (te - te[0]) / 1e6
        x, y, s = g["x"].to_numpy(), g["y"].to_numpy(), g["s"].to_numpy()
        mv = np.where(s >= thr)[0]
        xm = np.maximum.accumulate(x)
        t20f, t50f = first_crossing(t, xm, 20.0), first_crossing(t, xm, 50.0)
        if len(mv) == 0:
            rows.append((ev, nan, nan, nan, nan, nan, nan, t20f, t50f, nan, nan, nan)); continue
        i0 = int(mv[0])
        r = np.hypot(x[i0:] - x[i0], y[i0:] - y[i0])
        tt = t[i0:] - t[i0]
        rows.append((ev, first_crossing(tt, r, 10.0), first_crossing(tt, r, 40.0), float(x[i0]), float(y[i0]), float(x[-1]), float(r.max()),
                     t20f, t50f, t20f - t[i0], t50f - t[i0], float(t[i0])))
    return pl.DataFrame(rows, schema=["event_id", "t10", "t40", "x_onset", "y_onset", "x_end", "max_radial", "t20f", "t50f", "t20o", "t50o", "lead_s"], orient="row")


def sec_G():
    h(2, "G. Forum claims")
    claims = []

    # ---- 1
    h(3, "G1. 6,310 drill attempts (distinct event_id)")
    n_all = trk["event_id"].n_unique()
    n_pl = P["event_id"].n_unique()
    p(f"Distinct event_id overall: {n_all}; with PLAYER rows: {n_pl}; total rows {trk.height} (PLAYER {P.height}, BALL {B.height}).")
    claims.append(("1", "6,310 drill attempts", "CONFIRMED" if n_all == 6310 else "CONTRADICTED", f"{n_all} distinct event_id (all have PLAYER rows: {n_pl}); rows {trk.height}"))

    # ---- 2
    h(3, "G2. BALL rows")
    be = B.group_by("event_id").agg(pl.col("nfl_id").first().alias("bid"), pl.col("drill_type").first().alias("dtype"), pl.len().alias("bf"))
    p(f"BALL events: {be.height}; BALL players (distinct nfl_id): {B['nfl_id'].n_unique()}; BALL drill_types: {dict(be.group_by('dtype').len().iter_rows())}.")
    chk = be.join(A.select("event_id", pl.col("nfl_id").alias("pid"), "combine_position"), on="event_id", how="left")
    same = chk.filter(pl.col("bid") == pl.col("pid")).height
    p(f"BALL nfl_id equals the PLAYER nfl_id of the same event in {same} of {chk.height} BALL events. BALL-athlete combine_position: {dict(chk.group_by('combine_position').agg(pl.col('bid').n_unique()).iter_rows())}.")
    tot_wr_te = A.filter(pl.col("drill_type").is_in(["SKILL_DRILLS_WR", "SKILL_DRILLS_TE"])).height
    t = be.join(A.select("event_id", "drill_name", "draft_year"), on="event_id").group_by("dtype", "draft_year").agg(pl.len().alias("ball_attempts")).sort("dtype", "draft_year")
    tbl(t)
    t = be.join(A.select("event_id", "drill_name", "drill_type"), on="event_id").group_by("drill_type", "drill_name").agg(pl.len().alias("ball_attempts")).join(
        A.group_by("drill_type", "drill_name").len().rename({"len": "all_attempts"}), on=["drill_type", "drill_name"]).sort("drill_type", "drill_name")
    p(f"Of {tot_wr_te} WR+TE skill attempts, {be.height} have BALL frames. Ball coverage by drill:")
    tbl(t)
    ok = be.height == 551 and B["nfl_id"].n_unique() == 54 and set(be["dtype"]) <= {"SKILL_DRILLS_WR", "SKILL_DRILLS_TE"} and same == chk.height
    claims.append(("2", "BALL: nfl_id = athlete; 551 attempts, WR/TE only, 54 players", "CONFIRMED" if ok else "PARTLY/CONTRADICTED",
                   f"{be.height} attempts, {B['nfl_id'].n_unique()} players, types {sorted(set(be['dtype']))}; BALL nfl_id == PLAYER nfl_id in {same}/{chk.height} events (semantics 'athlete' is inferred from this)"))

    # ---- 3
    h(3, "G3. `dis` understates distance in change-of-direction drills?")
    p("Per attempt: sum_dis = sum of `dis`; sum_xy = sum of frame-to-frame Euclidean x/y distance; sum_s = sum of s*0.1. Medians (and mean) across attempts; ratios are medians of per-attempt ratios. The sums include every frame (first frame has no x/y step).")
    def row(g):
        return g.select(pl.len().alias("attempts"), pl.col("sum_dis").median().alias("dis_med"), pl.col("sum_xy").median().alias("xy_med"), pl.col("sum_s").median().alias("s_med"),
                        pl.col("sum_dis").mean().alias("dis_mean"), pl.col("sum_xy").mean().alias("xy_mean"), pl.col("sum_s").mean().alias("s_mean"),
                        (pl.col("sum_dis") / pl.col("sum_xy")).median().alias("dis/xy"), (pl.col("sum_s") / pl.col("sum_xy")).median().alias("s*0.1/xy"),
                        pl.col("net_disp").median().alias("net_disp_med"))
    t = A.group_by("drill_type").map_groups(lambda g: row(g).with_columns(pl.lit(g["drill_type"][0]).alias("drill_type"))).select("drill_type", pl.all().exclude("drill_type")).sort("drill_type")
    tbl(t, 2)
    p("Same for the three standard tests by draft_year:")
    t = A.filter(pl.col("drill_type").is_in(["FORTY_YARD_DASH", "THREE_CONE_DRILL", "SHORT_SHUTTLE"])).group_by("drill_type", "draft_year").map_groups(
        lambda g: row(g).with_columns(pl.lit(g["drill_type"][0]).alias("drill_type"), pl.lit(g["draft_year"][0]).alias("draft_year"))).select("drill_type", "draft_year", pl.all().exclude("drill_type", "draft_year")).sort("drill_type", "draft_year")
    tbl(t, 2)
    dd = A.group_by("drill_type").agg((pl.col("sum_dis") / pl.col("sum_xy")).median().alias("r")).sort("drill_type")
    sh = A.filter(pl.col("drill_type") == "SHORT_SHUTTLE").select(pl.col("sum_dis").median(), pl.col("sum_xy").median(), pl.col("sum_s").median())
    tc = A.filter(pl.col("drill_type") == "THREE_CONE_DRILL").select(pl.col("sum_dis").median(), pl.col("sum_xy").median(), pl.col("sum_s").median())
    fo = A.filter(pl.col("drill_type") == "FORTY_YARD_DASH").select(pl.col("sum_dis").median(), pl.col("sum_xy").median(), pl.col("sum_s").median())
    ratios = {r["drill_type"]: r["r"] for r in dd.to_dicts()}
    ok3 = ratios["SHORT_SHUTTLE"] < 0.5 and ratios["THREE_CONE_DRILL"] < 0.5 and ratios["FORTY_YARD_DASH"] > 0.8
    fm = lambda g: g.select(pl.col("sum_dis").mean().alias("a"), pl.col("sum_xy").mean().alias("b"), pl.col("sum_s").mean().alias("c")).row(0)
    mshu = fm(A.filter(pl.col("drill_type") == "SHORT_SHUTTLE")); m3c = fm(A.filter(pl.col("drill_type") == "THREE_CONE_DRILL")); m40 = fm(A.filter(pl.col("drill_type") == "FORTY_YARD_DASH"))
    claims.append(("3", "dis understates distance in COD drills (~5.7 vs ~15 shuttle; ~7.7 vs ~22.6 3-cone; ~36 vs ~40.5 forty)",
                   "CONFIRMED (numbers reproduce); also true beyond COD drills, see E4b" if ok3 else "CONTRADICTED",
                   f"mean sum dis / sum xy / sum s*0.1: shuttle {mshu[0]:.1f}/{mshu[1]:.1f}/{mshu[2]:.1f}; 3-cone {m3c[0]:.1f}/{m3c[1]:.1f}/{m3c[2]:.1f}; forty {m40[0]:.1f}/{m40[1]:.1f}/{m40[2]:.1f}; "
                   f"median per-attempt dis/xy: shuttle {ratios['SHORT_SHUTTLE']:.2f}, 3-cone {ratios['THREE_CONE_DRILL']:.2f}, forty {ratios['FORTY_YARD_DASH']:.2f}; s*0.1 matches xy within ~1-2%"))

    # ---- 4
    h(3, "G4. Coordinates and field bounds")
    allr = F.select(pl.col("x").min().alias("a"), pl.col("x").max().alias("b"), pl.col("y").min().alias("c"), pl.col("y").max().alias("d")).row(0)
    nout = F.filter((pl.col("x") < 0) | (pl.col("x") > FIELD_X) | (pl.col("y") < 0) | (pl.col("y") > FIELD_Y))
    p(f"PLAYER overall range: x [{allr[0]:.2f}, {allr[1]:.2f}], y [{allr[2]:.2f}, {allr[3]:.2f}]. Frames outside x 0-120 / y 0-53.33: {nout.height} ({pct(nout.height / F.height)}) in {nout['event_id'].n_unique()} attempts.")
    p("Per-drill_type percentile ranges of x and y (frames):")
    tbl(F.group_by("drill_type").agg(pl.col("x").quantile(0.001).alias("x_p0.1"), pl.col("x").quantile(0.5).alias("x_p50"), pl.col("x").quantile(0.999).alias("x_p99.9"), pl.col("x").min().alias("x_min"), pl.col("x").max().alias("x_max"),
                                    pl.col("y").quantile(0.001).alias("y_p0.1"), pl.col("y").quantile(0.5).alias("y_p50"), pl.col("y").quantile(0.999).alias("y_p99.9"), pl.col("y").min().alias("y_min"), pl.col("y").max().alias("y_max")).sort("drill_type"))
    bb = B.select(pl.col("x").min().alias("a"), pl.col("x").max().alias("b"), pl.col("y").min().alias("c"), pl.col("y").max().alias("d")).row(0)
    p(f"BALL range: x [{bb[0]:.2f}, {bb[1]:.2f}], y [{bb[2]:.2f}, {bb[3]:.2f}].")
    by = nout.group_by("drill_type").agg(pl.len().alias("frames_out"), pl.col("event_id").n_unique().alias("attempts_out")).sort("drill_type")
    tbl(by) if by.height else p("No out-of-bounds PLAYER frames.")
    f40y = F.filter(pl.col("drill_type") == "FORTY_YARD_DASH")
    claims.append(("4", "Game coordinates (x 0-120, y 0-53.33) but can fall outside", "CONFIRMED, but 'can' understates it: the 40 lane itself is out of bounds",
                   f"{nout.height} frames ({pct(nout.height / F.height)}) in {nout['event_id'].n_unique()} of {N_EVENTS} attempts are outside; x range [{allr[0]:.1f},{allr[1]:.1f}], y range [{allr[2]:.1f},{allr[3]:.1f}]; "
                   f"{pct((f40y['y'] < 0).mean())} of 40-yard frames have y<0 (lane y median {f40y['y'].median():.2f}), so every 40 attempt is partly outside the 0-53.33 band; shuttle and 3-cone sit at x~87-104 (different part of the 120-yd frame)"))

    # ---- 5
    h(3, "G5. 40-yard dash geometry")
    f40 = A.filter(pl.col("drill_type") == "FORTY_YARD_DASH")
    p(f"40 attempts: {f40.height}; players: {f40['nfl_id'].n_unique()}.")
    qs = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    rows = []
    for c in ["x_first", "x_last", "x_min", "x_max", "y_first", "y_last", "dur", "frames", "lead_s", "trail_s"]:
        rows.append((c, *[float(f40[c].quantile(v)) for v in qs]))
    tbl(pl.DataFrame(rows, schema=["stat", *[f"p{int(v * 100)}" for v in qs]], orient="row"))
    dirsign = f40.with_columns(((pl.col("x_last") - pl.col("x_first")).sign()).alias("sg")).group_by("draft_year", "sg").len().sort("draft_year", "sg")
    p("Sign of (x_last - x_first), i.e. direction of travel, by year:")
    tbl(dirsign)
    fs = forty_times(MOVE_THR)
    fs1 = forty_times(1.0)
    p(f"Attempts where radial distance from the onset position reaches 40 yd (s>=0.5 onset): {fs['t40'].is_not_nan().sum()} of {fs.height}. Onset position x percentiles (p5/p50/p95): "
      f"{fs['x_onset'].quantile(0.05):.1f} / {fs['x_onset'].median():.1f} / {fs['x_onset'].quantile(0.95):.1f}; end-of-recording x: {fs['x_end'].quantile(0.05):.1f} / {fs['x_end'].median():.1f} / {fs['x_end'].quantile(0.95):.1f}; "
      f"max radial distance from onset (median) {fs['max_radial'].median():.1f} yd.")
    s0 = F.filter((pl.col("drill_type") == "FORTY_YARD_DASH") & (pl.col("i") == 0))["s"]
    claims.append(("5", "40 runs x~10 to x~50; frames span start to end; no official start timestamp",
                   "PARTLY: geometry confirmed; 'start to end' holds only as a tight crop around the run",
                   f"x_first median {f40['x_first'].median():.1f} (p5-p95 {f40['x_first'].quantile(0.05):.1f}-{f40['x_first'].quantile(0.95):.1f}), x_last median {f40['x_last'].median():.1f} (p5-p95 {f40['x_last'].quantile(0.05):.1f}-{f40['x_last'].quantile(0.95):.1f}); "
                   f"direction always +x ({(f40['x_last'] > f40['x_first']).sum()}/{f40.height}); recording median {f40['dur'].median():.1f}s; {pct(f40['starts_moving'].mean())} of 40s already have s>=0.5 at frame 0 (median first-frame s {s0.median():.2f} yd/s), median stationary lead {f40['lead_s'].median():.2f}s and trail {f40['trail_s'].median():.2f}s; "
                   f"no start timestamp column exists (verified by schema)"))

    # ---- 6
    h(3, "G6. Official forty / ten_yd_split vs tracked attempts")
    from scipy import stats
    p("Tracking-derived times per attempt, three definitions (all use 10 Hz linear interpolation). (R) radial: time for the athlete to get 10 / 40 yd (Euclidean) away from the onset position, onset = first frame with s >= threshold. "
      "(XF) x-crossing from first frame: time from the first recorded frame until x reaches 20 / 50 (i.e. 10 / 40 yd beyond a start line at x=10). (XO) same but timed from the onset frame. "
      "Per player the best (minimum) tracked attempt is compared with the official value. offset = tracking minus official.")
    q40 = f40.select("event_id", "nfl_id", "draft_year")
    off = cr.select("nfl_id", "draft_year", "forty", "ten_yd_split")
    variants = [("R, onset s>=0.5", fs, "t10", "t40"), ("R, onset s>=1.0", fs1, "t10", "t40"),
                ("XF (x=20 / x=50 from first frame)", fs, "t20f", "t50f"), ("XO s>=0.5 (x=20 / x=50 from onset)", fs, "t20o", "t50o"),
                ("XO s>=1.0", fs1, "t20o", "t50o")]
    res_rows = []
    store = {}
    for label, fsx, c10, c40 in variants:
        a40 = q40.join(fsx.select("event_id", c10, c40), on="event_id")
        best = a40.group_by("nfl_id").agg(pl.col(c40).min().alias("b40"), pl.col(c10).min().alias("b10"), pl.len().alias("att"))
        m = best.join(off.select("nfl_id", "draft_year", "forty", "ten_yd_split"), on="nfl_id")
        for tag, bc, oc in [("40", "b40", "forty"), ("10", "b10", "ten_yd_split")]:
            mm = m.filter(pl.col(oc).is_not_null() & pl.col(bc).is_not_null() & pl.col(bc).is_not_nan())
            d = mm[bc] - mm[oc]
            r = stats.pearsonr(mm[bc].to_numpy(), mm[oc].to_numpy())[0]
            rho = stats.spearmanr(mm[bc].to_numpy(), mm[oc].to_numpy())[0]
            slope, icpt = np.polyfit(mm[oc].to_numpy(), mm[bc].to_numpy(), 1)
            res_rows.append((label, tag, mm.height, r, rho, d.median(), d.mean(), d.std(), d.quantile(0.05), d.quantile(0.95), float((d < 0).mean()), slope, icpt))
            store[(label, tag)] = (mm, d, r)
    tbl(pl.DataFrame(res_rows, schema=["definition", "dist", "n_players", "pearson", "spearman", "offset_median", "offset_mean", "offset_sd", "offset_p5", "offset_p95", "share_track_faster", "ols_slope", "ols_icpt"], orient="row"), 3)
    p("Rows with dist=40 compare against `forty`; dist=10 against `ten_yd_split`. 'n_players' is limited to players with a tracked 40, an official value and a valid tracking time. "
      "Radial definitions fail to reach 40 yd for some attempts (the recording ends near x=51 whereas the onset position is x~10.7), which is why the x-crossing definitions are included.")
    p("Reached 40 yd radially from onset (s>=0.5): " + f"{int(fs['t40'].is_not_nan().sum())} of {fs.height} attempts; reached x=50: {int(fs['t50f'].is_not_nan().sum())} of {fs.height}.")
    keyL = "XF (x=20 / x=50 from first frame)"
    mm, d_, r_ = store[(keyL, "40")]
    mm = mm.with_columns((pl.col("b40") - pl.col("forty")).alias("off"))
    p(f"Detail for {keyL}, 40 yd. Offset by draft year:")
    tbl(mm.group_by("draft_year").agg(pl.len().alias("n"), pl.col("off").median().alias("median_offset"), pl.col("off").std().alias("sd_offset"), pl.corr("b40", "forty").alias("r")).sort("draft_year"), 3)
    p("Offset by number of tracked attempts (if official = best of the player's runs, more tracked attempts => tracking-best closer to official):")
    tbl(mm.group_by("att").agg(pl.len().alias("n"), pl.col("off").median().alias("median_offset"), pl.col("off").std().alias("sd_offset")).sort("att"), 3)
    a_all = f40.select("event_id", "nfl_id").join(fs.select("event_id", "t50f"), on="event_id").join(off.select("nfl_id", "forty"), on="nfl_id").filter(pl.col("forty").is_not_null() & pl.col("t50f").is_not_nan())
    med_off = float(d_.median())
    cl = a_all.with_columns((pl.col("t50f") - pl.col("forty") - med_off).abs().alias("r")).group_by("nfl_id").agg(pl.col("r").min().alias("rmin"), pl.len().alias("att"))
    p("Is any single tracked attempt a clean match to the official time? For each player the smallest |tracking - official - median offset| over their tracked attempts (XF definition), by number of tracked attempts. "
      "If official times were matchable to an attempt after a constant offset, these residuals would be ~0.01 s:")
    tbl(cl.group_by("att").agg(pl.len().alias("players"), pl.col("rmin").median().alias("median_min_abs_residual"), pl.col("rmin").quantile(0.9).alias("p90_min_abs_residual"), (pl.col("rmin") < 0.03).mean().alias("share_within_0.03s")).sort("att"), 3)
    pair = a_all.group_by("nfl_id").agg(pl.col("t50f").sort().alias("ts")).filter(pl.col("ts").list.len() == 2).with_columns((pl.col("ts").list.get(1) - pl.col("ts").list.get(0)).alias("diff"))
    p(f"For players with two tracked 40 attempts (n={pair.height}), slower minus faster attempt (XF): median {pair['diff'].median():.3f} s, p90 {pair['diff'].quantile(0.9):.3f} s, max {pair['diff'].max():.3f} s "
      "(the between-attempt spread is a benchmark for how large a within-player matching error could be).")
    p("Initial / final speed in the 40 recordings (yd/s), first and last frame: " + "; ".join(
        f"{lab} p10/p50/p90 = {a_.quantile(0.1):.2f}/{a_.median():.2f}/{a_.quantile(0.9):.2f}" for lab, a_ in
        [("first-frame s", F.filter((pl.col('drill_type') == 'FORTY_YARD_DASH') & (pl.col('i') == 0))['s']), ("last-frame s", F.filter((pl.col('drill_type') == 'FORTY_YARD_DASH') & (pl.col('i') == pl.col('n') - 1))['s'])]))
    res = {(r[0], r[1]): r for r in res_rows}
    claims.append(("6", "Official forty/ten_yd_split are best attempt, not matchable to a tracked attempt", "PARTLY: consistent with, not proof of, 'best attempt'; tracking-vs-official relation measured",
                   f"XF 40yd: n={res[(keyL,'40')][2]}, r={res[(keyL,'40')][3]:.3f}, median offset {res[(keyL,'40')][5]:+.3f}s, SD {res[(keyL,'40')][7]:.3f}s; radial s>=0.5: n={res[('R, onset s>=0.5','40')][2]}, r={res[('R, onset s>=0.5','40')][3]:.3f}, offset {res[('R, onset s>=0.5','40')][5]:+.3f}s; "
                   f"10yd XF: r={res[(keyL,'10')][3]:.3f}, offset {res[(keyL,'10')][5]:+.3f}s"))

    # ---- 7
    h(3, "G7. DL PASS_RUSH_DRILL layout")
    R, L = (45.0, 23.75), (45.0, 30.25)
    for dtype in ("SKILL_DRILLS_DL", "SKILL_DRILLS_LB"):
        pr = A.filter((pl.col("drill_type") == dtype) & (pl.col("drill_name") == "PASS_RUSH_DRILL"))
        if pr.height == 0:
            continue
        pr = pr.with_columns(
            ((pl.col("x_first") - R[0]) ** 2 + (pl.col("y_first") - R[1]) ** 2).sqrt().alias("dR"),
            ((pl.col("x_first") - L[0]) ** 2 + (pl.col("y_first") - L[1]) ** 2).sqrt().alias("dL"),
        ).with_columns(
            pl.when(pl.col("dR") < pl.col("dL")).then(pl.lit("right (45,23.75)")).otherwise(pl.lit("left (45,30.25)")).alias("side"),
            pl.min_horizontal("dR", "dL").alias("dmin"),
        )
        p(f"**{dtype} / PASS_RUSH_DRILL**: attempts {pr.height}, players {pr['nfl_id'].n_unique()}.")
        tbl(pr.group_by("draft_year", "side").agg(pl.len().alias("reps"), pl.col("nfl_id").n_unique().alias("players"), pl.col("dmin").median().alias("median_dist_to_nearest_start"),
                                                  pl.col("dmin").quantile(0.9).alias("p90_dist"), (pl.col("dmin") < 1).mean().alias("share_within_1yd"), (pl.col("dmin") < 2).mean().alias("share_within_2yd"),
                                                  pl.col("y_max").median().alias("y_max_med"), pl.col("y_min").median().alias("y_min_med"), pl.col("y_last").median().alias("y_last_med")).sort("draft_year", "side"), 2)
        p("First-frame position summary by side (x, y percentiles p5/p50/p95):")
        tbl(pr.group_by("side").agg(pl.col("x_first").quantile(0.05).alias("x_p5"), pl.col("x_first").median().alias("x_p50"), pl.col("x_first").quantile(0.95).alias("x_p95"),
                                    pl.col("y_first").quantile(0.05).alias("y_p5"), pl.col("y_first").median().alias("y_p50"), pl.col("y_first").quantile(0.95).alias("y_p95")).sort("side"), 2)
        coarse = pr.with_columns(pl.col("x_first").round(0).alias("xr"), pl.col("y_first").round(0).alias("yr")).group_by("xr", "yr").len().sort("len", descending=True).head(8)
        p("Most common first-frame cells (rounded to 1 yd):")
        tbl(coarse)
        p("Overall nearest-start distance percentiles (yd): " + ", ".join(f"p{int(v * 100)}={pr['dmin'].quantile(v):.2f}" for v in [0.1, 0.5, 0.9, 0.99]) + f", max={pr['dmin'].max():.2f}.")
        # max excursion toward finish
        rt = pr.filter(pl.col("side").str.starts_with("right"))
        lt = pr.filter(pl.col("side").str.starts_with("left"))
        p(f"Right-side reps: share with y_max >= 39: {(rt['y_max'] >= 39).mean():.3f}, share with y_max >= 36: {(rt['y_max'] >= 36).mean():.3f}; left-side reps: share with y_min <= 15: {(lt['y_min'] <= 15).mean():.3f}, share <= 18: {(lt['y_min'] <= 18).mean():.3f}.")
        # players with both sides
        ps = pr.group_by("nfl_id").agg(pl.col("side").n_unique().alias("ns"), pl.len().alias("k"))
        p(f"Players with reps on both sides: {(ps['ns'] == 2).sum()} of {ps.height}; players with >=2 reps: {(ps['k'] >= 2).sum()}.")
        if dtype == "SKILL_DRILLS_DL":
            dl_pr = pr
    cnt = dl_pr.group_by("side").len()
    close = float((dl_pr["dmin"] < 2).mean())
    right_n = int(cnt.filter(pl.col("side").str.starts_with("right"))["len"][0]); left_n = int(cnt.filter(pl.col("side").str.starts_with("left"))["len"][0])
    per_year = dl_pr.group_by("draft_year", "side").len().sort("draft_year", "side")
    rt_, lt_ = dl_pr.filter(pl.col("side").str.starts_with("right")), dl_pr.filter(pl.col("side").str.starts_with("left"))
    claims.append(("7", "DL PASS_RUSH_DRILL: starts near (45,23.75) = right and (45,30.25) = left; finish through y=39 / y=15",
                   "CONFIRMED (starts are ~0.5-1.5 yd from the stated points, systematically at x~44.5)" if close > 0.95 else "PARTLY/CONTRADICTED",
                   f"{pct(close)} of {dl_pr.height} DL reps within 2 yd of the nearer point (median {dl_pr['dmin'].median():.2f} yd, p99 {dl_pr['dmin'].quantile(0.99):.2f}); right {right_n} / left {left_n} reps; "
                   f"right reps y_max>=39: {pct((rt_['y_max'] >= 39).mean())}; left reps y_min<=15: {pct((lt_['y_min'] <= 15).mean())}; by year (right/left): " +
                   "; ".join(f"{yr}: {dict((s_.split(' ')[0], n_) for y_, s_, n_ in per_year.iter_rows() if y_ == yr)}" for yr in (2023, 2024, 2025)) +
                   "; LB PASS_RUSH_DRILL (2023, 4 players) starts at x~42.8, ~3 yd from these points"))

    h(3, "G-summary")
    tbl(pl.DataFrame(claims, schema=["#", "claim", "verdict", "evidence"], orient="row"))


# ============================================================================= H. extras
def sec_H():
    h(2, "H. Additional observations")
    # attempts per drill type for players, fractions
    p("Observations that affect analysis (each backed by a table above; wording is my reading of those tables):")
    for line in [
        "1. Drill naming and content drift across years (C2): LINE/LINE_DRILL, PASS_PRO_MIRROR/PASS_PRO-MIRROR, OVER_THE_SHOULDER_ADJUST/OVER_SHOULDER_ADJUST, SPEED_OUT_LEFT/SPEED_OUT_ROUTE_LEFT look like renames; "
        "SHORT_ZONE_BREAKS (2023-24) is split into three named variants in 2025; POST_CORNER_ROUTE_LEFT is absent in 2025; CIRCUS_ROUTE_LEFT exists only in 2025; END_ZONE_FADE_RIGHT (TE) only 2024-25; TE CORNER_ROUTE has a single 2023 attempt (not really collected that year).",
        "2. `attempt` means different things by year (F1b): per drill_name in 2023/24, a running count within drill_type in 2025. Roughly 5-8% of 2023/24 player x drill_name groups and 25% of 2025 player x drill_type groups are missing some attempt numbers (an earlier or middle attempt is absent from the file).",
        "3. Most 'two attempts of the same drill_name' are NOT repeats under the same condition (C5): PASS_RUSH_DRILL (DL), BACK_PEDAL_AND_TRANSITION_45 and LINE_DRILL (DB), GAUNTLET_DRILL (WR/TE) and TE CORNER_ROUTE start in different places (all pairs begin >3 yd apart, apparently left/right or alternate variants). "
        "Genuine same-start repeats: 40-yard dash (375 players), OL PASS_RUSH_DROP (117), 3-cone (33), shuttle (33 with 79% start within 3 yd), small WR route and RUN_THE_HOOP counts (8-15 each).",
        "4. In 2023/24 SHORT_ZONE_BREAKS pools several variants under one name (3-5 attempts per DL player), so those multiple attempts are different breaks, not repeats.",
        "5. The 40-yard recording is a tight crop (G5): about 5.0 s, first frame mostly already moving at ~0.6 yd/s, last frame at full speed (~10.5 yd/s) with no deceleration captured, ending at x~51. Time-to-40 from tracking therefore sits ~0.2-0.3 s above the official time (G6) and the offset differs by year (2025 larger).",
        "6. `dis` is not a distance: it scales roughly with speed squared (E4b; log-log slope ~2.06, R^2 0.98), so it under-reads at every speed below ~11 yd/s, including in route and DL/OL drills (ratio 0.25-0.6), not only in change-of-direction tests. Use x/y or s*0.1 (both agree within ~1-2%).",
        "7. `a` is never negative (E5): it is an acceleration magnitude, so deceleration cannot be read from its sign; derive signed along-track acceleration from s or from x/y. `dir` follows atan2(dx, dy) in degrees (0 = +y, clockwise toward +x), matching x/y motion within about 0.5 degree median absolute difference (E6). `s` equals the centred x/y speed (corr 0.999).",
        "8. BALL rows exist only for the 2025 class (G2), so any ball-relative analysis cannot use 2023/2024 players. Ball frame count differs from the player's in 34 of 551 attempts (F).",
        "9. Coordinates are drill-specific: the 40 lane is y~-0.8 (outside 0-53.33), shuttle at x~87-104, y~10-19, 3-cone at x~94-102, y~46-54; skill drills range over x~1-91 with y from about -7 to 66 (G4). Position-based features must be made relative to each drill's start, and some drills need mirroring (H table).",
        "10. Duration/cropping of the same drill varies by year (C1): e.g. BACK_PEDAL_AND_TRANSITION_45 median 11.5 / 5.9 / 10.0 s (2023/24/25), SLANT_ROUTE_LEFT 4.5 / 4.2 / 2.7 s, FIVE_YARD_WAVE 15.8 / 16.0 / 12.1 s. Windows may include different numbers of reps or different crop rules; check before pooling years.",
        "11. Tracked vs official availability (D2): official time present but no tracked attempt for 6 players (40), 30 (3-cone), 41 (shuttle); tracked attempt but null official time for 10 (3-cone) and 10 (shuttle). 'Null = opted out' is therefore not exactly the same as 'did not run in the tracked session'.",
        "12. Small samples: tracked 3-cone covers 160 players (DB 24, WR 24, TE 19, DL 45, OL 48) and tracked shuttle 170 (DB 28, WR 29, TE 21, DL 38, OL 54); only 38 and 42 of them have two or more attempts. No QB/RB/LB/S-specific position groups exist: combine_position has only WR, TE, OL, DL, DB (safeties are in DB; OLB are in DL; ILB/MLB/RB are in DB).",
        "13. Four DL-labelled players (2023: three DE and one OLB by nfl_position) did LB skill drills (SKILL_DRILLS_LB, 2023 only); LB PASS_RUSH_DRILL starts at x~42.8, not at the DL start points.",
        "14. Quality is otherwise very clean: perfectly regular 0.1 s sampling, no nulls, no duplicate timestamps, no implausible speeds (max s 11.85 yd/s in a 40), no duplicate trajectories. The only odd attempts found are a few too-short/too-long shuttle and 3-cone recordings (E9).",
        "15. Cohort: 127 of 510 players are undrafted (44/36/47 by class), no TE went in round 1 (cohort), all five nfl_position='DB' players are undrafted, and one TE is labelled WR by combine_position, one FB is TE, one RB and 3 ILB/MLB are DB (A4).",
    ]:
        p(line)
    p("Shuffled / mirrored geometry: start-point and direction normalisation by drill_name (first-frame position percentiles; useful to see whether a drill needs mirroring):")
    sk = A.group_by("drill_type", "drill_canon").agg(
        pl.col("x_first").quantile(0.1).alias("x0_p10"), pl.col("x_first").median().alias("x0_p50"), pl.col("x_first").quantile(0.9).alias("x0_p90"),
        pl.col("y_first").quantile(0.1).alias("y0_p10"), pl.col("y_first").median().alias("y0_p50"), pl.col("y_first").quantile(0.9).alias("y0_p90"),
        pl.len().alias("attempts")).sort("drill_type", "drill_canon")
    tbl(sk, 1)
    p("Players by total number of tracked attempts (all drills), bins of 5:")
    t = A.group_by("nfl_id").len().with_columns(((pl.col("len") - 1) // 5 * 5 + 1).alias("attempts_from")).group_by("attempts_from").agg(pl.len().alias("players"), pl.col("len").max().alias("max_in_bin")).sort("attempts_from")
    tbl(t)
    p("Quick unit check -- mean player speed in 40 (yd/s) and top speed percentiles in the 40 per attempt (max s):")
    t = F.filter(pl.col("drill_type") == "FORTY_YARD_DASH").group_by("event_id").agg(pl.col("s").max().alias("smax")).select(
        pl.col("smax").quantile(0.05).alias("p5"), pl.col("smax").median().alias("p50"), pl.col("smax").quantile(0.95).alias("p95"), pl.col("smax").max().alias("max"))
    tbl(t)


def main():
    OUT.append("# Combine data audit\n\nGenerated by `scripts/audit/audit_combine.py` (all numbers computed from `data/processed/*.parquet`; aggregates only).\n")
    OUT.append(f"Tables: players {players.shape}, combine_results {cr.shape}, combine_tracking {trk.shape[0]} rows x {trk.shape[1]-1} cols. Nominal sampling 0.1 s; 'moving' threshold s >= {MOVE_THR} yd/s.\n")
    for fn in (sec_A, sec_B, sec_C, sec_C5, sec_D, sec_E, sec_E9, sec_F, sec_G, sec_H):
        print("running", fn.__name__, file=sys.stderr)
        fn()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(OUT), encoding="utf-8")
    print("wrote", REPORT, file=sys.stderr)


if __name__ == "__main__":
    main()
