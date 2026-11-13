"""Build the engaged-rep analysis dataset (step 2 of the pre-registered design).

Run from repo root:  .venv\\Scripts\\python.exe scripts\\build_engaged_reps.py [--cache path_to_frames.parquet]

Writes data/processed/{engaged_pairs,player_baselines,engaged_outcomes_SEALED}.parquet and
reports/dataset_build.md. No model is fitted. The only outcome-related numbers produced are the
count of engaged (primary) reps with pressure_allowed true and the base rate, computed in memory
before the sealed file is written; the sealed file is never read back except for key columns.
"""
from __future__ import annotations

import argparse

import numpy as np
import polars as pl

from bdb2027 import engaged_reps as er
from bdb2027 import paths

ap = argparse.ArgumentParser()
ap.add_argument("--cache", default=None, help="optional frame cache (same layout) to skip the tracking scan")
args = ap.parse_args()

OUT = paths.PROCESSED_DIR
REPORT = paths.REPO_ROOT / "reports" / "dataset_build.md"

pairs, diag = er.build_engaged_pairs(args.cache)
open_, sealed = er.split_outcomes(pairs)
base = er.build_player_baselines()

# outcome-related numbers allowed by the brief, computed in memory before sealing
prim = pairs.filter(pl.col("engaged_primary"))
n_press = int(prim["pressure_allowed"].sum())
base_rate = float(prim["pressure_allowed"].mean())
n_press_null = int(prim["pressure_allowed"].null_count())
del prim

open_.write_parquet(OUT / "engaged_pairs.parquet")
base.write_parquet(OUT / "player_baselines.parquet")
sealed.write_parquet(OUT / "engaged_outcomes_SEALED.parquet")

# verification of the sealed file: row count and key uniqueness only (key columns, no outcomes)
sk = pl.scan_parquet(OUT / "engaged_outcomes_SEALED.parquet").select(er.KEYS).collect()
sealed_rows, sealed_unique = sk.height, sk.unique().height
open_unique = open_.select(er.KEYS).unique().height
assert sealed_rows == open_.height == sealed_unique == open_unique

# ------------------------------------------------------------------ report
L: list[str] = []


def md(df: pl.DataFrame) -> str:
    cols = df.columns
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.iter_rows():
        out.append("| " + " | ".join(str(v) if c in ("season", "week") else (f"{v:,.3f}" if isinstance(v, float) else (f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else str(v))) for c, v in zip(cols, r)) + " |")
    return "\n".join(out)


def q(s: pl.Series) -> str:
    v = np.percentile(s.to_numpy(), [0, 25, 50, 75, 90, 100])
    return f"min {v[0]:.0f} / p25 {v[1]:.0f} / median {v[2]:.0f} / p75 {v[3]:.0f} / p90 {v[4]:.0f} / max {v[5]:.0f}; mean {s.mean():.2f}"


ex = er.VARIANTS
L.append("# Engaged-rep dataset build (step 2 of the pre-registered design)\n")
L.append("Code: `src/bdb2027/engaged_reps.py`, `scripts/build_engaged_reps.py` (rebuilds from the Parquet files; "
         f"frame cache used: {'yes (' + args.cache + ')' if args.cache else 'no, rebuilt from game_tracking_*.parquet'}). "
         "No model was fitted. Outcomes are in `data/processed/engaged_outcomes_SEALED.parquet` and were not opened (only its key columns were read for the row/uniqueness check).\n")

