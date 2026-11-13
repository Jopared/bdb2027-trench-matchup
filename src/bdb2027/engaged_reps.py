"""Engaged pass-protection reps: pairs, engagement flags, rep context, baselines, sealed outcomes.

Step 2 of the pre-registered design (reports/candidates_v2.md 3.5). Everything here is built from the
Parquet tables alone (optionally reusing a frame cache). Outcome columns are routed to a separate
"sealed" table (`split_outcomes`); no function in this module relates outcomes to anything.

Definitions (frozen; see reports/dataset_build.md):
  * pair: (game_id, play_id, blocker, rusher) on a REG/POST dropback (pass_result != ''),
    lined_up_position != 'NA' for both; blocker = player_play row with pressure_allowed non-null;
    rusher = row with blitzing == True on the opposing team (team_abbr differs).
  * window: ball_snap + 0.2 s .. min(ball_snap + 3.0 s, first pass_forward, first qb_sack)
    (missing tags are ignored by the minimum, so a play with no pass_forward and no sack is
    cut at snap + 3.0 s).
  * engaged(thr, k): at least k frames in the window, with both players tracked at the same time,
    having Euclidean x/y distance <= thr yards.
"""
from __future__ import annotations

import os
from typing import Iterable

import polars as pl

from bdb2027 import paths

KEYS = ["game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id"]
VARIANTS = {  # name -> (distance threshold yd, min frames)
    "primary": (1.5, 4),
    "d125": (1.25, 4),
    "d200": (2.0, 4),
    "k3": (1.5, 3),
    "k6": (1.5, 6),
}
SNAP_START_MS = 200
SNAP_CAP_MS = 3000
PLAY_ACTION_TAGS = ("play_action", "autoevent_playaction")
UNDRAFTED_PICK = 262
OFFICIAL_MEASURES = ["combine_weight", "arm_length", "forty", "ten_yd_split", "short_shuttle", "three_cone"]
BLOCKER_OUTCOMES = ["pressure_allowed", "peak_pressure_probability_allowed", "sack_allowed",
                    "time_to_pressure_allowed"]
RUSHER_OUTCOMES = ["rusher_time_to_pressure", "rusher_quick_pressure", "rusher_sack"]


# ------------------------------------------------------------------ pairs
def build_pairs() -> pl.DataFrame:
    """All co-occurring blocker/rusher pairs on REG+POST dropbacks, with context and outcomes.

    Outcome columns are present here (needed to key the sealed file) and must be removed with
    `split_outcomes` before anything is written to the open file.
    """
    pp = pl.read_parquet(paths.parquet("player_play"))
    games = pl.read_parquet(paths.parquet("games")).select(
        "game_id", "season", "season_type", "week", "home_team_abbr", "visitor_team_abbr")
    cr = pl.read_parquet(paths.parquet("combine_results")).select("nfl_id", "combine_position")
    pl_ = pl.read_parquet(paths.parquet("players")).select("nfl_id", "nfl_position")
    pos = cr.join(pl_, on="nfl_id", how="full", coalesce=True)

    d = (pp.filter((pl.col("pass_result") != "") & (pl.col("lined_up_position") != "NA"))
           .join(games, on="game_id"))
    blk = d.filter(pl.col("pressure_allowed").is_not_null()).select(
        "game_id", "play_id",
        pl.col("nfl_id").alias("blocker_nfl_id"), pl.col("team_abbr").alias("blocker_team"),
        pl.col("lined_up_position").alias("blocker_lined_up_position"),
        "season", "season_type", "week", "home_team_abbr", "visitor_team_abbr",
        "dropback_duration", "pass_rushers_encountered", "down", "yards_to_go", "quarter",
        "offense_formation", "play_direction", "play_nullified_by_penalty",
        "pre_snap_home_score", "pre_snap_visitor_score",
        "pre_snap_home_team_win_probability", "pre_snap_visitor_team_win_probability",
        "pressure_allowed", "peak_pressure_probability_allowed", "sack_allowed",
        "time_to_pressure_allowed")
    rsh = d.filter(pl.col("blitzing") == True).select(  # noqa: E712
        "game_id", "play_id",
        pl.col("nfl_id").alias("rusher_nfl_id"), pl.col("team_abbr").alias("rusher_team"),
        pl.col("lined_up_position").alias("rusher_lined_up_position"),
        pl.col("time_to_pressure").alias("rusher_time_to_pressure"),
        pl.col("quick_pressure").alias("rusher_quick_pressure"),
        pl.col("sack").alias("rusher_sack"))
    pairs = blk.join(rsh, on=["game_id", "play_id"]).filter(pl.col("blocker_team") != pl.col("rusher_team"))
    pairs = pairs.filter(pl.col("season_type").is_in(["REG", "POST"]))

    off_home = pl.col("blocker_team") == pl.col("home_team_abbr")
    pairs = pairs.with_columns(
        pl.when(off_home).then(pl.col("pre_snap_home_score") - pl.col("pre_snap_visitor_score"))
          .otherwise(pl.col("pre_snap_visitor_score") - pl.col("pre_snap_home_score")).alias("score_diff_offense"),
        pl.when(off_home).then(pl.col("pre_snap_home_team_win_probability"))
          .otherwise(pl.col("pre_snap_visitor_team_win_probability")).alias("offense_win_prob"),
        pl.col("offense_formation").is_in(["SHOTGUN", "EMPTY"]).alias("shotgun"),
        (pl.col("offense_formation") == "PISTOL").alias("pistol"),
    ).with_columns(
        pl.when(pl.col("offense_formation").is_null()).then(None).otherwise(pl.col("shotgun")).alias("shotgun"),
        pl.when(pl.col("offense_formation").is_null()).then(None).otherwise(pl.col("pistol")).alias("pistol"),
    ).drop("home_team_abbr", "visitor_team_abbr", "pre_snap_home_score", "pre_snap_visitor_score",
           "pre_snap_home_team_win_probability", "pre_snap_visitor_team_win_probability")
    for side, col in (("blocker", "blocker_nfl_id"), ("rusher", "rusher_nfl_id")):
        p = pos.select(pl.col("nfl_id").alias(col), pl.col("combine_position").alias(f"{side}_combine_position"),
                       pl.col("nfl_position").alias(f"{side}_nfl_position"))
        pairs = pairs.join(p, on=col, how="left")
    return pairs


# ------------------------------------------------------------------ frames
def load_frames(pairs: pl.DataFrame, cache: str | None = None) -> pl.DataFrame:
    """Tracking frames (game_id, play_id, nfl_id, time, x, y, event) for every player in `pairs`,
    all frames of their plays. Read from the Parquet files; `cache` (optional) is a Parquet file of
    the same layout produced earlier (it is not written here)."""
    if cache and os.path.exists(cache):
        return pl.read_parquet(cache)
    keys = pl.concat([
        pairs.select("game_id", "play_id", pl.col("blocker_nfl_id").alias("nfl_id")),
        pairs.select("game_id", "play_id", pl.col("rusher_nfl_id").alias("nfl_id")),
    ]).unique()
    parts = []
    for y in (2023, 2024, 2025):
        lf = pl.scan_parquet(paths.parquet(f"game_tracking_{y}")).select(
            "game_id", "play_id", "nfl_id", "time", "x", "y", "event")
        parts.append(lf.join(keys.lazy(), on=["game_id", "play_id", "nfl_id"], how="semi").collect())
    return pl.concat(parts)


def play_events(fr: pl.DataFrame, play_keys: pl.DataFrame) -> pl.DataFrame:
    """Per play: first ball_snap / pass_forward / qb_sack time, play-action flag, window bounds.
    Plays without a ball_snap tag are dropped."""
    ev = play_keys
    for e_ in ("ball_snap", "pass_forward", "qb_sack"):
        ev = ev.join(fr.filter(pl.col("event") == e_).group_by("game_id", "play_id")
                       .agg(pl.col("time").min().alias(e_)), on=["game_id", "play_id"], how="left")
    pa = (fr.filter(pl.col("event").is_in(PLAY_ACTION_TAGS)).select("game_id", "play_id").unique()
            .with_columns(pl.lit(True).alias("play_action")))
    ev = (ev.join(pa, on=["game_id", "play_id"], how="left")
            .with_columns(pl.col("play_action").fill_null(False)))
    ev = ev.filter(pl.col("ball_snap").is_not_null()).with_columns(
        pl.min_horizontal(pl.col("ball_snap") + pl.duration(milliseconds=SNAP_CAP_MS),
                          pl.col("pass_forward"), pl.col("qb_sack")).alias("t_end"),
        (pl.col("ball_snap") + pl.duration(milliseconds=SNAP_START_MS)).alias("t_start"))
    return ev