L.append("## 1. Definitions and filters\n")
L.append("""- **Plays**: `player_play` rows with `pass_result != ''` (dropbacks; the empty string is the non-dropback marker) and `lined_up_position != 'NA'` (pre-snap-penalty rows), joined to `games` for `season`, `season_type`, `week`. Kept `season_type` in REG, POST (PRE dropped).
- **Blocker**: row with `pressure_allowed` non-null (a pass-block snap), any lined-up position (so TE/RB/FB blockers are in the pairs table; the T/G/C restriction is a column filter). **Rusher**: row with `blitzing == True` on the opposing team (`team_abbr` differs), any alignment. Both are cohort players (all `player_play` rows are cohort players with Combine data).
- **Pair** = every (game, play, blocker, rusher) co-occurrence. The table has one row per pair, engaged or not, so the selection checks and the non-engaged placebo are possible.
- **Window**: `ball_snap` + 0.2 s to the earliest of `ball_snap` + 3.0 s, first `pass_forward`, first `qb_sack` (event tags read from the tracking frames of the pair players; they are play-level). Missing tags are ignored by the minimum: a play with no `pass_forward` and no sack is cut at snap + 3.0 s (decision, identical to the feasibility script). `qb_strip_sack` is not used. Pairs on plays with no `ball_snap` tag are dropped.
- **Distance**: Euclidean x/y between the two players at identical timestamps (10 Hz; frame spacing verified in the audit). **Engaged(thr, k)** = at least k such frames with d <= thr. Primary 1.5 yd / 4 frames; sensitivity 1.25 yd, 2.0 yd (k = 4), and k = 3, k = 6 (1.5 yd). Pairs with no overlapping frame in the window are non-engaged (`n_common_frames` = 0, `min_dist` null).
- **Double team**: `n_other_engaged_blockers` = number of OTHER pairs on the same play and rusher that are engaged under the PRIMARY definition (self excluded); `double_team` = that count >= 1. It is defined for non-engaged pairs too (count of primary-engaged cohort blockers with that rusher). Only cohort blockers are visible, so true double teams are understated.
- **Play action**: any `play_action` or `autoevent_playaction` event tag among the loaded frames of the play.
- **Shotgun**: `offense_formation` in SHOTGUN or EMPTY (decision); `pistol` is a separate flag; both null when formation is null.
- **Score differential / win probability**: offence minus defence pre-snap score, and offence pre-snap win probability, with the offence = the blocker's team (home/visitor decided from `games`).
- **Backward displacement**: blocker x at snap + 0.5 s / + 1.0 s minus x at the snap frame, signed so that backward is +x when `play_direction == 'left'` and -x when 'right' (`blocker_back_disp_05s`, `blocker_back_disp_10s`, yards). Null if `play_direction` is null or no frame exists at exactly that timestamp. Frames after the window end (pass thrown, sack) are used if they exist.
- **Player baselines**: one row per cohort player (510). `draft_overall_pick` null -> 262 with `undrafted` flag, `log_pick` = ln(pick), `draft_year` from combine_results (players as fallback), a `<measure>_missing` flag for each of combine_weight, arm_length, forty, ten_yd_split, short_shuttle, three_cone and for ngs_athleticism_score. Tracking-derived composites are NOT in this file (traits.py owns them).
- **Not included on purpose** (they would leak the outcome into the open file): sack tag, window end source, window length. `dropback_duration`, `play_nullified_by_penalty` are included as pre-specified/rep-context columns; both are set by what happens on the play and so are related to the outcome, as in the pre-registered covariate list.
""")

L.append("## 2. Reproduction of the feasibility counts\n")
e0 = open_.filter(pl.col("engaged_primary"))
L.append(md(pl.DataFrame({
    "quantity": ["co-occurring pairs (REG+POST)", "pairs before dropping no-snap plays", "engaged reps, primary",
                 "distinct engaged blockers, primary", "distinct engaged rushers, primary"],
    "this build": [open_.height, diag["pairs_before_snap_filter"], e0.height,
                   e0["blocker_nfl_id"].n_unique(), e0["rusher_nfl_id"].n_unique()],
    "feasibility_c3.md": [29269, 29271, 8271, 107, 129]})))
ok = open_.height == 29269 and e0.height == 8271
L.append(f"\nMatch: **{'YES' if ok else 'NO'}**. Dropped for missing `ball_snap`: {diag['dropped_no_snap']} pair(s). Plays in the table: {diag['plays']:,}; plays without a `pass_forward` tag: {diag['plays_without_pass_forward_tag']:,} of {diag['plays_total_with_snap']:,} ({diag['plays_without_pass_forward_tag'] / diag['plays_total_with_snap']:.1%}).\n")