# ------------------------------------------------------------------ engagement
def engagement(pairs: pl.DataFrame, fr: pl.DataFrame, ev: pl.DataFrame) -> pl.DataFrame:
    """Per pair: n_common_frames, n_close_{150,125,200}, min_dist, and engaged_<variant> flags."""
    w = (fr.join(ev.select("game_id", "play_id", "t_start", "t_end"), on=["game_id", "play_id"])
           .filter((pl.col("time") >= pl.col("t_start")) & (pl.col("time") <= pl.col("t_end")))
           .select("game_id", "play_id", "nfl_id", "time", "x", "y"))
    a = w.rename({"nfl_id": "blocker_nfl_id", "x": "xo", "y": "yo"})
    b = w.rename({"nfl_id": "rusher_nfl_id", "x": "xr", "y": "yr"})
    pj = (pairs.select(KEYS)
          .join(a, on=["game_id", "play_id", "blocker_nfl_id"])
          .join(b, on=["game_id", "play_id", "rusher_nfl_id", "time"])
          .with_columns(((pl.col("xo") - pl.col("xr")) ** 2 + (pl.col("yo") - pl.col("yr")) ** 2).sqrt().alias("d")))
    cnt = pj.group_by(KEYS).agg(
        pl.len().alias("n_common_frames"),
        (pl.col("d") <= 1.5).sum().alias("n_close_150"),
        (pl.col("d") <= 1.25).sum().alias("n_close_125"),
        (pl.col("d") <= 2.0).sum().alias("n_close_200"),
        pl.col("d").min().alias("min_dist"))
    out = pairs.select(KEYS).join(cnt, on=KEYS, how="left")
    for c in ("n_common_frames", "n_close_150", "n_close_125", "n_close_200"):
        out = out.with_columns(pl.col(c).fill_null(0).cast(pl.Int64))
    out = out.with_columns(
        (pl.col("n_close_150") >= 4).alias("engaged_primary"),
        (pl.col("n_close_125") >= 4).alias("engaged_d125"),
        (pl.col("n_close_200") >= 4).alias("engaged_d200"),
        (pl.col("n_close_150") >= 3).alias("engaged_k3"),
        (pl.col("n_close_150") >= 6).alias("engaged_k6"))
    return out


def backward_displacement(pairs: pl.DataFrame, fr: pl.DataFrame, ev: pl.DataFrame) -> pl.DataFrame:
    """Blocker displacement 'backward' (toward own QB) at snap+0.5 s and +1.0 s, in yards.

    Offence moves toward decreasing x when play_direction == 'left', so backward = +x (left) or -x (right):
    disp = sign * (x(snap + t) - x(snap)), sign = +1 for left, -1 for right. Null when play_direction is
    null or a frame at exactly that timestamp is missing. Frames after a sack/pass_forward are used
    as long as they exist (tracking continues ~1 s after the last event)."""
    bl = pairs.select("game_id", "play_id", "blocker_nfl_id", "play_direction").unique()
    f = fr.rename({"nfl_id": "blocker_nfl_id"}).select("game_id", "play_id", "blocker_nfl_id", "time", "x")
    base = (bl.join(ev.select("game_id", "play_id", "ball_snap"), on=["game_id", "play_id"])
              .join(f.rename({"time": "ball_snap", "x": "x0"}), on=["game_id", "play_id", "blocker_nfl_id", "ball_snap"],
                    how="left"))
    sign = pl.when(pl.col("play_direction") == "left").then(1.0).when(pl.col("play_direction") == "right").then(-1.0)
    for ms, nm in ((500, "05"), (1000, "10")):
        tt = base.select("game_id", "play_id", "blocker_nfl_id",
                         (pl.col("ball_snap") + pl.duration(milliseconds=ms)).alias("time"))
        xt = tt.join(f, on=["game_id", "play_id", "blocker_nfl_id", "time"], how="left").rename({"x": f"x_{nm}"})
        base = base.join(xt.select("game_id", "play_id", "blocker_nfl_id", f"x_{nm}"),
                         on=["game_id", "play_id", "blocker_nfl_id"], how="left")
        base = base.with_columns((sign * (pl.col(f"x_{nm}") - pl.col("x0"))).alias(f"blocker_back_disp_{nm}s"))
    return base.select("game_id", "play_id", "blocker_nfl_id", "blocker_back_disp_05s", "blocker_back_disp_10s")


# ------------------------------------------------------------------ assemble
OUTCOME_COLS = BLOCKER_OUTCOMES + RUSHER_OUTCOMES