L.append("## 3. Engaged reps, blockers, rushers by definition (REG+POST)\n")
rows = []
for nm, (thr, k) in ex.items():
    e = open_.filter(pl.col(f"engaged_{nm}"))
    bc = e.group_by("blocker_nfl_id").len()["len"]
    rc = e.group_by("rusher_nfl_id").len()["len"]
    rows.append(dict(definition=f"{nm} ({thr} yd / {k} fr)", engaged_reps=e.height,
                     of_which_REG=e.filter(pl.col("season_type") == "REG").height,
                     distinct_blockers=e["blocker_nfl_id"].n_unique(), distinct_rushers=e["rusher_nfl_id"].n_unique(),
                     blockers_ge10=int((bc >= 10).sum()), rushers_ge10=int((rc >= 10).sum()),
                     engagement_rate_of_pairs=e.height / open_.height))
L.append(md(pl.DataFrame(rows)))
L.append("")

L.append("## 4. Primary engaged reps by season and by position\n")
L.append(md(e0.group_by("season").agg(pl.len().alias("engaged_reps"), pl.col("blocker_nfl_id").n_unique().alias("blockers"),
                                     pl.col("rusher_nfl_id").n_unique().alias("rushers")).sort("season")))
L.append("\nAll pairs by season (engagement rate):\n")
L.append(md(open_.group_by("season").agg(pl.len().alias("pairs"), pl.col("engaged_primary").mean().alias("engaged_share")).sort("season")))
L.append("\nBlocker `lined_up_position` x rusher `lined_up_position` (primary engaged reps):\n")
ct = (e0.group_by("blocker_lined_up_position", "rusher_lined_up_position").len()
        .pivot(on="rusher_lined_up_position", index="blocker_lined_up_position", values="len").fill_null(0))
ct = ct.with_columns(pl.sum_horizontal(pl.exclude("blocker_lined_up_position")).alias("total")).sort("total", descending=True)
L.append(md(ct))
tgc = e0.filter(pl.col("blocker_lined_up_position").is_in(["T", "G", "C"]))
dl_ = pl.col("rusher_combine_position") == "DL"
al_ = pl.col("rusher_lined_up_position").is_in(["EDGE", "INTERIOR_LINE"])
sets = {
    "T/G/C blocker": tgc,
    "T/G/C blocker, rusher combine_position DL": tgc.filter(dl_),
    "T/G/C blocker, rusher aligned EDGE/INTERIOR_LINE": tgc.filter(al_),
    "T/G/C blocker, DL rusher aligned EDGE/INTERIOR_LINE (section 3.3 analysis set before composites)": tgc.filter(dl_ & al_),
}
L.append("\nShare of primary engaged reps in the section 3.3 sub-sets (composites not applied; they come from traits.py):\n")
L.append(md(pl.DataFrame([dict(subset=k, reps=v.height, share_of_engaged=v.height / e0.height,
                                blockers=v["blocker_nfl_id"].n_unique(), rushers=v["rusher_nfl_id"].n_unique())
                          for k, v in sets.items()])))
L.append("\nBlocker `combine_position` x rusher `combine_position` (primary engaged):\n")
L.append(md(e0.group_by("blocker_combine_position", "rusher_combine_position").len().sort("len", descending=True)))
L.append("\nRusher `nfl_position` (primary engaged):\n")
L.append(md(e0.group_by("rusher_nfl_position").len().sort("len", descending=True)))

L.append("\n## 5. Reps per blocker, rusher and dyad (primary engaged reps)\n")
bc = e0.group_by("blocker_nfl_id").len()["len"]
rc = e0.group_by("rusher_nfl_id").len()["len"]
dc = e0.group_by("blocker_nfl_id", "rusher_nfl_id").len()["len"]
L.append(f"- per blocker ({len(bc)} blockers): {q(bc)}; top-10 blockers hold {bc.sort(descending=True)[:10].sum() / bc.sum():.1%} of reps")
L.append(f"- per rusher ({len(rc)} rushers): {q(rc)}; top-10 rushers hold {rc.sort(descending=True)[:10].sum() / rc.sum():.1%} of reps")
L.append(f"- per dyad ({len(dc)} dyads): {q(dc)}; dyads with >= 2 reps: {(dc >= 2).sum()}")
tb = tgc.filter(dl_ & al_)
L.append(f"- section 3.3 sub-set (T/G/C vs DL EDGE/INTERIOR_LINE): per blocker {q(tb.group_by('blocker_nfl_id').len()['len'])}; "
         f"per rusher {q(tb.group_by('rusher_nfl_id').len()['len'])}; dyads {tb.select('blocker_nfl_id', 'rusher_nfl_id').unique().height}")
L.append("\nDouble teams (primary definition): ")
dt_units = e0.group_by("game_id", "play_id", "rusher_nfl_id").agg(pl.col("double_team").any())
L.append(f"{int(e0['double_team'].sum()):,} of {e0.height:,} engaged reps ({e0['double_team'].mean():.1%}) are flagged; {int(dt_units['double_team'].sum()):,} of {dt_units.height:,} engaged (play, rusher) units ({dt_units['double_team'].mean():.1%}).\n")

L.append("## 6. Covariate missingness\n")
cov = ["dropback_duration", "down", "yards_to_go", "quarter", "offense_formation", "shotgun", "pistol", "play_action",
       "pass_rushers_encountered", "score_diff_offense", "offense_win_prob", "play_nullified_by_penalty",
       "blocker_back_disp_05s", "blocker_back_disp_10s", "blocker_combine_position", "rusher_combine_position",
       "blocker_nfl_position", "rusher_nfl_position", "min_dist", "week"]
L.append(md(pl.DataFrame([dict(column=c, null_all_pairs=int(open_[c].null_count()),
                               null_primary_engaged=int(e0[c].null_count()),
                               pct_null_engaged=e0[c].null_count() / e0.height) for c in cov])))
L.append(f"\n`play_direction` null count is visible through the two displacement columns. Decision for rows with missing `dropback_duration` or other covariates: **none dropped here**; every row is kept and the analyst decides (the pre-registration must state the rule). Rows with any null among the listed covariates (primary engaged): {e0.filter(pl.any_horizontal(pl.col(cov).is_null())).height:,}.\n")
L.append("Formation counts (primary engaged): " + ", ".join(f"{r[0]}={r[1]}" for r in e0.group_by("offense_formation").len().sort("len", descending=True).iter_rows()) + ".\n")
L.append(f"Play-action share among primary engaged reps: {e0['play_action'].mean():.1%}; shotgun/empty share {e0['shotgun'].mean():.1%}.\n")

L.append("### Player baselines\n")
inplay = set(e0["blocker_nfl_id"].to_list()) | set(e0["rusher_nfl_id"].to_list())
bb = base.filter(pl.col("nfl_id").is_in(list(inplay)))
L.append(f"`player_baselines.parquet`: {base.height} rows, {base['nfl_id'].n_unique()} distinct players; {int(base['undrafted'].sum())} undrafted. "
         f"{bb.height} players appear in primary engaged reps. Missing shares (all players / players in engaged reps):\n")
L.append(md(pl.DataFrame([dict(column=c, missing_all=int(base[c].null_count()), pct_all=base[c].null_count() / base.height,
                               missing_in_engaged=int(bb[c].null_count()), pct_in_engaged=bb[c].null_count() / bb.height)
                          for c in er.OFFICIAL_MEASURES + ["ngs_athleticism_score", "draft_year", "combine_position", "nfl_position"]])))

L.append("\n## 7. Outcome file (sealed)\n")
L.append(f"`engaged_outcomes_SEALED.parquet`: {sealed_rows:,} rows (one per pair, same keys as `engaged_pairs.parquet`), keys unique: {sealed_unique == sealed_rows}; "
         f"columns {er.OUTCOME_COLS}. Only the allowed populated-check numbers, computed in memory before writing: "
         f"primary engaged reps with `pressure_allowed` true = **{n_press:,}** (base rate **{base_rate:.4f}**; null outcomes among engaged reps: {n_press_null}). Nothing else about outcomes was computed.\n")

REPORT.write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