def build_engaged_pairs(cache: str | None = None) -> tuple[pl.DataFrame, dict]:
    """Return (full pairs table incl. outcome columns, diagnostics dict).

    Pairs on plays without a ball_snap tag are dropped (diagnostics['dropped_no_snap'])."""
    pairs = build_pairs()
    n_all = pairs.height
    fr = load_frames(pairs, cache)
    play_keys = pairs.select("game_id", "play_id").unique()
    ev = play_events(fr, play_keys)
    pairs = pairs.join(ev.select("game_id", "play_id"), on=["game_id", "play_id"], how="semi")
    diag = {"pairs_before_snap_filter": n_all, "dropped_no_snap": n_all - pairs.height,
            "plays": pairs.select("game_id", "play_id").unique().height,
            "plays_without_pass_forward_tag": ev.filter(pl.col("pass_forward").is_null()).height,
            "plays_total_with_snap": ev.height}
    eng = engagement(pairs, fr, ev)
    disp = backward_displacement(pairs, fr, ev)
    pairs = (pairs.join(eng, on=KEYS)
                  .join(ev.select("game_id", "play_id", "play_action"), on=["game_id", "play_id"])
                  .join(disp, on=["game_id", "play_id", "blocker_nfl_id"], how="left"))
    # double team under the primary definition: other engaged cohort blockers with the same rusher on the play
    n_eng = (pairs.filter(pl.col("engaged_primary")).group_by("game_id", "play_id", "rusher_nfl_id")
                  .agg(pl.len().alias("_n_eng")))
    pairs = (pairs.join(n_eng, on=["game_id", "play_id", "rusher_nfl_id"], how="left")
                  .with_columns((pl.col("_n_eng").fill_null(0) - pl.col("engaged_primary").cast(pl.Int64))
                                .alias("n_other_engaged_blockers"))
                  .drop("_n_eng")
                  .with_columns((pl.col("n_other_engaged_blockers") >= 1).alias("double_team")))
    return pairs.sort(KEYS), diag


OPEN_COLUMNS = [
    "game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id",
    "engaged_primary", "engaged_d125", "engaged_d200", "engaged_k3", "engaged_k6",
    "n_common_frames", "n_close_150", "n_close_125", "n_close_200", "min_dist",
    "n_other_engaged_blockers", "double_team",
    "season", "season_type", "week", "blocker_team", "rusher_team",
    "blocker_lined_up_position", "rusher_lined_up_position",
    "blocker_combine_position", "blocker_nfl_position", "rusher_combine_position", "rusher_nfl_position",
    "dropback_duration", "down", "yards_to_go", "quarter", "offense_formation", "shotgun", "pistol",
    "play_action", "pass_rushers_encountered", "score_diff_offense", "offense_win_prob",
    "play_nullified_by_penalty", "blocker_back_disp_05s", "blocker_back_disp_10s",
]


def split_outcomes(pairs: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(open table without any outcome column, sealed outcome table keyed by KEYS)."""
    open_ = pairs.select(OPEN_COLUMNS)
    sealed = pairs.select(KEYS + OUTCOME_COLS)
    assert not set(OUTCOME_COLS) & set(open_.columns)
    return open_, sealed


# ------------------------------------------------------------------ baselines
def build_player_baselines() -> pl.DataFrame:
    """One row per cohort player (the 510 rows of players/combine_results)."""
    cr = pl.read_parquet(paths.parquet("combine_results"))
    pl_ = pl.read_parquet(paths.parquet("players")).select(
        "nfl_id", pl.col("draft_year").alias("draft_year_players"), "nfl_position", "draft_overall_pick")
    b = cr.join(pl_, on="nfl_id", how="full", coalesce=True)
    b = b.with_columns(
        pl.col("draft_overall_pick").is_null().alias("undrafted"),
        pl.col("draft_overall_pick").fill_null(UNDRAFTED_PICK).alias("draft_overall_pick"),
        pl.coalesce("draft_year", "draft_year_players").alias("draft_year"))
    b = b.with_columns(pl.col("draft_overall_pick").cast(pl.Float64).log().alias("log_pick"))
    b = b.with_columns([pl.col(c).is_null().alias(f"{c}_missing") for c in OFFICIAL_MEASURES + ["ngs_athleticism_score"]])
    cols = (["nfl_id", "draft_overall_pick", "undrafted", "log_pick", "draft_year", "combine_position", "nfl_position"]
            + OFFICIAL_MEASURES + [f"{c}_missing" for c in OFFICIAL_MEASURES]
            + ["ngs_athleticism_score", "ngs_athleticism_score_missing"])
    return b.select(cols).sort("nfl_id")
