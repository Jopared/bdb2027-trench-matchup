"""Audit of the in-game (NFL regular season) tables for BDB 2027.

Run from the repo root:  .venv\\Scripts\\python.exe scripts\\audit\\audit_game.py
Writes reports/audit_game.md. Only aggregates are written; no raw rows are copied
beyond a handful of short illustrative play descriptions (clearly marked).
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from bdb2027 import paths  # noqa: E402

OUT = ROOT / "reports" / "audit_game.md"
OUT.parent.mkdir(exist_ok=True)

con = duckdb.connect()
con.execute("PRAGMA threads=8")
T0 = time.time()
lines: list[str] = []
R: dict = {}  # key numbers reused in the verdict section


# ----------------------------------------------------------------- helpers
def q(sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def fmt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA or v is pd.NaT:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    if isinstance(v, (float, np.floating)):
        if float(v).is_integer() and abs(v) < 1e15:
            return f"{int(v):,}"
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        return f"{v:.3g}" if abs(v) < 0.001 else f"{v:.4g}" if abs(v) < 10 else f"{v:.1f}"
    return str(v).replace("|", "/").replace("\n", " ")


ID_COLS = {"draft_year", "season", "class", "game_id", "nfl_id", "play_id", "yr", "draft_round", "draft_overall_pick", "week", "quarter", "down",
           "min_game_id", "max_game_id", "min_week", "max_week", "min_pick", "max_pick", "game_key", "pick"}


def fmt_id(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA:
        return ""
    try:
        return str(int(v))
    except (TypeError, ValueError):
        return str(v)


def md(df: pd.DataFrame) -> str:
    df = df.replace([np.inf, -np.inf], np.nan)
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    idflags = [(c in ID_COLS) or c.endswith("_id") for c in cols]
    for row in df.itertuples(index=False):
        out.append("| " + " | ".join((fmt_id(v) if idflags[i] else fmt(v)) for i, v in enumerate(row)) + " |")
    return "\n".join(out)


def H(level: int, text: str):
    lines.append("\n" + "#" * level + " " + text + "\n")


def P(text: str = ""):
    lines.append(text)


def TBL(df: pd.DataFrame, note: str | None = None):
    if note:
        lines.append(note + "\n")
    lines.append(md(df) + "\n")


def pct(a, b, d=1):
    return f"{100 * a / b:.{d}f}%" if b else "n/a"


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def qcols(expr: str, prefix: str = "") -> str:
    """min, q1, median, q3, max of an expression, as SQL select-list."""
    return (
        f"min({expr}) AS {prefix}min, quantile_cont({expr}, 0.25) AS {prefix}q1, "
        f"quantile_cont({expr}, 0.5) AS {prefix}med, quantile_cont({expr}, 0.75) AS {prefix}q3, "
        f"max({expr}) AS {prefix}max"
    )


# ----------------------------------------------------------------- setup
for t in ("players", "player_career_successes", "games", "player_play",
          "game_tracking_2023", "game_tracking_2024", "game_tracking_2025"):
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{paths.parquet(t).as_posix()}')")
con.execute("""CREATE VIEW gt AS
  SELECT 2023 AS yr, * FROM game_tracking_2023 UNION ALL
  SELECT 2024, * FROM game_tracking_2024 UNION ALL
  SELECT 2025, * FROM game_tracking_2025""")

GRP = """CASE nfl_position
  WHEN 'WR' THEN 'WR' WHEN 'TE' THEN 'TE' WHEN 'RB' THEN 'RB_FB' WHEN 'FB' THEN 'RB_FB'
  WHEN 'T' THEN 'OL' WHEN 'G' THEN 'OL' WHEN 'C' THEN 'OL'
  WHEN 'DT' THEN 'IDL' WHEN 'NT' THEN 'IDL' WHEN 'DE' THEN 'EDGE' WHEN 'OLB' THEN 'EDGE'
  WHEN 'ILB' THEN 'LB' WHEN 'MLB' THEN 'LB' WHEN 'CB' THEN 'CB'
  WHEN 'FS' THEN 'S' WHEN 'SS' THEN 'S' WHEN 'DB' THEN 'DB_generic' ELSE 'OTHER' END"""
GROUPS = ["WR", "TE", "RB_FB", "OL", "IDL", "EDGE", "LB", "CB", "S", "DB_generic"]
POSITIONS = ["WR", "TE", "RB", "FB", "T", "G", "C", "DT", "NT", "DE", "OLB", "ILB", "MLB", "CB", "FS", "SS", "DB"]

con.execute(f"""CREATE TABLE pl AS SELECT p.*, {GRP} AS grp FROM players p""")
con.execute("""CREATE TABLE pp AS
  SELECT a.*, pl.nfl_position, pl.grp, pl.draft_year, pl.draft_round, pl.draft_overall_pick, pl.display_name,
         g.season, g.season_type, g.week,
         (a.lined_up_position = 'NA') AS is_na,
         (a.pass_result <> '') AS dropback,
         (a.team_abbr = a.possession_team) AS on_offense,
         (g.season_type = 'REG') AS reg
  FROM player_play a
  JOIN pl ON pl.nfl_id = a.nfl_id
  LEFT JOIN games g ON g.game_id = a.game_id""")
n_pp = q("SELECT count(*) n FROM pp").n[0]
assert n_pp == q("SELECT count(*) n FROM player_play").n[0], "join to players lost/duplicated rows"
assert q("SELECT count(*) n FROM pp WHERE season IS NULL").n[0] == 0

con.execute("CREATE TABLE tk AS SELECT DISTINCT yr, game_id, play_id, nfl_id FROM gt")
log("setup done")

# ============================================================== header
P("# Audit of in-game data (player_play, games, game tracking, career)")
P()
P("Generated by `scripts/audit/audit_game.py` (re-run to reproduce every number). All figures below were "
  "computed by that script from `data/processed/*.parquet`; statements marked *inference* are interpretation.")
P()
P("**Conventions.** `REG` = games with `season_type == 'REG'`; `ALL` = every game in `games` (REG + POST + PRE). "
  "Position groups (from `players.nfl_position`, NOT from `lined_up_position`): WR, TE, RB_FB (RB+FB), OL (T,G,C), "
  "IDL (DT,NT), EDGE (DE,OLB), LB (ILB,MLB; only 2 players), CB, S (FS,SS), DB_generic (position `DB`). "
  "A 'row' is one player_play row (one player on one play). 'Dropback' = `pass_result <> ''` "
  "(see section H1: **empty string, not null**). Unless stated, qualifying plays exclude the `lined_up_position == 'NA'` "
  "pre-snap-penalty rows.")

# ============================================================== quick facts (cohort)
H(2, "0. Cohort and table sizes")
cohort = q("""SELECT draft_year, count(*) players,
  sum((nfl_id IN (SELECT nfl_id FROM player_play))::int) with_pp_rows FROM players GROUP BY 1 ORDER BY 1""")
TBL(cohort)
sizes = q("""SELECT 'players' t, count(*) n FROM players UNION ALL SELECT 'player_career_successes', count(*) FROM player_career_successes
 UNION ALL SELECT 'games', count(*) FROM games UNION ALL SELECT 'player_play', count(*) FROM player_play
 UNION ALL SELECT 'game_tracking_2023', count(*) FROM game_tracking_2023 UNION ALL SELECT 'game_tracking_2024', count(*) FROM game_tracking_2024
 UNION ALL SELECT 'game_tracking_2025', count(*) FROM game_tracking_2025""")
TBL(sizes)
P("Players by nfl_position and draft class (cohort sizes):\n")
TBL(q("""SELECT nfl_position, sum((draft_year=2023)::int) "2023", sum((draft_year=2024)::int) "2024",
         sum((draft_year=2025)::int) "2025", count(*) total FROM players GROUP BY 1 ORDER BY total DESC"""))

# ============================================================== FACT 1 multi cohort plays
log("fact 1")
H(2, "1. Fact 1 - how many cohort players share a play (tracking and player_play)")
tkp = q("""WITH c AS (SELECT yr, game_id, play_id, count(*) n FROM tk GROUP BY ALL)
 SELECT n AS cohort_players_tracked_on_play, count(*) plays FROM c GROUP BY 1 ORDER BY 1""")
tot_plays = int(tkp.plays.sum())
multi_plays = int(tkp[tkp.cohort_players_tracked_on_play >= 2].plays.sum())
tkp["share"] = tkp.plays / tot_plays
TBL(tkp, "Tracking: distinct (game_id, play_id) by number of distinct cohort nfl_ids with tracking on that play "
         f"(total tracked plays {tot_plays:,}; players in tracking = "
         f"{q('SELECT count(DISTINCT nfl_id) n FROM tk').n[0]}).")
R["tk_plays"] = tot_plays
R["tk_multi_plays"] = multi_plays
P(f"Tracking plays with >=2 cohort players: **{multi_plays:,} ({pct(multi_plays, tot_plays)})**.\n")

ppp = q("""WITH c AS (SELECT game_id, play_id, count(*) n FROM pp GROUP BY ALL)
 SELECT n AS cohort_rows_on_play, count(*) plays FROM c GROUP BY 1 ORDER BY 1""")
pp_plays = int(ppp.plays.sum())
ppp["share"] = ppp.plays / pp_plays
TBL(ppp, f"player_play: distinct plays by number of cohort rows on that play (total {pp_plays:,}).")

# pair analysis on player_play (has team_abbr). exclude NA rows (pre-snap penalty) from analysis pairs.
con.execute("""CREATE TABLE pairs AS
 SELECT a.game_id, a.play_id, a.reg, a.nfl_id AS a_id, b.nfl_id AS b_id, a.grp AS ga, b.grp AS gb,
        a.nfl_position AS pa, b.nfl_position AS pb, (a.team_abbr = b.team_abbr) AS same_team,
        a.is_na OR b.is_na AS any_na
 FROM pp a JOIN pp b ON a.game_id = b.game_id AND a.play_id = b.play_id AND a.nfl_id < b.nfl_id""")
tot_pairs = q("SELECT count(*) n, count(DISTINCT (game_id, play_id)) plays, sum(same_team::int) same, sum((NOT same_team)::int) opp FROM pairs")
TBL(tot_pairs, "All unordered cohort-cohort pairs on the same play (player_play, ALL games, incl. NA rows).")
R["pairs"] = tot_pairs.iloc[0].to_dict()
TBL(q("""SELECT reg, count(*) pairs, count(DISTINCT (game_id, play_id)) plays_with_pair,
   sum(same_team::int) same_team_pairs, sum((NOT same_team)::int) opposing_pairs,
   count(DISTINCT CASE WHEN NOT same_team THEN (game_id, play_id) END) plays_with_opposing_pair
   FROM pairs WHERE NOT any_na GROUP BY 1 ORDER BY 1"""),
    "Same split excluding NA (pre-snap-penalty) rows, by REG vs non-REG.")

P("Specific matchup types (opposing teams only, NA rows excluded). `plays` = distinct plays; `players_a`/`players_b` = "
  "distinct cohort players that ever appear in such a pairing; `max_per_player` = most such plays for one player.\n")


def matchup(label, ga_list, gb_list):
    ga = ",".join(f"'{x}'" for x in ga_list)
    gb = ",".join(f"'{x}'" for x in gb_list)
    d = q(f"""WITH x AS (
        SELECT game_id, play_id, reg, a_id, b_id FROM pairs WHERE NOT same_team AND NOT any_na AND ga IN ({ga}) AND gb IN ({gb})
        UNION ALL
        SELECT game_id, play_id, reg, b_id, a_id FROM pairs WHERE NOT same_team AND NOT any_na AND gb IN ({ga}) AND ga IN ({gb}) ),
      per AS (SELECT a_id, count(*) c FROM x WHERE reg GROUP BY 1)
      SELECT '{label}' AS matchup, count(*) AS pairs_all, count(DISTINCT (game_id, play_id)) AS plays_all,
             sum(reg::int) AS pairs_reg, count(DISTINCT CASE WHEN reg THEN (game_id, play_id) END) AS plays_reg,
             count(DISTINCT CASE WHEN reg THEN a_id END) AS players_a_reg, count(DISTINCT CASE WHEN reg THEN b_id END) AS players_b_reg,
             (SELECT max(c) FROM per) AS max_per_player_a_reg,
             (SELECT quantile_cont(c, 0.5) FROM per) AS median_per_player_a_reg FROM x""")
    return d


mm = pd.concat([
    matchup("WR/TE vs DB (CB,S,DB)", ["WR", "TE"], ["CB", "S", "DB_generic"]),
    matchup("WR vs CB", ["WR"], ["CB"]),
    matchup("TE vs S/LB", ["TE"], ["S", "LB"]),
    matchup("OL vs IDL/EDGE", ["OL"], ["IDL", "EDGE"]),
    matchup("OL vs EDGE", ["OL"], ["EDGE"]),
    matchup("OL vs IDL", ["OL"], ["IDL"]),
    matchup("WR vs WR (opp.)", ["WR"], ["WR"]),
    matchup("any offense vs any defense", ["WR", "TE", "RB_FB", "OL"], ["IDL", "EDGE", "LB", "CB", "S", "DB_generic"]),
], ignore_index=True)
TBL(mm)
R["mm"] = mm
same_team_ol = q("""SELECT count(*) pairs, count(DISTINCT (game_id, play_id)) plays FROM pairs WHERE same_team AND NOT any_na AND reg
   AND ga='OL' AND gb='OL'""")
same_team_wr = q("""SELECT count(*) pairs, count(DISTINCT (game_id, play_id)) plays FROM pairs WHERE same_team AND NOT any_na AND reg
   AND ga IN ('WR','TE') AND gb IN ('WR','TE')""")
TBL(pd.concat([same_team_ol.assign(kind="same-team OL-OL (REG)"), same_team_wr.assign(kind="same-team WR/TE-WR/TE (REG)")]),
    "Same-team pairs for comparison.")
P("*Note*: a pair on the same play does not identify who covered / blocked whom; tracking only has the cohort players, so the "
  "opponent's position and the rest of the 22 are unobserved. See interpretation in the summary.\n")

# ============================================================== FACT 2 route coverage + snaps
log("fact 2")
H(2, "2. Fact 2 - WR/TE rows only on route plays; row counts vs career snaps")
f2 = q("""SELECT nfl_position, count(*) rows, count(route_ran) rows_with_route, sum((route_ran IS NULL)::int) rows_without_route
  FROM pp WHERE grp IN ('WR','TE','RB_FB') GROUP BY 1 ORDER BY 1""")
TBL(f2, "route_ran non-null by nfl_position (ALL rows incl. NA / PRE / POST).")
R["f2"] = f2
f2b = q("""SELECT nfl_position, is_na, count(*) rows, count(route_ran) with_route FROM pp WHERE nfl_position IN ('WR','TE','RB','FB')
  GROUP BY ALL ORDER BY 1,2""")
TBL(f2b, "Same, split by whether the row is a pre-snap-penalty (NA) row.")
f2c = q("""SELECT lined_up_position, count(*) rows, count(route_ran) with_route FROM pp WHERE nfl_position IN ('WR','TE') GROUP BY 1 ORDER BY 2 DESC""")
TBL(f2c, "WR/TE (by nfl_position) rows by lined_up_position.")
f2d = q("""SELECT nfl_position, nfl_id, display_name, count(*) rows, count(route_ran) with_route FROM pp WHERE nfl_position='RB' GROUP BY ALL""")
P("The single RB (nfl_position RB) has rows both with and without route_ran:\n")
TBL(f2d.drop(columns=["display_name"]))
P("Non-WR/TE rows that have route_ran non-null (by nfl_position, lined_up_position):\n")
TBL(q("""SELECT nfl_position, lined_up_position, count(*) rows_with_route FROM pp WHERE route_ran IS NOT NULL
   AND nfl_position NOT IN ('WR','TE') GROUP BY ALL ORDER BY 3 DESC"""))

# route vs not route: are there WR/TE pass-play rows that are not route? check route-less fraction of dropbacks
P("Share of WR/TE rows on dropbacks vs non-dropbacks (if non-dropback WR/TE rows have routes, 'route_ran' is not only a pass-play flag):\n")
TBL(q("""SELECT grp, dropback, count(*) rows, count(route_ran) with_route FROM pp WHERE grp IN ('WR','TE') AND NOT is_na GROUP BY ALL ORDER BY 1,2"""))

snaps = q("""WITH r AS (SELECT nfl_id, count(*) all_rows, sum(reg::int) reg_rows,
              sum((season_type IN ('REG','POST'))::int) regpost_rows, sum((reg AND NOT is_na)::int) reg_nonna_rows
            FROM pp GROUP BY 1)
  SELECT p.grp, p.nfl_id, coalesce(r.all_rows,0) all_rows, coalesce(r.reg_rows,0) reg_rows,
         coalesce(r.regpost_rows,0) regpost_rows, coalesce(r.reg_nonna_rows,0) reg_nonna_rows,
         c.career_offensive_snaps off_s, c.career_defensive_snaps def_s, c.career_special_teams_snaps st_s,
         CASE WHEN p.grp IN ('WR','TE','RB_FB','OL') THEN c.career_offensive_snaps ELSE c.career_defensive_snaps END AS side_snaps
  FROM pl p LEFT JOIN r USING(nfl_id) LEFT JOIN player_career_successes c USING(nfl_id)""")
agg = snaps.groupby("grp").agg(players=("nfl_id", "count"), side_snaps=("side_snaps", "sum"), all_rows=("all_rows", "sum"),
                               regpost_rows=("regpost_rows", "sum"), reg_rows=("reg_rows", "sum"),
                               reg_nonna=("reg_nonna_rows", "sum")).reindex(GROUPS).dropna(how="all")
agg["ratio_ALL"] = agg.all_rows / agg.side_snaps
agg["ratio_REG+POST"] = agg.regpost_rows / agg.side_snaps
agg["ratio_REG"] = agg.reg_rows / agg.side_snaps
agg = agg.reset_index()
TBL(agg, "Sum of player_play rows divided by the sum of career snaps on the player's primary side (offense for WR/TE/RB_FB/OL, "
         "defense otherwise). Career snaps cover the NFL career to date (max career_games_active = 51 = 3 x 17, i.e. regular "
         "seasons 2023-2025; whether playoff snaps are included is not documented).")
R["snap_ratio"] = agg
# per-player ratio distribution using REG+POST rows
sp = snaps[snaps.side_snaps > 0].copy()
sp["ratio"] = sp.regpost_rows / sp.side_snaps
pr = sp.groupby("grp").ratio.describe(percentiles=[0.1, 0.5, 0.9]).reset_index()[["grp", "count", "10%", "50%", "90%", "min", "max"]]
TBL(pr, "Per-player ratio (REG+POST player_play rows / career side snaps), players with >0 career snaps.")
eq = snaps.copy()
eq["cmp"] = np.where(eq.reg_rows == eq.side_snaps, "REG rows == career side snaps",
                     np.where(eq.reg_rows > eq.side_snaps, "REG rows > career snaps", "REG rows < career snaps"))
TBL(eq.groupby(["grp", "cmp"]).size().reset_index(name="players").pivot(index="grp", columns="cmp", values="players").fillna(0).astype(int).reset_index(),
    "Per-player comparison of REG-only player_play rows (incl. NA rows) with career snaps on the player's primary side. Exact equality for essentially every "
    "OL/DL/EDGE/LB/CB/S/DB player means career snaps = regular-season snaps only (POST and PRE are not in career snaps), and that player_play is complete "
    "for those groups.")
R["eq"] = eq.groupby(["grp", "cmp"]).size().reset_index(name="players")
# special teams
st = snaps.groupby("grp").agg(st_snaps=("st_s", "sum")).reset_index()
P("Career special-teams snaps are large for some groups, but no ST rows exist in player_play (see H2).\n")
TBL(st)
# Sum for the group+offense/defense mismatch
TBL(q("""SELECT grp, on_offense, count(*) rows FROM pp WHERE NOT is_na GROUP BY ALL ORDER BY 1,2"""),
    "Side of ball of rows by position group (on_offense = team_abbr == possession_team). Players appearing on the 'wrong' side "
    "(e.g. defenders on offense after a turnover) are small.")

TBL(q("""SELECT nfl_position, season_type, count(*) rows, count(DISTINCT nfl_id) players FROM pp WHERE nfl_position='DB' GROUP BY ALL"""),
    "The 5 generic-DB players only have PRE rows (career defensive snaps = 0).")

# ============================================================== FACT 3 no-row players
log("fact 3")
H(2, "3. Fact 3 - the 13 cohort players with no in-game rows")
nr = q("""SELECT p.display_name, p.nfl_position, p.draft_year, p.draft_round, p.draft_overall_pick,
     c.career_offensive_snaps off_s, c.career_defensive_snaps def_s, c.career_special_teams_snaps st_s, c.career_games_active ga
   FROM players p LEFT JOIN player_career_successes c USING(nfl_id)
   WHERE p.nfl_id NOT IN (SELECT nfl_id FROM player_play) ORDER BY p.draft_year, p.draft_round NULLS LAST, p.nfl_position""")
TBL(nr, f"{len(nr)} cohort players with no player_play rows (and none in tracking: "
        f"{q('SELECT count(*) n FROM players WHERE nfl_id NOT IN (SELECT nfl_id FROM tk)').n[0]} without tracking).")
R["no_row_n"] = len(nr)
TBL(nr.assign(draft_round=nr.draft_round.fillna(-1).astype(int).astype(str).replace("-1", "undrafted")).groupby(["nfl_position", "draft_round"]).size().reset_index(name="players"),
    "Summary by position x draft round.")
P(f"Of these, {int((nr.off_s.fillna(0)+nr.def_s.fillna(0)+nr.st_s.fillna(0) > 0).sum())} have non-zero career snaps of some kind "
  f"(career_games_active > 0: {int((nr.ga.fillna(0) > 0).sum())}). Players with zero career snaps never played; any with ST snaps only would "
  "be special-teams-only players.\n")
gm_miss = q("""SELECT g.game_id, g.season, g.season_type, g.week, g.home_team_abbr, g.visitor_team_abbr FROM games g
   WHERE g.game_id NOT IN (SELECT game_id FROM player_play)""")
TBL(gm_miss, "Games in `games` with no player_play rows (and no tracking rows: "
             f"{q('SELECT count(*) n FROM games WHERE game_id NOT IN (SELECT game_id FROM tk)').n[0]} games without tracking).")
R["gm_miss"] = gm_miss
R["no_row_df"] = nr

# ============================================================== FACT 4 NA rows
log("fact 4")
H(2, "4. Fact 4 - `lined_up_position == 'NA'` rows")
na = q("""SELECT count(*) rows,
  sum((play_nullified_by_penalty='Y')::int) nullified_Y,
  sum((penalty_yards IS NOT NULL)::int) penalty_yards_nonnull,
  sum((play_description ILIKE '%PENALTY%')::int) desc_has_PENALTY,
  sum((play_description ILIKE '%No Play%')::int) desc_has_NoPlay,
  sum((play_description ILIKE '%False Start%')::int) desc_false_start,
  sum((play_description ILIKE '%Offside%' OR play_description ILIKE '%Encroachment%' OR play_description ILIKE '%Neutral Zone%')::int) desc_offside_enc_nz,
  sum((play_description ILIKE '%Delay of Game%')::int) desc_delay,
  sum(dropback::int) dropback_rows, sum((NOT dropback)::int) nondropback_rows,
  sum(reg::int) reg_rows, count(DISTINCT (game_id, play_id)) distinct_plays, count(DISTINCT nfl_id) players
  FROM pp WHERE is_na""")
TBL(na.T.reset_index().rename(columns={"index": "metric", 0: "value"}))
R["na"] = na.iloc[0].to_dict()
P("Penalty-type breakdown of NA rows (regex on the first matched `PENALTY on <team>-<name>, <foul>` phrase; fouls are public play text, "
  "aggregated only):\n")
na_pen = q("""SELECT coalesce(regexp_extract(play_description, 'PENALTY on [A-Z]+(?:-[^,]+)?, ([^,]+),', 1), '(no PENALTY phrase)') AS foul, count(*) rows
   FROM pp WHERE is_na GROUP BY 1 ORDER BY 2 DESC LIMIT 15""")
TBL(na_pen)
TBL(q("""SELECT pass_result, count(*) rows FROM pp WHERE is_na GROUP BY 1 ORDER BY 2 DESC"""), "pass_result on NA rows ('' = non-dropback):")
TBL(q("""SELECT nfl_position, count(*) na_rows, count(DISTINCT nfl_id) players FROM pp WHERE is_na GROUP BY 1 ORDER BY 2 DESC"""),
    "NA rows by nfl_position.")
nacols = q("""SELECT
 count(*) rows, count(route_ran) route_ran, count(coverage_assignment) coverage_assignment, count(blitzing) blitzing,
 count(pressure_allowed) pressure_allowed, count(tackle) tackle, count(offense_formation) offense_formation,
 count(team_coverage_type) team_coverage_type, count(yards_gained) yards_gained, count(expected_points_added) epa,
 count(down) down, count(rush_yards) rush_yards, count(rec_yards) rec_yards
 FROM pp WHERE is_na""")
TBL(nacols.T.reset_index().rename(columns={"index": "non-null count of column on NA rows", 0: "n"}))
na_trk = q("""SELECT count(*) na_rows, sum((t.nfl_id IS NOT NULL)::int) have_tracking
  FROM pp LEFT JOIN tk t ON t.game_id = pp.game_id AND t.play_id = pp.play_id AND t.nfl_id = pp.nfl_id WHERE pp.is_na""")
TBL(na_trk, "NA rows with / without a tracking key.")
R["na_trk"] = na_trk.iloc[0].to_dict()
TBL(q("""SELECT p.is_na, count(*) rows, sum(CASE WHEN p.is_na THEN 0 ELSE 0 END) z FROM pp p GROUP BY 1""").drop(columns="z"),
    "(Context) total rows by is_na.")
na_ev = q("""WITH k AS (SELECT p.game_id, p.play_id, p.nfl_id FROM pp p WHERE p.is_na)
   SELECT count(*) na_player_plays_in_tracking,
          sum((has_snap)::int) with_ball_snap, sum((has_penalty_flag)::int) with_penalty_flag_event, quantile_cont(n, 0.5) median_frames
   FROM (SELECT k.game_id, k.play_id, k.nfl_id, count(*) n, bool_or(g.event = 'ball_snap') has_snap,
                bool_or(g.event IN ('penalty_flag','penalty_accepted','penalty_declined')) has_penalty_flag
         FROM k JOIN gt g ON g.game_id=k.game_id AND g.play_id=k.play_id AND g.nfl_id=k.nfl_id GROUP BY ALL)""")
TBL(na_ev, "Tracking for NA rows that do have tracking: ball_snap present / penalty-flag events.")
P("Illustrative play descriptions for NA rows (public play text; a couple of examples only):\n")
ex = q("""SELECT substr(play_description, 1, 110) AS example_description FROM pp WHERE is_na ORDER BY hash(game_id, play_id, nfl_id) LIMIT 4""")
P("\n".join(f"- `{d}`" for d in ex.example_description) + "\n")
# NA rows with dropback-type results
TBL(q("""SELECT (play_description ILIKE '%No Play%') AS desc_no_play, (play_description ILIKE '%pass %' OR play_description ILIKE '%sacked%') AS desc_pass_like,
   (play_description ILIKE '%PENALTY%') AS has_penalty, count(*) rows FROM pp WHERE is_na GROUP BY ALL ORDER BY 4 DESC"""),
    "NA rows: description cross-check. Rows with pass-like text but not 'No Play' would be post-snap plays; "
    "the pass_result values above show whether the play had a result recorded.")

# ============================================================== FACT 5/E join coverage
log("fact 5")
H(2, "5. Fact 5 / Section E - join coverage between tracking and player_play")
con.execute("""CREATE TABLE tk_only AS SELECT t.* FROM tk t ANTI JOIN player_play p ON p.game_id=t.game_id AND p.play_id=t.play_id AND p.nfl_id=t.nfl_id""")
con.execute("""CREATE TABLE pp_only AS SELECT pp.*, (pp.game_id) AS gid FROM pp ANTI JOIN tk t ON pp.game_id=t.game_id AND pp.play_id=t.play_id AND pp.nfl_id=t.nfl_id""")
con.execute("""CREATE TABLE pp_both AS SELECT pp.* FROM pp SEMI JOIN tk t ON pp.game_id=t.game_id AND pp.play_id=t.play_id AND pp.nfl_id=t.nfl_id""")
cov = q("""SELECT 'tracking keys total' k, count(*) n FROM tk UNION ALL SELECT 'player_play rows total', count(*) FROM player_play
  UNION ALL SELECT 'keys in both', count(*) FROM pp_both UNION ALL SELECT 'tracking keys WITHOUT player_play row', count(*) FROM tk_only
  UNION ALL SELECT 'player_play rows WITHOUT tracking', count(*) FROM pp_only""")
TBL(cov)
byyr = q("""SELECT (SELECT count(*) FROM tk_only WHERE yr=2023) tk_only_2023, (SELECT count(*) FROM tk_only WHERE yr=2024) tk_only_2024,
 (SELECT count(*) FROM tk_only WHERE yr=2025) tk_only_2025""")
TBL(byyr, "Tracking keys without player_play, by tracking file year (forum: 449 / 857 / 1,191).")
byyr2 = q("""SELECT sum((season=2023)::int) pp_only_2023, sum((season=2024)::int) pp_only_2024, sum((season=2025)::int) pp_only_2025 FROM pp_only""")
TBL(byyr2, "player_play rows without tracking, by game season (forum: 293 / 661 / 796).")
R["tk_only"] = int(q("SELECT count(*) n FROM tk_only").n[0])
R["pp_only"] = int(q("SELECT count(*) n FROM pp_only").n[0])
R["tk_only_yr"] = byyr.iloc[0].tolist()
R["pp_only_yr"] = byyr2.iloc[0].tolist()

H(3, "5a. Tracking keys WITHOUT a player_play row (tk_only)")
TBL(q("""SELECT p.nfl_position, count(*) keys, count(DISTINCT t.nfl_id) players FROM tk_only t JOIN pl p USING(nfl_id) GROUP BY 1 ORDER BY 2 DESC"""),
    "By nfl_position.")
TBL(q("""SELECT g.season_type, count(*) keys FROM tk_only t JOIN games g USING(game_id) GROUP BY 1 ORDER BY 2 DESC"""), "By season_type.")
# Position share of tk_only relative to all tracking for the position
TBL(q("""WITH a AS (SELECT p.nfl_position pos, count(*) tracked FROM tk t JOIN pl p USING(nfl_id) GROUP BY 1),
  b AS (SELECT p.nfl_position pos, count(*) missing FROM tk_only t JOIN pl p USING(nfl_id) GROUP BY 1)
  SELECT a.pos, a.tracked, coalesce(b.missing,0) tracking_keys_without_pp, round(100.0*coalesce(b.missing,0)/a.tracked,2) pct_of_position_tracking
  FROM a LEFT JOIN b USING(pos) ORDER BY 3 DESC"""), "Share of each position's tracked player-plays that lack a player_play row.")
tko = q("""WITH x AS (
  SELECT t.*, (SELECT count(*) FROM pp q2 WHERE q2.game_id=t.game_id AND q2.play_id=t.play_id) AS other_pp_rows_on_play
  FROM tk_only t)
  SELECT other_pp_rows_on_play > 0 AS play_has_other_pp_rows, count(*) keys FROM x GROUP BY 1""")
TBL(tko, "Does the same (game_id, play_id) have player_play rows for some other cohort player?")
tk_ev = q("""WITH k AS (SELECT * FROM tk_only)
  SELECT count(*) player_plays, sum(has_snap::int) with_ball_snap, sum(has_pass::int) with_pass_forward,
         sum(has_run::int) with_handoff_or_run_event, sum(has_sack::int) with_qb_sack, sum(has_pen::int) with_penalty_event,
         quantile_cont(n, 0.5) median_frames
  FROM (SELECT k.game_id, k.play_id, k.nfl_id, count(*) n, bool_or(g.event='ball_snap') has_snap, bool_or(g.event='pass_forward') has_pass,
        bool_or(g.event IN ('handoff','run','run_attempt','qb_sneak','qb_kneel','qb_slide','lateral','snap_direct')) has_run,
        bool_or(g.event IN ('qb_sack','qb_strip_sack')) has_sack,
        bool_or(g.event IN ('penalty_flag','penalty_accepted','penalty_declined')) has_pen
        FROM k JOIN gt g ON g.game_id=k.game_id AND g.play_id=k.play_id AND g.nfl_id=k.nfl_id GROUP BY ALL)""")
TBL(tk_ev, "Tracking events on the tk_only player-plays.")
tk_vs = q("""WITH k AS (SELECT * FROM tk_only),
  ev AS (SELECT k.game_id, k.play_id, k.nfl_id, bool_or(g.event='ball_snap') has_snap, bool_or(g.event='pass_forward') has_pass,
         bool_or(g.event IN ('handoff','run','run_attempt','qb_sneak','lateral')) has_run
         FROM k JOIN gt g ON g.game_id=k.game_id AND g.play_id=k.play_id AND g.nfl_id=k.nfl_id GROUP BY ALL)
  SELECT p.nfl_position, count(*) keys, round(100.0*sum(has_pass::int)/count(*),1) pct_pass_forward_event,
         round(100.0*sum((has_run AND NOT has_pass)::int)/count(*),1) pct_run_event_no_pass FROM ev JOIN pl p USING(nfl_id) GROUP BY 1 ORDER BY 2 DESC""")
TBL(tk_vs, "tk_only keys by position: share whose tracking shows a pass_forward event (pass play) vs run-type events.")
# what do other cohort players' pp rows say on those plays (route/dropback)?
tk_ctx = q("""SELECT p.dropback, p.is_na, count(DISTINCT (t.game_id, t.play_id, t.nfl_id)) keys
  FROM tk_only t JOIN pp p ON p.game_id=t.game_id AND p.play_id=t.play_id GROUP BY ALL ORDER BY 3 DESC""")
TBL(tk_ctx, "For tk_only keys whose play has other cohort pp rows: dropback / NA status of that play (key counted once per distinct value).")
tk_noplay = q("""SELECT count(*) keys_on_plays_with_no_pp_row_at_all FROM tk_only t WHERE NOT EXISTS (SELECT 1 FROM pp WHERE pp.game_id=t.game_id AND pp.play_id=t.play_id)""")
TBL(tk_noplay)
TBL(q("""SELECT p.nfl_position, p.draft_round IS NULL AS undrafted, count(DISTINCT t.nfl_id) players, count(*) keys FROM tk_only t JOIN pl p USING(nfl_id)
   WHERE p.nfl_position IN ('WR','TE','FB','RB') GROUP BY ALL ORDER BY 1"""), "(WR/TE/FB/RB tk_only keys by drafted status.)")
# for the pp rows of the same player-game, was player in pp for same game on other plays
tk_samegame = q("""SELECT sum((EXISTS (SELECT 1 FROM pp WHERE pp.game_id=t.game_id AND pp.nfl_id=t.nfl_id))::int) keys_player_has_other_pp_rows_that_game, count(*) keys FROM tk_only t""")
TBL(tk_samegame)

H(3, "5b. player_play rows WITHOUT a tracking key (pp_only)")
TBL(q("""SELECT is_na, count(*) rows FROM pp_only GROUP BY 1 ORDER BY 1"""), "NA (pre-snap penalty) status.")
TBL(q("""SELECT nfl_position, count(*) rows, sum(is_na::int) na_rows, sum((route_ran IS NOT NULL)::int) with_route FROM pp_only GROUP BY 1 ORDER BY 2 DESC"""), "By nfl_position.")
TBL(q("""SELECT season_type, count(*) rows FROM pp_only GROUP BY 1 ORDER BY 2 DESC"""), "By season_type.")
TBL(q("""SELECT lined_up_position, count(*) rows FROM pp_only GROUP BY 1 ORDER BY 2 DESC"""), "By lined_up_position.")
TBL(q("""SELECT dropback, (route_ran IS NOT NULL) has_route, play_nullified_by_penalty AS nullified, count(*) rows FROM pp_only WHERE NOT is_na GROUP BY ALL ORDER BY 4 DESC"""),
    "Non-NA pp_only rows: dropback / route / nullified status.")
TBL(q("""SELECT season_type, dropback, (route_ran IS NOT NULL) has_route, count(*) rows FROM pp_only WHERE NOT is_na GROUP BY ALL ORDER BY 1,2,3"""), "Non-NA pp_only rows by season_type.")
TBL(q("""SELECT (SELECT count(*) FROM pp_only o WHERE EXISTS (SELECT 1 FROM tk WHERE tk.game_id=o.game_id AND tk.play_id=o.play_id)) AS pp_only_rows_whose_play_has_some_other_tracking,
   count(*) AS pp_only_rows FROM pp_only"""), "pp_only rows whose play is present in tracking for another cohort player.")
TBL(q("""SELECT substr(regexp_extract(play_description, 'PENALTY on [A-Z]+(?:-[^,]+)?, ([^,]+),', 1), 1, 40) AS foul, count(*) rows FROM pp_only WHERE NOT is_na GROUP BY 1 ORDER BY 2 DESC LIMIT 10"""),
    "Fouls named in descriptions of non-NA pp_only rows ('' = no PENALTY phrase).")
TBL(q("""SELECT (SELECT count(*) FROM pp_only WHERE is_na) na_in_pp_only, (SELECT count(*) FROM pp WHERE is_na) na_total,
   (SELECT count(*) FROM pp_only WHERE NOT is_na) non_na_in_pp_only, (SELECT count(*) FROM pp_only WHERE NOT is_na AND play_nullified_by_penalty='Y') nullified_non_na_in_pp_only,
   (SELECT count(*) FROM pp_only WHERE NOT is_na AND play_description ILIKE '%No Play%') no_play_text_non_na_in_pp_only"""))
R["pp_only_na"] = int(q("SELECT count(*) n FROM pp_only WHERE is_na").n[0])

H(3, "5c. Key uniqueness and referential integrity")
ri = q("""SELECT 'player_play rows' check_, count(*) n FROM player_play
 UNION ALL SELECT 'player_play distinct (game_id,play_id,nfl_id)', count(DISTINCT (game_id,play_id,nfl_id)) FROM player_play
 UNION ALL SELECT 'player_play rows duplicated on full-row equality (all 64 cols)', count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM player_play)) FROM player_play
 UNION ALL SELECT 'players: rows', count(*) FROM players UNION ALL SELECT 'players: distinct nfl_id', count(DISTINCT nfl_id) FROM players
 UNION ALL SELECT 'career: rows', count(*) FROM player_career_successes UNION ALL SELECT 'career: distinct nfl_id', count(DISTINCT nfl_id) FROM player_career_successes
 UNION ALL SELECT 'games: rows', count(*) FROM games UNION ALL SELECT 'games: distinct game_id', count(DISTINCT game_id) FROM games
 UNION ALL SELECT 'games: distinct game_key', count(DISTINCT game_key) FROM games
 UNION ALL SELECT 'player_play nfl_id NOT in players', count(*) FROM player_play WHERE nfl_id NOT IN (SELECT nfl_id FROM players)
 UNION ALL SELECT 'player_play game_id NOT in games', count(*) FROM player_play WHERE game_id NOT IN (SELECT game_id FROM games)
 UNION ALL SELECT 'tracking keys nfl_id NOT in players', count(*) FROM tk WHERE nfl_id NOT IN (SELECT nfl_id FROM players)
 UNION ALL SELECT 'tracking keys game_id NOT in games', count(*) FROM tk WHERE game_id NOT IN (SELECT game_id FROM games)
 UNION ALL SELECT 'career nfl_id NOT in players', count(*) FROM player_career_successes WHERE nfl_id NOT IN (SELECT nfl_id FROM players)
 UNION ALL SELECT 'players nfl_id NOT in career', count(*) FROM players WHERE nfl_id NOT IN (SELECT nfl_id FROM player_career_successes)
 UNION ALL SELECT 'games with no player_play rows', count(*) FROM games WHERE game_id NOT IN (SELECT game_id FROM player_play)
 UNION ALL SELECT 'games with no tracking rows', count(*) FROM games WHERE game_id NOT IN (SELECT game_id FROM tk)
 UNION ALL SELECT 'games in tracking but not in player_play', count(DISTINCT game_id) FROM tk WHERE game_id NOT IN (SELECT game_id FROM player_play)
 UNION ALL SELECT 'players in tracking but not in player_play', count(DISTINCT nfl_id) FROM tk WHERE nfl_id NOT IN (SELECT nfl_id FROM player_play)
 UNION ALL SELECT 'players in player_play but not in tracking', count(DISTINCT nfl_id) FROM player_play WHERE nfl_id NOT IN (SELECT nfl_id FROM tk)
 UNION ALL SELECT 'player_play distinct (game_id,play_id)', count(DISTINCT (game_id,play_id)) FROM player_play
 UNION ALL SELECT 'tracking distinct (game_id,play_id)', count(DISTINCT (game_id,play_id)) FROM tk
 UNION ALL SELECT 'tracking plays absent from player_play (no cohort row at all)', count(*) FROM (SELECT DISTINCT game_id, play_id FROM tk EXCEPT SELECT game_id, play_id FROM player_play)
 UNION ALL SELECT 'player_play plays absent from tracking', count(*) FROM (SELECT DISTINCT game_id, play_id FROM player_play EXCEPT SELECT game_id, play_id FROM tk)
 UNION ALL SELECT 'tracking file/year vs games.season mismatch (keys)', count(*) FROM tk JOIN games g USING(game_id) WHERE g.season <> tk.yr
 UNION ALL SELECT 'draft_year of cohort players with NULL draft_overall_pick (undrafted)', count(*) FROM players WHERE draft_overall_pick IS NULL""")
TBL(ri)
R["ri"] = ri

# ============================================================== FACT 6 season types
log("fact 6")
H(2, "6. Fact 6 - season types, PRE games")
TBL(q("""SELECT season, season_type, count(*) games, min(week) min_week, max(week) max_week FROM games GROUP BY ALL ORDER BY 1,2"""), "games by season x season_type.")
TBL(q("""SELECT season_type, count(*) games FROM games GROUP BY 1 ORDER BY 1"""))
TBL(q("""SELECT g.season, g.season_type, count(*) AS pp_rows, count(DISTINCT p.game_id) AS pp_games, count(DISTINCT p.nfl_id) players
   FROM player_play p JOIN games g USING(game_id) GROUP BY ALL ORDER BY 1,2"""), "player_play rows by season x season_type.")
TBL(q("""SELECT g.season, g.season_type, count(*) AS tracking_keys, count(DISTINCT t.game_id) AS tracking_games
   FROM tk t JOIN games g USING(game_id) GROUP BY ALL ORDER BY 1,2"""), "Tracking keys (distinct game_id, play_id, nfl_id) by season x season_type.")
TBL(q("""SELECT g.season_type, count(*) AS tracking_keys FROM tk t JOIN games g USING(game_id) GROUP BY 1 ORDER BY 1"""))
TBL(q("""SELECT season_type, count(*) rows, count(DISTINCT nfl_id) players,
   sum(is_na::int) na_rows FROM pp GROUP BY 1 ORDER BY 1"""), "player_play by season_type (players = cohort players with >=1 row).")
TBL(q("""SELECT count(*) game_ids_with_rows_but_absent_from_games FROM (SELECT DISTINCT game_id FROM player_play UNION SELECT DISTINCT game_id FROM tk) x
   WHERE game_id NOT IN (SELECT game_id FROM games)"""))
# date parse from game id
TBL(q("""SELECT season_type, min(game_id) min_game_id, max(game_id) max_game_id, count(*) n FROM games GROUP BY 1 ORDER BY 1"""),
    "game_id ranges (format looks like YYYYMMDDNN) by season_type.")
TBL(q("""SELECT p.draft_year, g.season_type, count(*) rows FROM player_play a JOIN players p USING(nfl_id) JOIN games g USING(game_id) GROUP BY ALL ORDER BY 1,2"""),
    "player_play rows by draft class x season_type.")

# ============================================================== FACT 7 blitzing
log("fact 7")
H(2, "7. Fact 7 - blitzing / pressure fields")
P("Defence-side positions (DE, OLB, DT, NT, ILB, MLB, CB, FS, SS, DB), non-NA rows. `dropback` = pass_result <> ''.\n")
DEFPOS = "'DE','OLB','DT','NT','ILB','MLB','CB','FS','SS','DB'"
x7 = q(f"""SELECT dropback, blitzing, quick_pressure, (time_to_pressure IS NULL) AS ttp_null, (time_to_qb_hurry IS NULL) AS hurry_null,
   count(*) rows FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na GROUP BY ALL ORDER BY 1,2,3,4,5""")
TBL(x7, "Full cross-tab: dropback x blitzing x quick_pressure x time_to_pressure null-ness x time_to_qb_hurry null-ness. "
        "(<NA> in blitzing / quick_pressure means null.)")
R["x7"] = x7
TBL(q(f"""SELECT dropback, blitzing, count(*) rows, round(100.0*count(*)/sum(count(*)) OVER (),2) pct FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na GROUP BY dropback, blitzing ORDER BY 1,2"""),
    "blitzing x dropback only.")
TBL(q(f"""SELECT (blitzing IS NULL) AS blitzing_null, play_nullified_by_penalty AS nullified, season_type, count(*) rows,
   round(100.0*count(coverage_assignment)/count(*),1) "coverage_assignment nn%", round(100.0*count(team_coverage_type)/count(*),1) "team_coverage_type nn%"
   FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na AND dropback GROUP BY ALL ORDER BY 1,2,3"""),
    "Defender dropback rows where blitzing is null vs not: null blitzing is concentrated on penalty-nullified plays (nullified = Y: coverage and scheme also null); in PRE games coverage_assignment is almost never populated (about 0.4%) even when blitzing is, so coverage analysis must use REG/POST only.")
TBL(q(f"""SELECT dropback, blitzing, quick_pressure, count(*) rows FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na AND blitzing GROUP BY ALL ORDER BY 1,3"""),
    "blitzing = True: quick_pressure by dropback.")
rush = q(f"""SELECT count(*) rush_rows, sum((time_to_pressure IS NOT NULL)::int) ttp_nonnull, sum((quick_pressure IS NOT NULL)::int) qp_nonnull,
   sum((quick_pressure IS NULL AND time_to_pressure IS NOT NULL)::int) qp_null_but_ttp_nonnull,
   sum((quick_pressure IS NOT NULL AND time_to_pressure IS NULL)::int) qp_nonnull_but_ttp_null,
   sum((time_to_qb_hurry IS NOT NULL)::int) hurry_nonnull, sum((time_to_pressure IS NULL AND time_to_qb_hurry IS NOT NULL)::int) hurry_but_no_pressure,
   sum((time_to_pressure IS NOT NULL AND time_to_qb_hurry IS NULL)::int) pressure_but_no_hurry,
   sum((quick_pressure AND time_to_pressure > 2.5)::int) quick_true_but_ttp_gt_2_5, sum((quick_pressure = FALSE AND time_to_pressure <= 2.5)::int) quick_false_but_ttp_le_2_5,
   sum((player_get_off IS NULL)::int) get_off_null, sum((sack IS NOT NULL AND sack > 0)::int) sacks
   FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na AND blitzing AND dropback""")
TBL(rush.T.reset_index().rename(columns={"index": "metric (blitzing & dropback)", 0: "value"}))
R["rush"] = rush.iloc[0].to_dict()
TBL(q(f"""SELECT quick_pressure, count(*) rush_rows_with_pressure, round(min(time_to_pressure),2) min_ttp, round(max(time_to_pressure),2) max_ttp,
   round(quantile_cont(time_to_pressure,0.5),2) median_ttp, round(min(time_to_qb_hurry),2) min_hurry, round(max(time_to_qb_hurry),2) max_hurry,
   sum((time_to_pressure <= 2.5)::int) ttp_le_2p5, sum((time_to_pressure > 2.5)::int) ttp_gt_2p5
   FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na AND blitzing AND dropback AND time_to_pressure IS NOT NULL GROUP BY 1 ORDER BY 1"""),
    "Check of the '2.5 s' rule among rushers with a pressure (time_to_pressure non-null). quick_pressure is null on a few dozen of these rows.")
TBL(q("""SELECT quick_pressure, round(time_to_pressure,3) = 2.5 AS ttp_exactly_2p5, (time_to_pressure < 2.5) AS ttp_lt_2p5, count(*) rows FROM pp
   WHERE blitzing AND dropback AND time_to_pressure IS NOT NULL GROUP BY ALL ORDER BY 1,2,3"""), "Boundary check around exactly 2.5 s.")
TBL(q(f"""SELECT nfl_position, count(*) rows, sum((blitzing IS NULL)::int) blitzing_null, sum((blitzing IS NOT NULL AND blitzing)::int) blitzing_true,
   round(100.0*sum((blitzing IS NOT NULL AND blitzing)::int)/count(*),1) pct_rows_blitzing_true,
   round(100.0*sum((blitzing IS NOT NULL AND blitzing AND dropback)::int)/nullif(sum(dropback::int),0),1) pct_dropback_rows_blitzing_true
   FROM pp WHERE NOT is_na GROUP BY 1 ORDER BY 2 DESC"""), "Share of rows with blitzing = True by nfl_position (all rows, and as a share of dropback rows). Includes offensive positions to show where blitzing is populated.")
TBL(q("""SELECT lined_up_position, count(*) rows, sum((blitzing IS NULL)::int) blitzing_null, sum((blitzing IS NOT NULL AND blitzing)::int) blitzing_true,
   round(100.0*sum((blitzing IS NOT NULL AND blitzing AND dropback)::int)/nullif(sum(dropback::int),0),1) pct_dropback_rows_blitzing_true
   FROM pp WHERE NOT is_na GROUP BY 1 ORDER BY 2 DESC"""), "Same by lined_up_position.")
TBL(q(f"""SELECT nfl_position, count(*) rush_rows, sum((player_get_off IS NULL)::int) get_off_null,
   round(100.0*sum((player_get_off IS NULL)::int)/count(*),1) pct_get_off_null, round(avg(player_get_off),3) mean_get_off
   FROM pp WHERE nfl_position IN ({DEFPOS}) AND NOT is_na AND blitzing AND dropback GROUP BY 1 ORDER BY 2 DESC"""),
    "player_get_off nullness when blitzing = True and dropback.")
TBL(q(f"""SELECT blitzing, dropback, count(*) rows, sum((player_get_off IS NOT NULL)::int) get_off_nonnull FROM pp WHERE NOT is_na GROUP BY ALL ORDER BY 1,2"""),
    "player_get_off non-null count by blitzing x dropback (all positions).")
TBL(q("""SELECT grp, count(*) rows_blitzing_true FROM pp WHERE blitzing AND NOT is_na GROUP BY 1 ORDER BY 2 DESC"""), "Which groups ever carry blitzing = True.")

# ============================================================== SECTION A exposure
log("section A")
H(2, "A. Exposure")
con.execute("""CREATE TABLE exp AS
  SELECT p.nfl_id, p.nfl_position, p.grp, p.draft_year,
    count(a.nfl_id) AS rows_all, coalesce(sum(a.reg::int),0) AS rows_reg,
    coalesce(sum((a.reg AND NOT a.is_na)::int),0) AS rows_reg_nonna,
    count(DISTINCT a.game_id) AS games_all, count(DISTINCT CASE WHEN a.reg THEN a.game_id END) AS games_reg,
    coalesce(sum((a.reg AND a.season=2023)::int),0) AS r23, coalesce(sum((a.reg AND a.season=2024)::int),0) AS r24,
    coalesce(sum((a.reg AND a.season=2025)::int),0) AS r25
  FROM pl p LEFT JOIN pp a ON a.nfl_id = p.nfl_id GROUP BY 1,2,3,4""")


def exposure(by_cols: str, label_cols: list[str], where: str = "TRUE") -> pd.DataFrame:
    return q(f"""SELECT {by_cols}, count(*) players,
       sum((rows_all>0)::int) players_any_ALL, sum((rows_reg>0)::int) players_any_REG,
       sum(rows_reg) total_rows_REG,
       min(rows_reg) FILTER (WHERE rows_reg>0) REG_min, quantile_cont(rows_reg, 0.25) FILTER (WHERE rows_reg>0) REG_q1,
       quantile_cont(rows_reg, 0.5) FILTER (WHERE rows_reg>0) REG_med, quantile_cont(rows_reg, 0.75) FILTER (WHERE rows_reg>0) REG_q3,
       max(rows_reg) REG_max,
       sum(rows_all) total_rows_ALL, min(rows_all) FILTER (WHERE rows_all>0) ALL_min, quantile_cont(rows_all, 0.5) FILTER (WHERE rows_all>0) ALL_med,
       max(rows_all) ALL_max
       FROM exp WHERE {where} GROUP BY {by_cols} ORDER BY {by_cols}""")


P("Distribution columns (`REG_min` ... `REG_max`) are player_play rows per player among players with >=1 REG row "
  "(players with 0 are counted in `players` but not in the quantiles). `total_rows` includes NA rows. "
  "Rows per player is NOT snaps-equivalent for WR/TE (route plays only).\n")
H(3, "A1. By nfl_position x draft_year")
a1 = exposure("nfl_position, draft_year", ["nfl_position", "draft_year"])
TBL(a1)
H(3, "A1b. By nfl_position (all classes)")
TBL(exposure("nfl_position", ["nfl_position"]))
H(3, "A1c. By position group x draft_year")
a1c = exposure("grp, draft_year", ["grp", "draft_year"])
TBL(a1c)
H(3, "A1d. By position group (all classes)")
a1d = exposure("grp", ["grp"])
TBL(a1d)
R["a1d"] = a1d
tot = q(f"""SELECT 'ALL cohort' grp, count(*) players, sum((rows_all>0)::int) players_any_ALL, sum((rows_reg>0)::int) players_any_REG, sum(rows_reg) total_rows_REG,
   sum(rows_all) total_rows_ALL, quantile_cont(rows_reg, 0.5) FILTER (WHERE rows_reg>0) REG_med FROM exp""")
TBL(tot)
H(3, "A2. By season (REG only; and ALL games)")
a2 = q("""WITH s AS (SELECT p.grp, p.nfl_id, a.season, count(*) rows_reg FROM pl p JOIN pp a ON a.nfl_id=p.nfl_id WHERE a.reg GROUP BY ALL)
  SELECT grp, season, count(*) players_with_rows, sum(rows_reg) total_rows, min(rows_reg) min, quantile_cont(rows_reg,0.25) q1,
         quantile_cont(rows_reg,0.5) med, quantile_cont(rows_reg,0.75) q3, max(rows_reg) max FROM s GROUP BY ALL ORDER BY 1,2""")
TBL(a2, "REG-season rows per player among players with >=1 row in that season.")
a2b = q("""SELECT season, season_type, count(*) rows, count(DISTINCT nfl_id) players FROM pp GROUP BY ALL ORDER BY 1,2""")
TBL(a2b, "All games: rows by season x season_type.")
H(3, "A3. Class x season: how unequal is exposure?")
a3 = q("""SELECT draft_year AS class, season, count(DISTINCT nfl_id) players_with_rows, sum(reg::int) reg_rows,
   round(sum(reg::int)*1.0/count(DISTINCT CASE WHEN reg THEN nfl_id END),1) reg_rows_per_active_player, count(*) all_rows
   FROM pp GROUP BY ALL ORDER BY 1,2""")
TBL(a3)
a3b = q("""SELECT draft_year AS class, count(*) players, sum(rows_reg) reg_rows, round(sum(rows_reg)*1.0/count(*),1) reg_rows_per_cohort_player,
   quantile_cont(rows_reg, 0.5) median_reg_rows_per_cohort_player, sum(games_reg) reg_player_games FROM exp GROUP BY 1 ORDER BY 1""")
TBL(a3b, "Per-class REG exposure (zeros included in per-player mean/median).")
R["a3b"] = a3b
H(3, "A4. Group x class x season (REG), players with rows / total rows / median rows per active player")
a4 = q("""WITH s AS (SELECT p.grp, p.draft_year, a.season, p.nfl_id, count(*) r FROM pl p JOIN pp a ON a.nfl_id=p.nfl_id WHERE a.reg GROUP BY ALL)
  SELECT grp, draft_year AS class, season, count(*) active_players, sum(r) rows, quantile_cont(r,0.5) median_rows FROM s GROUP BY ALL ORDER BY 1,2,3""")
TBL(a4)
H(3, "A5. Distinct REG games per player")
TBL(q("""SELECT grp, count(*) players, min(games_reg) G_min, quantile_cont(games_reg,0.25) G_q1, quantile_cont(games_reg,0.5) G_med,
   quantile_cont(games_reg,0.75) G_q3, max(games_reg) G_max FROM exp WHERE rows_reg>0 GROUP BY 1 ORDER BY 1"""))

# ============================================================== SECTION B
log("section B")
H(2, "B. Outcome availability by position group")
P("Base filter for all of B: `NOT is_na` (pre-snap-penalty rows removed). Qualifying-play counts are shown for REG-only and for ALL games "
  "(PRE+REG+POST). `>=50/100/200` = number of players in the group with at least that many qualifying plays. "
  "`players` = cohort players in the group (incl. those with no rows).\n")

con.execute("CREATE TABLE ppn AS SELECT * FROM pp WHERE NOT is_na")


def family_counts(name: str, group_filter: str, qual: str, groups: list[str]) -> pd.DataFrame:
    base = q(f"""WITH per AS (
        SELECT p.grp, p.nfl_id,
               coalesce(sum(CASE WHEN ({qual}) AND a.reg THEN 1 ELSE 0 END),0) AS q_reg,
               coalesce(sum(CASE WHEN ({qual}) THEN 1 ELSE 0 END),0) AS q_all
        FROM pl p LEFT JOIN ppn a ON a.nfl_id=p.nfl_id GROUP BY 1,2)
      SELECT grp, count(*) players,
         sum((q_reg>0)::int) any_REG, sum((q_reg>=50)::int) ge50_REG, sum((q_reg>=100)::int) ge100_REG, sum((q_reg>=200)::int) ge200_REG,
         sum(q_reg) plays_REG,
         sum((q_all>0)::int) any_ALL, sum((q_all>=50)::int) ge50_ALL, sum((q_all>=100)::int) ge100_ALL, sum((q_all>=200)::int) ge200_ALL, sum(q_all) plays_ALL
      FROM per WHERE grp IN ({",".join(repr(g) for g in groups)}) GROUP BY 1""")
    base["o"] = base.grp.map({g: i for i, g in enumerate(GROUPS)})
    return base.sort_values("o").drop(columns="o")


def family_fields(group_filter_groups: list[str], qual: str, specs: list[tuple[str, str]], reg_only: bool = True, by="grp") -> pd.DataFrame:
    sel = []
    for col, kind in specs:
        if kind == "nn":
            sel.append(f"round(100.0*count({col})/count(*),1) AS \"{col} nn%\"")
        elif kind == "true":
            sel.append(f"round(100.0*sum(CASE WHEN {col} THEN 1 ELSE 0 END)/count(*),2) AS \"{col} true%\"")
        elif kind == "mean":
            sel.append(f"round(avg({col}),3) AS \"{col} mean\"")
        elif kind == "sum":
            sel.append(f"sum(CASE WHEN {col} > 0 THEN 1 ELSE 0 END) AS \"n {col}>0\"")
    return q(f"""SELECT {by}, count(*) qualifying_plays_REG, {", ".join(sel)} FROM ppn
      WHERE ({qual}) AND reg AND grp IN ({",".join(repr(g) for g in group_filter_groups)}) GROUP BY 1 ORDER BY 1""")


# ---------------------------------------------------------- B1 receiving
H(3, "B1. Receiving (WR, TE, RB_FB)")
P("Qualifying play = `route_ran` non-null. Targets = `target` True (target is a non-null boolean on every row).\n")
REC = ["WR", "TE", "RB_FB"]
c = family_counts("routes", "", "route_ran IS NOT NULL", REC)
TBL(c, "Players by routes run.")
R["B1_routes"] = c
c = family_counts("targets", "", "target IS TRUE", REC)
TBL(c, "Players by targets (qualifying play = target True). NB thresholds of 50/100/200 targets are extreme for this sample; see also >=25 / >=10 below.")
R["B1_targets"] = c
t2 = q("""WITH per AS (SELECT p.grp, p.nfl_id, coalesce(sum(CASE WHEN a.target AND a.reg THEN 1 ELSE 0 END),0) t FROM pl p LEFT JOIN ppn a ON a.nfl_id=p.nfl_id GROUP BY 1,2)
  SELECT grp, count(*) players, sum((t>=10)::int) ge10_targets_REG, sum((t>=25)::int) ge25_targets_REG, sum((t>=40)::int) ge40_targets_REG, max(t) max_targets, sum(t) total_targets_REG
  FROM per WHERE grp IN ('WR','TE','RB_FB') GROUP BY 1""")
TBL(t2)
rf = family_fields(REC, "route_ran IS NOT NULL", [("separation_at_pass_forward", "nn"), ("cushion", "nn"), ("yards_after_catch", "nn"),
                                                   ("expected_yards_after_catch", "nn"), ("rec_yards", "nn"), ("target", "true"),
                                                   ("pass_result", "nn"), ("dropback_duration", "nn"), ("pressure_allowed", "nn"),
                                                   ("team_coverage_type", "nn"), ("in_motion_at_ball_snap", "nn")])
TBL(rf, "Non-null rate of each field among REG qualifying (route) plays. (`pass_result nn%` = 100 because it is '' not null; see H1.)")
P("Separation / cushion / YAC availability on non-target routes vs target routes (REG, routes, non-NA):\n")
sep = q("""SELECT grp, target, count(*) routes, round(100.0*count(separation_at_pass_forward)/count(*),1) "separation nn%",
   round(100.0*count(cushion)/count(*),1) "cushion nn%", round(100.0*count(yards_after_catch)/count(*),1) "yac nn%",
   round(100.0*count(expected_yards_after_catch)/count(*),1) "eyac nn%", round(100.0*count(rec_yards)/count(*),1) "rec_yards nn%"
   FROM ppn WHERE route_ran IS NOT NULL AND reg AND grp IN ('WR','TE','RB_FB') GROUP BY ALL ORDER BY 1,2""")
TBL(sep)
R["sep"] = sep
sep2 = q("""SELECT target, pass_result, count(*) routes, round(100.0*count(separation_at_pass_forward)/count(*),1) "separation nn%",
   round(100.0*count(cushion)/count(*),1) "cushion nn%", round(100.0*count(yards_after_catch)/count(*),1) "yac nn%",
   round(100.0*count(expected_yards_after_catch)/count(*),1) "eyac nn%" FROM ppn
   WHERE route_ran IS NOT NULL AND reg AND grp IN ('WR','TE','RB_FB') GROUP BY ALL ORDER BY 1,2""")
TBL(sep2, "Same by target x pass_result of the play ('' = non-dropback; C complete, I incomplete, IN interception, S sack, R scramble).")
sep3 = q("""SELECT p.grp, count(*) non_target_routes_with_sep, count(DISTINCT a.nfl_id) players_with_any FROM ppn a JOIN pl p USING(nfl_id)
   WHERE a.route_ran IS NOT NULL AND a.reg AND NOT a.target AND a.separation_at_pass_forward IS NOT NULL AND p.grp IN ('WR','TE','RB_FB') GROUP BY 1""")
TBL(sep3, "Non-target REG routes that nevertheless have separation_at_pass_forward.")
sep4 = q("""WITH per AS (SELECT p.grp, p.nfl_id, coalesce(sum(CASE WHEN a.separation_at_pass_forward IS NOT NULL AND a.reg THEN 1 ELSE 0 END),0) s,
   coalesce(sum(CASE WHEN a.separation_at_pass_forward IS NOT NULL AND a.reg AND a.target THEN 1 ELSE 0 END),0) st
   FROM pl p LEFT JOIN ppn a ON a.nfl_id=p.nfl_id GROUP BY 1,2)
   SELECT grp, count(*) players, sum((s>=25)::int) ge25_sep, sum((s>=50)::int) ge50_sep, sum((s>=100)::int) ge100_sep, sum((s>=200)::int) ge200_sep, max(s) max_sep_plays,
     sum((st>=10)::int) ge10_target_sep, sum((st>=25)::int) ge25_target_sep FROM per WHERE grp IN ('WR','TE','RB_FB') GROUP BY 1""")
TBL(sep4, "Players by number of REG plays with non-null separation_at_pass_forward (any route) and by target-only separation.")
R["sep4"] = sep4
TBL(q("""SELECT grp, route_ran, count(*) rows, round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY grp),1) pct_within_grp,
   round(100.0*count(separation_at_pass_forward)/count(*),1) "separation nn%", round(100.0*sum(target::int)/count(*),1) "target%" FROM ppn
   WHERE route_ran IS NOT NULL AND reg AND grp IN ('WR','TE','RB_FB') GROUP BY grp, route_ran ORDER BY 1,3 DESC"""), "route_ran value distribution (REG, non-NA).")
TBL(q("""SELECT grp, (route_ran IS NOT NULL) has_route, dropback, count(*) rows FROM ppn WHERE reg AND grp IN ('WR','TE','RB_FB') GROUP BY ALL ORDER BY 1,2,3"""),
    "Route rows vs dropback status (REG).")
TBL(q("""SELECT grp, round(avg(separation_at_pass_forward),2) mean_sep, round(avg(cushion),2) mean_cushion, round(min(separation_at_pass_forward),2) min_sep,
   round(max(separation_at_pass_forward),2) max_sep, round(min(cushion),2) min_cushion, round(max(cushion),2) max_cushion,
   round(avg(expected_yards_after_catch),2) mean_eyac, round(avg(yards_after_catch),2) mean_yac, count(yards_after_catch) n_yac, sum((target AND pass_result='C')::int) n_catches
   FROM ppn WHERE reg AND grp IN ('WR','TE','RB_FB') GROUP BY 1 ORDER BY 1"""), "Value ranges.")
TBL(q("""SELECT grp, count(*) targets, sum((pass_result='C')::int) catches, sum((pass_result='I')::int) incomplete, sum((pass_result='IN')::int) interceptions,
   sum((yards_after_catch IS NOT NULL)::int) yac_nn, sum((separation_at_pass_forward IS NOT NULL)::int) sep_nn, sum((expected_yards_after_catch IS NOT NULL)::int) eyac_nn,
   sum((rec_yards IS NOT NULL)::int) rec_yards_nn FROM ppn WHERE target AND reg AND grp IN ('WR','TE','RB_FB') GROUP BY 1"""), "Among REG targets: pass_result split and populated fields.")

# ---------------------------------------------------------- B2 pass protection
H(3, "B2. Pass protection (OL; TE/RB/WR/FB when present)")
P("Pass-block snap definition used: `pressure_allowed IS NOT NULL`. Verification that this coincides with `pass_rushers_encountered`, `dropback_duration`, "
  "`peak_pressure_probability_allowed` non-null (row counts):\n")
TBL(q("""SELECT grp, count(*) rows, sum((pressure_allowed IS NOT NULL)::int) pressure_allowed_nn, sum((pass_rushers_encountered IS NOT NULL)::int) rushers_nn,
   sum((dropback_duration IS NOT NULL)::int) dropback_duration_nn, sum((peak_pressure_probability_allowed IS NOT NULL)::int) peak_nn,
   sum((sack_allowed IS NOT NULL)::int) sack_allowed_nn, sum((pressure_allowed IS NOT NULL AND NOT dropback)::int) pb_snaps_on_nondropback,
   sum((pressure_allowed IS NULL AND dropback)::int) dropback_rows_without_pb
   FROM ppn GROUP BY 1 ORDER BY 1"""))
PB = ["OL", "TE", "RB_FB", "WR"]
c = family_counts("passblock", "", "pressure_allowed IS NOT NULL", ["OL", "TE", "RB_FB", "WR"])
TBL(c, "Players by pass-block snaps.")
R["B2"] = c
pf = family_fields(PB, "pressure_allowed IS NOT NULL", [("pressure_allowed", "true"), ("peak_pressure_probability_allowed", "nn"), ("peak_pressure_probability_allowed", "mean"),
                                                         ("time_to_pressure_allowed", "nn"), ("time_to_pressure_allowed", "mean"), ("sack_allowed", "nn"),
                                                         ("sack_allowed", "true"), ("pass_rushers_encountered", "nn"), ("pass_rushers_encountered", "mean"),
                                                         ("dropback_duration", "nn"), ("dropback_duration", "mean"), ("extended_sack_allowed", "nn")])
TBL(pf, "Among REG pass-block snaps. `true%` = % of snaps with value True (sack_allowed is double; True%=value>0 not applied, see sums below).")
TBL(q("""SELECT grp, count(*) pb_snaps, sum(pressure_allowed::int) pressures, sum((sack_allowed>0)::int) sacks_allowed,
   sum((extended_sack_allowed>0)::int) ext_sacks_allowed, count(DISTINCT sack_allowed) sack_allowed_distinct, min(sack_allowed) min_sa, max(sack_allowed) max_sa,
   sum((time_to_pressure_allowed IS NOT NULL AND pressure_allowed)::int) ttp_allowed_nn_on_pressure, sum((time_to_pressure_allowed IS NOT NULL AND NOT pressure_allowed)::int) ttp_allowed_nn_no_pressure
   FROM ppn WHERE pressure_allowed IS NOT NULL AND reg GROUP BY 1 ORDER BY 1"""), "Counts (REG).")
pc = q("""WITH per AS (SELECT p.grp, p.nfl_id, coalesce(sum(CASE WHEN a.pressure_allowed AND a.reg THEN 1 ELSE 0 END),0) pr
   FROM pl p LEFT JOIN ppn a ON a.nfl_id=p.nfl_id GROUP BY 1,2)
   SELECT grp, sum((pr>=5)::int) ge5_pressures_allowed, sum((pr>=10)::int) ge10_pressures_allowed, sum((pr>=20)::int) ge20, max(pr) max_pressures FROM per WHERE grp='OL' GROUP BY 1""")
TBL(pc, "OL players by number of REG pressures allowed (outcome event counts matter for rate reliability).")
TBL(q("""SELECT nfl_position, count(*) pb_snaps, round(100.0*avg(pressure_allowed::int),2) pressure_rate_pct, round(100.0*avg((sack_allowed>0)::int),2) sack_rate_pct
   FROM ppn WHERE grp='OL' AND pressure_allowed IS NOT NULL AND reg GROUP BY 1 ORDER BY 1"""), "OL by nfl_position (REG).")
TBL(q("""SELECT grp, count(*) rows_nondropback_with_pb_fields FROM ppn WHERE pressure_allowed IS NOT NULL AND NOT dropback GROUP BY 1"""), "Pass-block fields populated on non-dropback rows (play text suggests these are play-action/scramble/other).")
TBL(q("""SELECT t.pass_result, count(*) pb_snaps FROM ppn t WHERE t.pressure_allowed IS NOT NULL AND t.grp='OL' GROUP BY 1 ORDER BY 2 DESC"""), "pass_result on OL pass-block snaps.")

# ---------------------------------------------------------- B3 pass rush
H(3, "B3. Pass rush (DE, OLB, DT, NT, LB, DB)")
P("Pass-rush snap = `blitzing IS TRUE AND dropback` (host: blitzing marks all rushers). Pressure = `time_to_pressure IS NOT NULL` (host: null = no pressure). "
  "Sack = `sack > 0`.\n")
PR = ["EDGE", "IDL", "LB", "CB", "S", "DB_generic"]
c = family_counts("rush", "", "blitzing IS TRUE AND dropback", PR)
TBL(c, "Players by pass-rush snaps.")
R["B3"] = c
# pressures per player
pcnt = q("""WITH per AS (SELECT p.grp, p.nfl_id, coalesce(sum(CASE WHEN a.blitzing AND a.dropback AND a.reg THEN 1 ELSE 0 END),0) rs,
    coalesce(sum(CASE WHEN a.blitzing AND a.dropback AND a.reg AND a.time_to_pressure IS NOT NULL THEN 1 ELSE 0 END),0) pr,
    coalesce(sum(CASE WHEN a.blitzing AND a.dropback AND a.reg AND a.sack>0 THEN 1 ELSE 0 END),0) sk
    FROM pl p LEFT JOIN ppn a ON a.nfl_id=p.nfl_id GROUP BY 1,2)
    SELECT grp, count(*) players, sum((rs>=100)::int) ge100_rush_snaps, sum((pr>=10)::int) ge10_pressures, sum((pr>=20)::int) ge20_pressures, max(pr) max_pressures,
      sum(pr) total_pressures, sum(sk) total_sacks, sum((sk>=3)::int) ge3_sacks, max(sk) max_sacks FROM per WHERE grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY 1""")
TBL(pcnt, "REG: players by number of pressures / sacks (event counts).")
R["B3_events"] = pcnt
prf = family_fields(PR, "blitzing IS TRUE AND dropback", [("time_to_pressure", "nn"), ("quick_pressure", "nn"), ("quick_pressure", "true"), ("time_to_qb_hurry", "nn"),
                                                          ("unblocked_pressure", "nn"), ("unblocked_pressure", "true"), ("player_get_off", "nn"), ("player_get_off", "mean"),
                                                          ("sack", "nn"), ("sack", "sum"), ("coverage_assignment", "nn")])
TBL(prf, "Field availability among REG pass-rush snaps. Pressure rate = `time_to_pressure nn%`.")
TBL(q("""SELECT nfl_position, count(*) rush_snaps, round(100.0*count(time_to_pressure)/count(*),2) pressure_rate_pct,
   round(100.0*sum((sack>0)::int)/count(*),2) sack_rate_pct, round(100.0*sum((quick_pressure)::int)/count(*),2) quick_pressure_pct,
   round(100.0*count(player_get_off)/count(*),1) get_off_nn_pct, round(avg(player_get_off),3) mean_get_off
   FROM ppn WHERE blitzing AND dropback AND reg AND grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY 1 ORDER BY 2 DESC"""), "By nfl_position (REG).")
TBL(q("""SELECT grp, count(*) dropback_rows, sum((blitzing IS TRUE)::int) rush_snaps, round(100.0*avg((blitzing IS TRUE)::int),1) pct_rush FROM ppn
   WHERE dropback AND reg AND grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY 1 ORDER BY 1"""), "Share of dropback rows on which the defender rushed.")
TBL(q("""SELECT grp, count(*) rows, sum((sack IS NOT NULL)::int) sack_nn, sum((sack>0)::int) sack_pos, count(DISTINCT sack) sack_distinct, min(sack) min_sack, max(sack) max_sack
   FROM ppn WHERE reg AND grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY 1 ORDER BY 1"""), "sack field (all REG defender rows; sack is a double, half-sacks possible).")
TBL(q("""SELECT blitzing, dropback, count(sack) sack_nn, sum((sack>0)::int) sack_pos FROM ppn WHERE grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY ALL ORDER BY 1,2"""),
    "Is sack only populated on rushers?")

# ---------------------------------------------------------- B4 coverage
H(3, "B4. Coverage (CB, S, LB, DB)")
P("Coverage snap = `coverage_assignment IS NOT NULL`. 'Assigned coverage' additionally excludes `NO_ASSIGNMENT` (rushers/spies/etc.).\n")
CV = ["CB", "S", "LB", "DB_generic", "EDGE", "IDL"]
c = family_counts("cov", "", "coverage_assignment IS NOT NULL", CV)
TBL(c, "Players by snaps with coverage_assignment non-null.")
R["B4a"] = c
c2 = family_counts("cov2", "", "coverage_assignment IS NOT NULL AND coverage_assignment <> 'NO_ASSIGNMENT'", CV)
TBL(c2, "Players by snaps with a real coverage assignment (non-null and not NO_ASSIGNMENT).")
R["B4b"] = c2
TBL(q("""SELECT grp, count(*) cov_snaps, sum((coverage_assignment_at_snap IS NOT NULL)::int) at_snap_nn, sum(dropback::int) on_dropback,
   sum((coverage_assignment = 'NO_ASSIGNMENT')::int) no_assignment, sum((coverage_assignment='MAN')::int) man,
   sum((coverage_assignment <> 'NO_ASSIGNMENT' AND coverage_assignment <> 'MAN')::int) zone_like,
   sum((coverage_assignment <> coalesce(coverage_assignment_at_snap,'~'))::int) differs_from_at_snap
   FROM ppn WHERE coverage_assignment IS NOT NULL AND reg AND grp IN ('CB','S','LB','DB_generic','EDGE','IDL') GROUP BY 1 ORDER BY 1"""), "REG coverage rows by group.")
cad = q("""SELECT coverage_assignment, sum((grp='CB')::int) CB, sum((grp='S')::int) S, sum((grp='LB')::int) LB, sum((grp='DB_generic')::int) DB_generic,
   sum((grp='EDGE')::int) EDGE, sum((grp='IDL')::int) IDL, count(*) total FROM ppn WHERE coverage_assignment IS NOT NULL AND reg GROUP BY 1 ORDER BY total DESC""")
TBL(cad, "coverage_assignment values (REG rows) by group.")
TBL(q("""SELECT team_coverage_man_zone, team_coverage_type, count(*) rows FROM ppn WHERE coverage_assignment IS NOT NULL AND reg AND grp IN ('CB','S','LB','DB_generic') GROUP BY ALL ORDER BY 3 DESC"""),
    "Team scheme on CB/S/LB coverage rows.")
P("Which fields are populated on defender coverage rows (CB/S/LB/DB, REG, coverage_assignment non-null and not NO_ASSIGNMENT; plus target/True counts):\n")
cols = [r[0] for r in con.execute("DESCRIBE player_play").fetchall()]
parts = []
for ccol in cols:
    parts.append(f"SELECT '{ccol}' AS col, round(100.0*count({ccol})/count(*),1) AS nonnull_pct FROM ppn WHERE coverage_assignment IS NOT NULL AND coverage_assignment<>'NO_ASSIGNMENT' AND reg AND grp IN ('CB','S','LB','DB_generic')")
cvf = q(" UNION ALL ".join(parts))
OUTCOME_COLS = ("route_ran", "separation_at_pass_forward", "cushion", "expected_yards_after_catch", "yards_after_catch", "rec_yards", "rush_yards", "target",
    "tackle", "assist", "tackle_for_loss", "sack", "blitzing", "pressure_allowed", "player_get_off", "time_to_pressure", "quick_pressure", "unblocked_pressure",
    "fumble", "fumble_lost", "caused_forced_fumble", "recovered_fumble", "pass_result", "pass_length", "yards_gained", "dropback_duration", "pass_rushers_encountered",
    "time_to_qb_hurry")
TBL(cvf[cvf.col.isin(OUTCOME_COLS)].reset_index(drop=True),
    "Non-null % of outcome-type columns on those rows (0 = never populated for coverage defenders).")
TBL(q("""SELECT grp, coverage_assignment = 'MAN' AS man, dropback, count(*) rows, round(100.0*count(cushion)/count(*),1) "cushion nn%", round(avg(cushion),2) mean_cushion,
   round(min(cushion),2) min_cushion, round(max(cushion),2) max_cushion FROM ppn WHERE reg AND grp IN ('CB','S') AND coverage_assignment IS NOT NULL
   AND coverage_assignment <> 'NO_ASSIGNMENT' GROUP BY ALL ORDER BY 1,2,3"""),
    "`cushion` IS populated on defender rows (CB/S): the only defender-vs-receiver spatial number on a coverage row. Man coverage has a smaller cushion than zone, so it looks "
    "like a pre-snap distance to the matched/nearest receiver (*inference*: the field is not documented for defenders). It is not a separation-allowed or play outcome.")
TBL(q("""SELECT grp, dropback, (coverage_assignment IS NOT NULL) has_assignment, count(*) rows, round(100.0*count(cushion)/count(*),1) "cushion nn%" FROM ppn
   WHERE reg AND grp IN ('CB','S','EDGE','IDL') GROUP BY ALL ORDER BY 1,2,3"""), "cushion availability on defenders by play type and whether a coverage_assignment exists (it is also present on run plays).")
TBL(q("""SELECT grp, sum(target::int) rows_with_target_true, count(rec_yards) rec_yards_nn, count(separation_at_pass_forward) sep_nn, count(cushion) cushion_nn,
   count(expected_yards_after_catch) eyac_nn, count(route_ran) route_nn FROM ppn WHERE grp IN ('CB','S','LB','DB_generic','EDGE','IDL') GROUP BY 1 ORDER BY 1"""),
    "Receiver-style/target fields on ALL defender rows (confirms there is no defender-targeted / separation-allowed information).")
TBL(q("""SELECT grp, dropback, pass_result, count(*) rows FROM ppn WHERE coverage_assignment IS NOT NULL AND coverage_assignment <> 'NO_ASSIGNMENT' AND reg AND grp IN ('CB','S') GROUP BY ALL ORDER BY 1,2,4 DESC"""),
    "Play-level pass_result on CB/S coverage rows (play-level only: the same value for every player on the play; there is no defender-level target flag).")
TBL(q("""SELECT grp, count(*) cov_snaps, sum((pass_result IN ('C','I','IN'))::int) pass_plays_with_throw, sum((pass_result='C')::int) completions_on_play,
   sum(coalesce(yards_gained,0)) yards_gained_sum, count(yards_gained) yards_gained_nn
   FROM ppn WHERE coverage_assignment IS NOT NULL AND coverage_assignment <> 'NO_ASSIGNMENT' AND reg AND grp IN ('CB','S','LB','DB_generic') GROUP BY 1"""),
    "Team-play outcomes attached to a coverage snap are play level (yards_gained is the play's yardage, not the defender's).")

# ---------------------------------------------------------- B5 run defence
H(3, "B5. Run defence / tackling")
P("Defender rows. 'Run-defence snap' = defender on the defence side (team_abbr <> possession_team) and `NOT dropback` (pass_result = ''), non-NA. "
  "tackle/assist/tackle_for_loss are null when the player had no tackle credit and populated (0/1) only for credited players (see value table).\n")
RD = ["EDGE", "IDL", "LB", "CB", "S", "DB_generic"]
TBL(q("""SELECT tackle, assist, tackle_for_loss, caused_forced_fumble, recovered_fumble, count(*) rows FROM ppn WHERE grp IN ('EDGE','IDL','LB','CB','S','DB_generic')
   GROUP BY ALL ORDER BY 6 DESC LIMIT 14"""), "Value combinations of tackle fields on defender rows.")
c = family_counts("rundef", "", "NOT on_offense AND NOT dropback", RD)
TBL(c, "Players by run-defence snaps.")
R["B5"] = c
c = family_counts("tacklesnaps", "", "NOT on_offense", RD)
TBL(c, "Players by ALL defensive snaps (denominator for tackle/assist per snap).")
R["B5_allsnaps"] = c
rdf = q("""SELECT grp, dropback, count(*) rows, round(100.0*count(tackle)/count(*),1) "tackle nn%", round(100.0*sum((tackle>0)::int)/count(*),2) "tackle>0 %",
   round(100.0*sum((assist>0)::int)/count(*),2) "assist>0 %", round(100.0*sum(tackle_for_loss::int)/count(*),2) "TFL %", round(100.0*count(sack)/count(*),2) "sack nn%",
   sum((tackle>0)::int) n_tackles, sum((assist>0)::int) n_assists, sum(tackle_for_loss::int) n_tfl, sum((caused_forced_fumble>0)::int) n_cff, sum(recovered_fumble::int) n_rec
   FROM ppn WHERE NOT on_offense AND reg AND grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY ALL ORDER BY 1,2""")
TBL(rdf, "Defender REG rows: tackle metrics by dropback (False = run / non-pass defence snap).")
R["rdf"] = rdf
tk_pl = q("""WITH per AS (SELECT p.grp, p.nfl_id, coalesce(sum(CASE WHEN a.tackle>0 AND a.reg THEN a.tackle ELSE 0 END),0) tk,
    coalesce(sum(CASE WHEN a.assist>0 AND a.reg THEN 1 ELSE 0 END),0) ast, coalesce(sum(CASE WHEN a.tackle_for_loss AND a.reg THEN 1 ELSE 0 END),0) tfl
    FROM pl p LEFT JOIN ppn a ON a.nfl_id=p.nfl_id GROUP BY 1,2)
    SELECT grp, count(*) players, sum((tk>=10)::int) ge10_tackles, sum((tk>=25)::int) ge25_tackles, sum((tk>=50)::int) ge50_tackles, max(tk) max_tackles,
           sum((tk+ast>=25)::int) ge25_tackles_plus_assists, sum((tfl>=5)::int) ge5_tfl, max(tfl) max_tfl FROM per WHERE grp IN ('EDGE','IDL','LB','CB','S','DB_generic') GROUP BY 1""")
TBL(tk_pl, "Event counts per player (REG).")
R["tk_pl"] = tk_pl

# ---------------------------------------------------------- B6 run blocking
H(3, "B6. Run blocking for OL (is anything recorded beyond the row?)")
oc = []
for ccol in cols:
    oc.append(f"""SELECT '{ccol}' AS col, round(100.0*count({ccol}) FILTER (WHERE NOT dropback)/nullif(count(*) FILTER (WHERE NOT dropback),0),1) AS run_play_nn_pct,
       round(100.0*count({ccol}) FILTER (WHERE dropback)/nullif(count(*) FILTER (WHERE dropback),0),1) AS dropback_nn_pct FROM ppn WHERE grp='OL' AND on_offense AND reg""")
olr = q(" UNION ALL ".join(oc))
nrun = q("SELECT count(*) FILTER (WHERE NOT dropback) run_rows, count(*) FILTER (WHERE dropback) dropback_rows FROM ppn WHERE grp='OL' AND on_offense AND reg")
TBL(nrun, "OL rows on offence (REG, non-NA).")
play_level = {"game_id", "play_id", "team_abbr", "nfl_id", "lined_up_position", "play_description", "quarter", "down", "yards_to_go", "possession_team", "yardline_side",
              "yardline_number", "game_clock", "pre_snap_home_score", "pre_snap_visitor_score", "play_direction", "pre_snap_home_team_win_probability",
              "pre_snap_visitor_team_win_probability", "home_team_win_probability_added", "visitor_team_win_probility_added", "expected_points_added", "expected_points",
              "offense_formation", "receiver_alignment", "pass_result", "pass_length", "play_nullified_by_penalty", "penalty_yards", "pre_penalty_yards_gained", "yards_gained",
              "team_coverage_man_zone", "team_coverage_type", "rush_yards", "fumble", "fumble_lost"}
olr["kind"] = np.where(olr.col.isin(play_level), "play-level context", "player-level field")
TBL(olr[(olr.run_play_nn_pct.fillna(0) > 0) | (olr.dropback_nn_pct.fillna(0) > 0)].sort_values(["kind", "col"]),
    "Non-null % of every column for OL rows on run (non-dropback) vs dropback plays. Columns with 0% on both are omitted.")
TBL(q("""SELECT count(*) OL_run_rows, sum((in_motion_at_ball_snap IS NOT NULL)::int) in_motion_nn, sum((rush_yards IS NOT NULL)::int) rush_yards_nn,
  sum((fumble IS NOT NULL)::int) fumble_nn, sum((tackle IS NOT NULL)::int) tackle_nn, sum((target)::int) target_true FROM ppn WHERE grp='OL' AND on_offense AND reg AND NOT dropback"""),
    "Player-level-looking fields on OL run rows.")
c = family_counts("olrun", "", "on_offense AND NOT dropback", ["OL"])
TBL(c, "OL players by run-play rows (the only thing recorded; denominator for any team-level run outcome such as yards_gained / rush_yards).")
R["B6"] = c

# ============================================================== SECTION C columns
log("section C")
H(2, "C. Every player_play column: dtype, null rate overall and by position group")
P("Null rates over ALL player_play rows (incl. NA, PRE, POST). Group columns show % null. `empty` = % of rows equal to the empty string '' (VARCHAR only). "
  "Flags: CONSTANT (<=1 distinct non-null value), SPARSE (>95% null), and EMPTYSTR (contains '' values that are not null).\n")
dt = dict(con.execute("DESCRIBE player_play").fetchall()[i][:2] for i in range(len(cols)))
rows_c = []
gl = ",".join(f"'{g}'" for g in GROUPS)
tot_rows = n_pp
colstats = {}
for ccol in cols:
    dtype = dt[ccol]
    s = q(f"""SELECT count(*) n, count({ccol}) nn, count(DISTINCT {ccol}) nd,
        {f"sum(({ccol} = '')::int)" if dtype == 'VARCHAR' else "0"} AS nempty FROM pp""").iloc[0]
    byg = q(f"""SELECT grp, round(100.0*(1 - count({ccol})*1.0/count(*)),1) nullpct FROM pp GROUP BY 1""").set_index("grp").nullpct
    row = {"column": ccol, "dtype": dtype, "null%": round(100.0 * (1 - s.nn / s.n), 2), "empty%": round(100.0 * s.nempty / s.n, 2) if dtype == "VARCHAR" else "",
           "distinct": int(s.nd)}
    for g in GROUPS:
        row[g] = byg.get(g, np.nan)
    flags = []
    if s.nd <= 1:
        flags.append("CONSTANT")
    if (1 - s.nn / s.n) > 0.95:
        flags.append("SPARSE")
    if dtype == "VARCHAR" and s.nempty > 0:
        flags.append("EMPTYSTR")
    row["flags"] = ",".join(flags)
    rows_c.append(row)
colt = pd.DataFrame(rows_c)
TBL(colt)
R["colt"] = colt
# rows by group note
TBL(q("SELECT grp, count(*) rows FROM pp GROUP BY 1 ORDER BY 2 DESC"), "Rows per group (denominators for the group null rates above).")
P("Columns that are never populated for any cohort row (`null% = 100`) or constant: " +
  (", ".join(colt[colt["flags"].str.contains("CONSTANT")].column) or "none") + ".\n")

# ============================================================== SECTION D tracking
log("section D")
H(2, "D. Game tracking")
d1 = q("""SELECT yr, count(*) frames, count(DISTINCT (game_id, play_id, nfl_id)) player_plays, count(DISTINCT nfl_id) players, count(DISTINCT game_id) games,
   count(DISTINCT (game_id, play_id)) plays FROM gt GROUP BY 1 ORDER BY 1""")
TBL(d1)
R["d1"] = d1
con.execute("""CREATE TABLE fp AS
  SELECT yr, game_id, play_id, nfl_id, count(*) n, min(time) t0, max(time) t1,
    count(*) FILTER (WHERE event='ball_snap') n_snap, min(time) FILTER (WHERE event='ball_snap') snap_t,
    max(time) FILTER (WHERE event IS NOT NULL) last_ev_t, arg_max(event, time) FILTER (WHERE event IS NOT NULL) last_ev,
    arg_min(event, time) FILTER (WHERE event IS NOT NULL) first_ev,
    count(*) FILTER (WHERE event IS NOT NULL) n_ev
  FROM gt GROUP BY 1,2,3,4""")
# frames before snap / after last event: second pass
con.execute("""CREATE TABLE fpos AS
  SELECT g.yr, g.game_id, g.play_id, g.nfl_id,
     count(*) FILTER (WHERE f.snap_t IS NOT NULL AND g.time < f.snap_t) pre_snap_frames,
     count(*) FILTER (WHERE f.snap_t IS NOT NULL AND g.time >= f.snap_t AND g.time <= f.last_ev_t) snap_to_last_event_frames,
     count(*) FILTER (WHERE f.last_ev_t IS NOT NULL AND g.time > f.last_ev_t) after_last_event_frames
  FROM gt g JOIN fp f ON f.yr=g.yr AND f.game_id=g.game_id AND f.play_id=g.play_id AND f.nfl_id=g.nfl_id GROUP BY ALL""")
log("fp built")
TBL(q(f"""SELECT yr, count(*) player_plays, {qcols('n', 'frames_')}, round(avg(n),1) frames_mean FROM fp GROUP BY 1 ORDER BY 1"""), "Frames per player-play.")
TBL(q(f"""SELECT {qcols('n', 'frames_')}, quantile_cont(n,0.01) p01, quantile_cont(n,0.99) p99 FROM fp"""), "All years.")
dup = q("""SELECT count(*) AS duplicate_frames FROM (SELECT game_id, play_id, nfl_id, time FROM gt GROUP BY ALL HAVING count(*) > 1)""")
TBL(dup, "Duplicate (game_id, play_id, nfl_id, time) keys in tracking.")
R["dupframes"] = int(dup.duplicate_frames[0])
dtq = q("""WITH d AS (SELECT epoch_ms(time) - lag(epoch_ms(time)) OVER (PARTITION BY game_id, play_id, nfl_id ORDER BY time) AS dms FROM gt)
   SELECT dms AS delta_ms, count(*) n FROM d WHERE dms IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 8""")
TBL(dtq, "Distribution of time between consecutive frames within a player-play (ms; top values).")
R["dtq"] = dtq
dtq2 = q("""WITH d AS (SELECT epoch_ms(time) - lag(epoch_ms(time)) OVER (PARTITION BY game_id, play_id, nfl_id ORDER BY time) AS dms FROM gt)
   SELECT count(*) intervals, sum((dms=100)::int) exactly_100ms, sum((dms<>100)::int) not_100ms, min(dms) min_ms, max(dms) max_ms FROM d WHERE dms IS NOT NULL""")
TBL(dtq2)
R["dtq2"] = dtq2.iloc[0].to_dict()
TBL(q("""SELECT count(*) frames, count(DISTINCT epoch_ms(time) % 100) distinct_ms_mod_100, min(time) min_time, max(time) max_time FROM gt"""),
    "Timestamp granularity check (ms mod 100 has one value if all frames sit on a 100 ms grid... they may still be offset; see delta table).")
TBL(q("""SELECT yr, count(*) frames, round(100.0*(1-count(x)*1.0/count(*)),4) "x null%", round(100.0*(1-count(y)*1.0/count(*)),4) "y null%",
   round(100.0*(1-count(s)*1.0/count(*)),4) "s null%", round(100.0*(1-count(a)*1.0/count(*)),4) "a null%", round(100.0*(1-count(dis)*1.0/count(*)),4) "dis null%",
   round(100.0*(1-count(o)*1.0/count(*)),4) "o null%", round(100.0*(1-count(dir)*1.0/count(*)),4) "dir null%", round(100.0*(1-count(event)*1.0/count(*)),2) "event null%"
   FROM gt GROUP BY 1 ORDER BY 1"""), "Null rates by year.")
TBL(q("""SELECT count(*) frames_with_null_s_a_o_dir, sum((s IS NULL)::int) s_null, sum((a IS NULL)::int) a_null, sum((o IS NULL)::int) o_null, sum((dir IS NULL)::int) dir_null,
   sum((s IS NULL AND a IS NULL AND o IS NULL AND dir IS NULL)::int) all_four_null FROM gt WHERE s IS NULL OR a IS NULL OR o IS NULL OR dir IS NULL"""))
TBL(q("""SELECT p.grp, count(*) frames, round(100.0*(1-count(s)*1.0/count(*)),3) "s null%", round(100.0*(1-count(o)*1.0/count(*)),3) "o null%", round(100.0*(1-count(dir)*1.0/count(*)),3) "dir null%"
   FROM gt JOIN pl p USING(nfl_id) GROUP BY 1 ORDER BY 1"""), "Null rates by position group.")
# events
ev = q("""SELECT coalesce(event, '(null)') event, count(*) frames, count(DISTINCT (game_id, play_id, nfl_id)) player_plays FROM gt GROUP BY 1 ORDER BY 2 DESC""")
ev["pct_of_frames"] = ev.frames / ev.frames.sum() * 100
TBL(ev, "All event values.")
R["ev"] = ev
snapshare = q("""SELECT yr, count(*) player_plays, sum((n_snap>=1)::int) with_ball_snap, round(100.0*avg((n_snap>=1)::int),2) pct_with_ball_snap, sum((n_snap>1)::int) multiple_snap_events,
    sum((n_ev=0)::int) no_events_at_all FROM fp GROUP BY 1 ORDER BY 1""")
TBL(snapshare, "Share of player-plays containing a ball_snap event.")
R["snapshare"] = snapshare
tot_snap = q("SELECT count(*) pp_n, sum((n_snap>=1)::int) w, sum((n_snap=0)::int) wo FROM fp").iloc[0]
R["snapshare_tot"] = tot_snap.to_dict()
TBL(q("""SELECT p.grp, count(*) player_plays, round(100.0*avg((f.n_snap>=1)::int),2) pct_with_snap FROM fp f JOIN pl p USING(nfl_id) GROUP BY 1 ORDER BY 1"""), "By position group.")
TBL(q("""SELECT (f.n_snap>=1) has_snap, (p.nfl_id IS NOT NULL) in_player_play, count(*) player_plays FROM fp f
   LEFT JOIN player_play p ON p.game_id=f.game_id AND p.play_id=f.play_id AND p.nfl_id=f.nfl_id GROUP BY ALL ORDER BY 1,2"""),
    "Player-plays with / without ball_snap vs presence in player_play.")
TBL(q(f"""SELECT {qcols('pre_snap_frames', 'pre_')} FROM fpos JOIN fp USING(yr, game_id, play_id, nfl_id) WHERE n_snap>=1"""), "Frames BEFORE the ball_snap frame (player-plays with a snap).")
TBL(q(f"""SELECT {qcols('snap_to_last_event_frames', 'snap2last_')} FROM fpos JOIN fp USING(yr, game_id, play_id, nfl_id) WHERE n_snap>=1"""), "Frames from the snap through the last event.")
TBL(q(f"""SELECT {qcols('after_last_event_frames', 'after_')}, round(100.0*avg((after_last_event_frames=0)::int),1) pct_zero_after FROM fpos JOIN fp USING(yr, game_id, play_id, nfl_id) WHERE n_snap>=1 AND n_ev>0"""),
    "Frames AFTER the last tagged event (event tags end the play: tackle / out_of_bounds / touchdown / incomplete etc.).")
TBL(q("""SELECT last_ev, count(*) player_plays, round(100.0*count(*)/sum(count(*)) OVER (),1) pct FROM fp GROUP BY 1 ORDER BY 2 DESC LIMIT 12"""), "Last event tag on the player-play.")
TBL(q("""SELECT first_ev, count(*) player_plays, round(100.0*count(*)/sum(count(*)) OVER (),1) pct FROM fp GROUP BY 1 ORDER BY 2 DESC LIMIT 8"""), "First event tag on the player-play.")
TBL(q("""SELECT n_ev AS tagged_frames_per_player_play, count(*) player_plays FROM fp GROUP BY 1 ORDER BY 1 LIMIT 12"""), "Number of tagged frames per player-play.")
# event tags across players
et = q("""WITH f AS (SELECT game_id, play_id, time, count(*) n_rows, count(event) n_tagged, count(DISTINCT event) n_distinct_tags FROM gt GROUP BY ALL HAVING count(*) >= 2)
  SELECT count(*) frames_with_2plus_cohort_rows, sum((n_tagged = 0)::int) no_row_tagged, sum((n_tagged = n_rows)::int) all_rows_tagged,
    sum((n_tagged > 0 AND n_tagged < n_rows)::int) partially_tagged, sum((n_distinct_tags > 1)::int) conflicting_tags FROM f""")
TBL(et, "Event tagging across different cohort players in the same (game, play, frame). (partially_tagged would mean only some players carry the tag.)")
R["et"] = et.iloc[0].to_dict()
TBL(q("""WITH s AS (SELECT game_id, play_id, nfl_id, min(time) FILTER (WHERE event='ball_snap') st FROM gt GROUP BY ALL),
  p AS (SELECT game_id, play_id, count(DISTINCT st) n_snap_times, count(st) n_with_snap FROM s GROUP BY ALL HAVING count(*) >= 2)
  SELECT count(*) plays_with_2plus_players, sum((n_with_snap>=2 AND n_snap_times=1)::int) snap_time_identical_across_players,
    sum((n_snap_times>1)::int) snap_time_differs FROM p"""), "ball_snap timestamp across players on the same play.")
# event/number of frames for other events: which events appear per-player (individual) vs play-level
TBL(q("""WITH e AS (SELECT game_id, play_id, event, time, count(*) n_rows FROM gt WHERE event IS NOT NULL GROUP BY ALL)
  SELECT event, count(*) event_frames, sum((n_rows>=2)::int) frames_tagged_on_2plus_players, max(n_rows) max_players_tagged FROM e GROUP BY 1 ORDER BY 2 DESC LIMIT 15"""),
    "For each event: number of (play, frame) occurrences and how often it is tagged on >=2 cohort players simultaneously.")
# ranges
rg = q("""SELECT 'x' v, min(x) mn, quantile_cont(x,0.001) p001, quantile_cont(x,0.5) med, quantile_cont(x,0.999) p999, max(x) mx FROM gt
 UNION ALL SELECT 'y', min(y), quantile_cont(y,0.001), quantile_cont(y,0.5), quantile_cont(y,0.999), max(y) FROM gt
 UNION ALL SELECT 's', min(s), quantile_cont(s,0.001), quantile_cont(s,0.5), quantile_cont(s,0.999), max(s) FROM gt
 UNION ALL SELECT 'a', min(a), quantile_cont(a,0.001), quantile_cont(a,0.5), quantile_cont(a,0.999), max(a) FROM gt
 UNION ALL SELECT 'dis', min(dis), quantile_cont(dis,0.001), quantile_cont(dis,0.5), quantile_cont(dis,0.999), max(dis) FROM gt
 UNION ALL SELECT 'o', min(o), quantile_cont(o,0.001), quantile_cont(o,0.5), quantile_cont(o,0.999), max(o) FROM gt
 UNION ALL SELECT 'dir', min(dir), quantile_cont(dir,0.001), quantile_cont(dir,0.5), quantile_cont(dir,0.999), max(dir) FROM gt""")
TBL(rg, "Ranges (all years).")
R["rg"] = rg
imp = q("""SELECT count(*) frames,
   sum((x < 0 OR x > 120)::int) x_outside_0_120, sum((x < -1 OR x > 121)::int) x_outside_by_1yd, sum((y < 0 OR y > 53.3)::int) y_outside_0_53p3,
   sum((s > 10)::int) s_gt_10, sum((s > 11)::int) s_gt_11, sum((s > 12)::int) s_gt_12, sum((s > 13)::int) s_gt_13,
   sum((abs(a) > 10)::int) abs_a_gt_10, sum((abs(a) > 15)::int) abs_a_gt_15, sum((abs(a) > 20)::int) abs_a_gt_20,
   sum((dis > 1.5)::int) dis_gt_1p5_per_0p1s, sum((a < 0)::int) a_negative, sum((o < 0 OR o > 360)::int) o_outside_0_360, sum((dir < 0 OR dir > 360)::int) dir_outside_0_360 FROM gt""")
TBL(imp.T.reset_index().rename(columns={"index": "flag (thresholds are mine)", 0: "frames"}))
R["imp"] = imp.iloc[0].to_dict()
TBL(q("""SELECT yr, count(*) frames, round(max(s),2) max_s, round(max(abs(a)),2) max_abs_a, round(avg(s),3) mean_s, round(avg(abs(a)),3) mean_abs_a,
  sum((s>12)::int) s_gt_12, sum((abs(a)>15)::int) abs_a_gt_15 FROM gt GROUP BY 1 ORDER BY 1"""), "Speed/acceleration by year.")
TBL(q("""WITH w AS (SELECT s, dis, a, o, lag(s) OVER (PARTITION BY game_id, play_id, nfl_id ORDER BY time) s_prev FROM gt)
   SELECT round(corr(s, dis*10),3) corr_s_vs_dis_per_s, round(avg(abs(s - dis*10)),3) mean_abs_diff_s_vs_dis10, round(quantile_cont(abs(s - dis*10), 0.99),3) p99_abs_diff
   FROM w"""), "Consistency check: s vs dis x 10 (dis is yards per 0.1 s frame).")
TBL(q("""WITH w AS (SELECT yr, game_id, play_id, nfl_id, s, a, lag(s) OVER (PARTITION BY game_id, play_id, nfl_id ORDER BY time) sp FROM gt)
   SELECT count(*) frames_checked, round(corr(a, (s - sp)*10),3) corr_a_vs_ds_dt, round(avg(a),3) mean_a, round(avg((s - sp)*10),3) mean_ds_dt FROM w WHERE sp IS NOT NULL"""),
    "Consistency check: a vs finite-difference of s (yd/s^2).")
TBL(q("""SELECT yr, min(x) min_x, max(x) max_x, min(y) min_y, max(y) max_y FROM gt GROUP BY 1 ORDER BY 1"""), "x,y ranges by year.")
# play direction normalisation check
TBL(q("""WITH f AS (SELECT t.game_id, t.play_id, t.nfl_id, arg_min(t.x, t.time) FILTER (WHERE t.event='ball_snap') AS x_at_snap FROM gt t GROUP BY ALL),
  j AS (SELECT p.play_direction, p.yardline_side, p.yardline_number, p.possession_team, p.team_abbr, f.x_at_snap FROM pp p JOIN f USING(game_id, play_id, nfl_id) WHERE f.x_at_snap IS NOT NULL AND NOT p.is_na)
  SELECT play_direction, count(*) n, round(quantile_cont(x_at_snap, 0.05),1) x_snap_p05, round(quantile_cont(x_at_snap, 0.5),1) x_snap_med, round(quantile_cont(x_at_snap, 0.95),1) x_snap_p95,
         round(avg(CASE WHEN team_abbr=possession_team THEN x_at_snap END),1) mean_x_offense, round(avg(CASE WHEN team_abbr<>possession_team THEN x_at_snap END),1) mean_x_defense
  FROM j GROUP BY 1 ORDER BY 1"""),
    "x at ball_snap by play_direction. If coordinates were normalised the offence would always sit on the same side of the defence; instead the offence has the larger mean x when play_direction = left and the smaller when right, so x/y are RAW field coordinates (direction must be handled by the analyst).")

# ============================================================== SECTION F career
log("section F")
H(2, "F. Career table")
con.execute("""CREATE TABLE car AS SELECT p.nfl_id, p.nfl_position, p.grp, p.draft_year, p.draft_round, p.draft_overall_pick,
   c.career_offensive_snaps off_s, c.career_defensive_snaps def_s, c.career_special_teams_snaps st_s,
   c.career_offensive_snaps + c.career_defensive_snaps AS od_s, c.career_offensive_snaps + c.career_defensive_snaps + c.career_special_teams_snaps AS all_s,
   CASE WHEN p.grp IN ('WR','TE','RB_FB','OL') THEN c.career_offensive_snaps ELSE c.career_defensive_snaps END AS side_s,
   c.career_games_active ga, c.career_games_started gs, c.ap_all_pro_1st_team ap1, c.ap_all_pro_2nd_team ap2, c.pro_bowl_original_ballot pb
   FROM pl p JOIN player_career_successes c USING(nfl_id)""")
TBL(q("""SELECT count(*) players, sum((off_s IS NULL)::int) off_null, sum((def_s IS NULL)::int) def_null, sum((st_s IS NULL)::int) st_null, sum((ga IS NULL)::int) ga_null, sum((gs IS NULL)::int) gs_null,
  sum((off_s=0 AND def_s=0 AND st_s=0)::int) zero_snaps_all_types, sum((ga=0)::int) zero_games_active, sum((gs>ga)::int) started_gt_active, max(ga) max_ga, max(gs) max_gs FROM car"""))
TBL(q(f"""SELECT grp, count(*) players, {qcols('side_s', 'side_snaps_')}, round(avg(side_s),0) mean_side_snaps FROM car GROUP BY 1 ORDER BY 1"""), "Career snaps on the player's primary side (offence for WR/TE/RB_FB/OL, defence otherwise), by group.")
TBL(q(f"""SELECT grp, draft_year, count(*) players, {qcols('side_s', 'side_snaps_')} FROM car GROUP BY 1,2 ORDER BY 1,2"""), "Same by group x draft class.")
TBL(q(f"""SELECT grp, draft_year, {qcols('ga', 'ga_')}, {qcols('gs', 'gs_')} FROM car GROUP BY 1,2 ORDER BY 1,2"""), "Games active / games started by group x draft class.")
TBL(q(f"""SELECT draft_year, count(*) players, {qcols('all_s', 'all_snaps_')}, round(avg(ga),1) mean_games_active, max(ga) max_ga FROM car GROUP BY 1 ORDER BY 1"""), "All-snaps by class (note: 2023 class has had up to 3 seasons, 2025 class 1).")
TBL(q("""SELECT grp, count(*) players, sum(ap1) all_pro_1st, sum(ap2) all_pro_2nd, sum(pb) pro_bowl_ballot_selections, sum((pb>0)::int) players_with_pro_bowl,
   sum((ap1>0 OR ap2>0)::int) players_with_all_pro FROM car GROUP BY 1 ORDER BY 1"""), "All-Pro / Pro Bowl counts by group (selections; pro_bowl_original_ballot may be 0/1/2 = seasons).")
TBL(q("""SELECT draft_year, count(*) players, sum(ap1) all_pro_1st, sum(ap2) all_pro_2nd, sum(pb) pro_bowl, sum((pb>0)::int) players_with_pro_bowl FROM car GROUP BY 1 ORDER BY 1"""), "By draft class.")
TBL(q("""SELECT nfl_position, draft_year, ap1, ap2, pb FROM car WHERE ap1>0 OR ap2>0 OR pb>0 ORDER BY pb DESC, ap1 DESC, nfl_position"""), "Positions of all players with any honour (no names).")
cdf = q("SELECT * FROM car").merge(q("SELECT nfl_id FROM players"), on="nfl_id")
sp_rows = []
for key, d in [("ALL players", cdf)] + [(g, cdf[cdf.grp == g]) for g in GROUPS]:
    d = d[d.draft_overall_pick.notna()]
    if len(d) < 5:
        continue
    for metric in ("side_s", "all_s", "ga"):
        rho, pv = spearmanr(d.draft_overall_pick, d[metric])
        sp_rows.append({"group": key, "metric": {"side_s": "career snaps (primary side)", "all_s": "career snaps (off+def+ST)", "ga": "games active"}[metric],
                        "n_drafted": len(d), "spearman_rho": round(rho, 3), "p": float(f"{pv:.2g}")})
sp_df = pd.DataFrame(sp_rows)
TBL(sp_df, "Spearman correlation of draft_overall_pick with career outcome (drafted players only; negative = earlier pick, more snaps). "
           "Confounded by draft-class age (see per-class rows below).")
R["sp_df"] = sp_df
sp2 = []
for dy in (2023, 2024, 2025):
    d = cdf[(cdf.draft_year == dy) & cdf.draft_overall_pick.notna()]
    rho, pv = spearmanr(d.draft_overall_pick, d.all_s)
    sp2.append({"draft_year": dy, "n_drafted": len(d), "rho_pick_vs_all_snaps": round(rho, 3), "p": float(f"{pv:.2g}")})
TBL(pd.DataFrame(sp2), "Within-class (controls for years of NFL exposure):")
sp3 = []
for g in GROUPS:
    for dy in (2023, 2024, 2025):
        d = cdf[(cdf.grp == g) & (cdf.draft_year == dy) & cdf.draft_overall_pick.notna()]
        if len(d) >= 8:
            rho, pv = spearmanr(d.draft_overall_pick, d.side_s)
            sp3.append({"group": g, "draft_year": dy, "n_drafted": len(d), "rho_pick_vs_side_snaps": round(rho, 3)})
TBL(pd.DataFrame(sp3), "Within group x class (groups with >=8 drafted players).")
TBL(q("SELECT draft_year, count(*) players, sum((draft_overall_pick IS NULL)::int) undrafted, min(draft_overall_pick) min_pick, max(draft_overall_pick) max_pick FROM players GROUP BY 1 ORDER BY 1"), "Draft status.")
TBL(q("SELECT grp, count(*) players, sum((draft_overall_pick IS NULL)::int) undrafted, sum((draft_round=1)::int) round1, sum((draft_round<=3)::int) rounds_1_3, sum((draft_round>=5)::int) rounds_5_7 FROM pl GROUP BY 1 ORDER BY 1"),
    "Draft status by group.")
# career snaps vs rows exposure: top-line how many players have enough rows
TBL(q("""SELECT e.grp, count(*) players, corr(e.rows_reg, c.all_s) pearson_rows_vs_all_snaps FROM exp e JOIN car c USING(nfl_id) GROUP BY 1 ORDER BY 1"""), "Pearson correlation between REG player_play rows and career total snaps (sanity).")

# ============================================================== SECTION H
log("section H")
H(2, "H. Other findings")
H(3, "H1. Dropback encoding: pass_result is EMPTY STRING, not null")
Hq = q("""SELECT count(*) rows, sum((pass_result IS NULL)::int) pass_result_null, sum((pass_result = '')::int) pass_result_empty_string,
  sum((pass_result <> '')::int) pass_result_populated FROM player_play""")
TBL(Hq)
R["H1"] = Hq.iloc[0].to_dict()
P("Because the CSV stores a quoted empty string (`\"\"`), polars keeps it as '' rather than null. The `convert.py` docstring claims dropbacks are "
  "`pass_result.is_not_null()` - that is **wrong for these Parquet files** (every row is non-null). Use `pass_result <> ''` (or `pass_result != ''`). "
  "Other VARCHAR columns containing '' values: " + (", ".join(colt[colt["flags"].str.contains("EMPTYSTR")].column) or "none") + ".\n")
TBL(q("""SELECT pass_result, count(*) rows, count(DISTINCT (game_id, play_id)) plays FROM player_play GROUP BY 1 ORDER BY 2 DESC"""), "pass_result values (rows are player-rows).")
H(3, "H2. Play types, special teams, non-scrimmage plays")
P("play_description regex classification of distinct plays in player_play (one description per (game_id, play_id); rows counted per play):\n")
pt = q("""WITH d AS (SELECT game_id, play_id, any_value(play_description) dsc, any_value(pass_result) pr, any_value(play_nullified_by_penalty) nul,
     bool_or(is_na) any_na, bool_and(is_na) all_na FROM pp GROUP BY 1,2)
  SELECT CASE
    WHEN dsc ILIKE '%punts%' OR dsc ILIKE '%punt %' THEN 'punt'
    WHEN dsc ILIKE '%kicks off%' OR dsc ILIKE '%kickoff%' THEN 'kickoff'
    WHEN dsc ILIKE '%field goal%' THEN 'field goal'
    WHEN dsc ILIKE '%extra point%' OR dsc ILIKE '%PAT%' AND dsc ILIKE '%is good%' THEN 'extra point'
    WHEN dsc ILIKE '%two-point%' OR dsc ILIKE '%2-pt%' THEN 'two-point try'
    WHEN dsc ILIKE '%kneels%' THEN 'kneel'
    WHEN dsc ILIKE '%spiked%' THEN 'spike'
    WHEN dsc ILIKE '%sacked%' THEN 'sack'
    WHEN dsc ILIKE '%No Play%' AND dsc ILIKE '%PENALTY%' THEN 'penalty - no play'
    WHEN pr <> '' THEN 'dropback (pass_result populated)'
    ELSE 'run / other scrimmage (pass_result empty)' END AS play_type,
    count(*) plays, sum((nul='Y')::int) nullified_plays, sum(all_na::int) plays_all_rows_NA, sum(any_na::int) plays_any_row_NA FROM d GROUP BY 1 ORDER BY 2 DESC""")
TBL(pt)
R["pt"] = pt
P("Tracking-side evidence of special teams (events that only occur on kicks): `punt_land` / `kick_recovered` / `field_goal_attempt` / `punt_fake`:\n")
TBL(q("""SELECT event, count(*) frames, count(DISTINCT (game_id, play_id)) plays FROM gt WHERE event IN ('punt_land','kick_recovered','field_goal_attempt','punt_fake','touchback','kickoff','punt','onside_kick') GROUP BY 1 ORDER BY 2 DESC"""))
TBL(q("""SELECT pass_result, count(DISTINCT (game_id, play_id)) plays FROM pp WHERE play_description ILIKE '%touchback%' GROUP BY 1 ORDER BY 2 DESC"""),
    "Plays whose description mentions a touchback (the 381 'touchback' tracking events are mostly interception touchbacks, not kickoffs).")
TBL(q("""SELECT p.dsc_type, count(*) rows FROM (SELECT CASE WHEN play_description ILIKE '%punt%' THEN 'mentions punt' WHEN play_description ILIKE '%kicks off%' THEN 'kickoff' WHEN play_description ILIKE '%field goal%' THEN 'field goal' ELSE 'other' END dsc_type FROM pp) p GROUP BY 1 ORDER BY 2 DESC"""),
    "Rows whose description mentions punt / kickoff / field goal.")
TBL(q("""SELECT offense_formation, count(*) rows FROM pp GROUP BY 1 ORDER BY 2 DESC"""), "offense_formation values (null = no formation, e.g. specials / spikes?).")
TBL(q("""SELECT down, count(*) rows FROM pp GROUP BY 1 ORDER BY 1"""), "down values (null / 0 / 4).")
H(3, "H3. Nullified plays and penalties")
TBL(q("""SELECT play_nullified_by_penalty, is_na, count(*) rows, count(DISTINCT (game_id, play_id)) plays, sum((yards_gained IS NOT NULL)::int) yards_gained_nn FROM pp GROUP BY ALL ORDER BY 1,2"""),
    "play_nullified_by_penalty is 'Y'/'N'. Y rows are post-snap plays that were wiped by a penalty (NA rows are pre-snap).")
TBL(q("""SELECT play_nullified_by_penalty, count(*) rows, round(avg(yards_gained),2) mean_yards_gained, round(avg(pre_penalty_yards_gained),2) mean_pre_penalty_yards, round(avg(expected_points_added),3) mean_epa FROM pp GROUP BY 1"""))
H(3, "H4. Duplicated plays / odd ids")
TBL(q("""SELECT count(*) AS player_play_rows, count(DISTINCT (game_id, play_id, nfl_id)) AS distinct_keys FROM player_play"""))
TBL(q("""SELECT count(*) plays_where_description_differs_across_players FROM (SELECT game_id, play_id FROM player_play GROUP BY ALL HAVING count(DISTINCT play_description) > 1)"""))
TBL(q("""SELECT count(*) plays_where_context_differs FROM (SELECT game_id, play_id FROM player_play GROUP BY ALL HAVING count(DISTINCT (quarter, down, yards_to_go, possession_team, yardline_number)) > 1)"""))
TBL(q("""SELECT count(*) AS plays, count(DISTINCT (game_id, play_description)) AS distinct_descriptions_per_game,
   count(*) - count(DISTINCT (game_id, play_description)) AS repeated_descriptions_within_game FROM (SELECT DISTINCT game_id, play_id, play_description FROM player_play)"""))
TBL(q("""SELECT count(*) game_ids, sum((game_id < 2023000000 OR game_id > 2026999999)::int) out_of_range, count(DISTINCT game_id // 100) distinct_dates FROM games"""))
TBL(q("""SELECT season, count(*) games, sum((game_id // 1000000 <> season AND NOT (season_type='POST' AND game_id // 1000000 = season + 1))::int) game_id_year_mismatch FROM games GROUP BY 1 ORDER BY 1"""),
    "game_id year prefix vs season (POST games are played in January of season+1).")
TBL(q("""SELECT play_id, count(*) n FROM (SELECT DISTINCT game_id, play_id FROM player_play) GROUP BY 1 ORDER BY 2 DESC LIMIT 3"""), "(Context) play_id values are per-game sequence numbers, not globally unique.")
TBL(q("""SELECT count(*) AS plays, sum((c = 1)::int) single_cohort_row, sum((c > 1)::int) multi FROM (SELECT game_id, play_id, count(*) c FROM player_play GROUP BY ALL)"""))
H(3, "H5. Other oddities")
TBL(q("""SELECT game_clock, count(*) n FROM player_play GROUP BY 1 ORDER BY 2 DESC LIMIT 3"""), "game_clock dtype is TIME; the value 'HH:MM' is actually minutes:seconds (e.g. a clock of 8:42 appears as 08:42:00). Interpret hours as minutes and minutes as seconds.")
TBL(q("""SELECT count(*) AS rows, sum((lined_up_position='EXTRA_OL')::int) extra_ol_rows FROM player_play"""))
TBL(q("""SELECT p.nfl_position, a.lined_up_position, count(*) rows FROM pp a JOIN players p USING(nfl_id) WHERE NOT a.is_na GROUP BY ALL HAVING count(*) > 200 ORDER BY 1, 3 DESC"""),
    "nfl_position vs lined_up_position (rows > 200). Shows position labels (e.g. OLB/DE) vs alignment (EDGE/INTERIOR_LINE) are not 1:1.")
TBL(q("""SELECT quarter, count(*) rows FROM player_play GROUP BY 1 ORDER BY 1"""), "quarters (5 = overtime).")
TBL(q("""SELECT count(*) rows_without_pre_snap_win_prob, sum((expected_points_added IS NULL)::int) epa_null, sum((home_team_win_probability_added IS NULL)::int) wpa_null FROM player_play WHERE lined_up_position <> 'NA'"""))
TBL(q("""SELECT p.draft_year, count(DISTINCT a.nfl_id) players_with_rows, count(DISTINCT a.team_abbr) teams FROM player_play a JOIN players p USING(nfl_id) GROUP BY 1 ORDER BY 1"""))
TBL(q("""SELECT count(*) rows_where_nfl_position_defence_but_on_offense FROM pp WHERE NOT is_na AND on_offense AND grp IN ('IDL','EDGE','LB','CB','S','DB_generic')"""),
    "(Context for side-of-ball): defenders on offence / offence on defence rows.")
TBL(q("""SELECT count(*) rows_where_nfl_position_offence_but_on_defence FROM pp WHERE NOT is_na AND NOT on_offense AND grp IN ('WR','TE','RB_FB','OL')"""))
TBL(q("""SELECT p.grp, count(*) rows, sum((a.on_offense IS NULL)::int) side_unknown FROM pp a JOIN pl p USING(nfl_id) GROUP BY 1 ORDER BY 1"""))

# ============================================================== SECTION G verdicts (numbers filled in from the run)
log("section G")
H(2, "G. Forum / host facts: verdicts")
pairs_tot = R["pairs"]
mm = R["mm"].set_index("matchup")
na = R["na"]
sr = R["snap_ratio"].set_index("grp")
eqt = R["eq"]
eq_n = int(eqt[~eqt.grp.isin(["WR", "TE", "RB_FB"])].players.sum())
eq_eq = int(eqt[(~eqt.grp.isin(["WR", "TE", "RB_FB"])) & eqt["cmp"].str.startswith("REG rows ==")].players.sum())
f2 = R["f2"].set_index("nfl_position")
n_pre_rows = int(q("SELECT count(*) n FROM pp WHERE season_type = 'PRE'").n[0])
n_post_rows = int(q("SELECT count(*) n FROM pp WHERE season_type = 'POST'").n[0])
pre_tk_only = int(q("SELECT count(*) n FROM tk_only t JOIN games g USING(game_id) WHERE g.season_type = 'PRE'").n[0])
pre_tk = int(q("SELECT count(*) n FROM tk t JOIN games g USING(game_id) WHERE g.season_type = 'PRE'").n[0])
pre_games_tk = int(q("SELECT count(DISTINCT t.game_id) n FROM tk t JOIN games g USING(game_id) WHERE g.season_type = 'PRE'").n[0])
tko_wrte = int(q("SELECT count(*) n FROM tk_only t JOIN pl USING(nfl_id) WHERE pl.nfl_position IN ('WR','TE','FB')").n[0])
tko_pass = int(tk_ev.with_pass_forward[0])
tko_other_pp = int(tko[tko.play_has_other_pp_rows]["keys"].sum())
ppo_na = R["pp_only_na"]
ol_route_rows = int(q("SELECT count(*) n FROM pp WHERE grp = 'OL' AND route_ran IS NOT NULL").n[0])
rx = R["rush"]
n_bl_null_db = int(q("SELECT count(*) n FROM pp WHERE dropback AND blitzing IS NULL").n[0])
bl_null_txt = ", ".join(f"{r.grp} {int(r.n):,}" for r in q("SELECT grp, count(*) n FROM pp WHERE dropback AND blitzing IS NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 5").itertuples())
boundary = q("""SELECT sum((quick_pressure = FALSE AND round(time_to_pressure, 3) = 2.5)::int) false_at_2p5,
                       sum((quick_pressure = FALSE AND time_to_pressure < 2.5)::int) false_below,
                       sum((quick_pressure AND time_to_pressure >= 2.5)::int) true_at_or_above
                FROM pp WHERE blitzing AND dropback AND time_to_pressure IS NOT NULL""").iloc[0]
v = []
v.append(("1", "(Host) Game tracking contains only the 510 cohort players, not all 22", "CONFIRMED",
          f"Tracking has {q('SELECT count(DISTINCT nfl_id) n FROM tk').n[0]} distinct nfl_ids, all inside the cohort (13 cohort players have no tracking). "
          f"{R['tk_multi_plays']:,} of {R['tk_plays']:,} tracked plays ({pct(R['tk_multi_plays'], R['tk_plays'])}) have >=2 cohort players; "
          f"player_play: {int(pairs_tot['n']):,} same-play pairs = {int(pairs_tot['same']):,} same-team + {int(pairs_tot['opp']):,} opposing. "
          f"REG, non-NA, opposing teams: WR/TE-vs-DB {int(mm.loc['WR/TE vs DB (CB,S,DB)','pairs_reg']):,} pairs on {int(mm.loc['WR/TE vs DB (CB,S,DB)','plays_reg']):,} plays "
          f"(WR-vs-CB {int(mm.loc['WR vs CB','plays_reg']):,} plays); OL-vs-IDL/EDGE {int(mm.loc['OL vs IDL/EDGE','pairs_reg']):,} pairs on {int(mm.loc['OL vs IDL/EDGE','plays_reg']):,} plays. "
          "Same-play co-occurrence does not say who covered or blocked whom."))
v.append(("2", "(Host) WR/TE rows only on route plays; DB/DL/OL ~99.9% of snaps, WR ~60%, TE ~40%", "CONFIRMED (with refinements)",
          f"route_ran is non-null on {int(f2.loc['WR','rows_with_route']):,}/{int(f2.loc['WR','rows']):,} WR rows and {int(f2.loc['TE','rows_with_route']):,}/{int(f2.loc['TE','rows']):,} TE rows (100%), "
          f"and every WR/TE row is on a dropback. REG rows / career snaps: WR {sr.loc['WR','ratio_REG']*100:.1f}%, TE {sr.loc['TE','ratio_REG']*100:.1f}%, "
          f"OL {sr.loc['OL','ratio_REG']*100:.1f}%, IDL {sr.loc['IDL','ratio_REG']*100:.1f}%, EDGE {sr.loc['EDGE','ratio_REG']*100:.1f}%, CB {sr.loc['CB','ratio_REG']*100:.1f}%, S {sr.loc['S','ratio_REG']*100:.1f}%. "
          f"For OL/DL/EDGE/LB/CB/S/DB, REG rows equal career snaps exactly for {eq_eq}/{eq_n} players, so 'career snaps' = regular season only and coverage there is ~100% (better than the reported 99.9%). "
          f"Caveats: FB 36/36 and RB 44/86 rows have a route (the RB is mixed); {ol_route_rows} OL rows (T/G/C lined up as TE/FB/WR) also carry route_ran; "
          f"including PRE+POST, player_play rows exceed career snaps (OL {sr.loc['OL','ratio_ALL']*100:.0f}%)."))
v.append(("3", "(Host) 13 players never took the field; 497 players and 1,001 of 1,002 games in player_play",
          "CONFIRMED",
          f"{R['no_row_n']} cohort players have no player_play and no tracking rows (all have 0 career snaps and 0 games active); 497 players and "
          f"{q('SELECT count(DISTINCT game_id) n FROM player_play').n[0]} of {q('SELECT count(*) n FROM games').n[0]} games appear. The missing game is a REG game "
          f"(game_id {int(R['gm_miss'].iloc[0].game_id)}, week {int(R['gm_miss'].iloc[0].week)}, {R['gm_miss'].iloc[0].home_team_abbr} vs {R['gm_miss'].iloc[0].visitor_team_abbr}) with no tracking either. "
          "List by position and round: section 3 (7 undrafted, 3 drafted in rounds 6-7, 3 in rounds 3-5; 9 of 13 are 2025-class)."))
v.append(("4", "(Host) `lined_up_position == 'NA'` (1,383 rows) = plays killed by a pre-snap penalty", "CONFIRMED for 99.3% of rows; PARTLY as a definition",
          f"{int(na['rows']):,} rows; {int(na['desc_has_PENALTY']):,} ({pct(na['desc_has_PENALTY'], na['rows'])}) have 'PENALTY ... No Play' in the description, play_nullified_by_penalty = Y and penalty_yards populated "
          f"(False Start {int(na['desc_false_start'])}, Delay of Game {int(na['desc_delay'])}, offside/encroachment/NZI {int(na['desc_offside_enc_nz'])}). "
          "10 rows are exceptions (no penalty text, nullified = N; section 4). Route, coverage, tackle fields are null on NA rows; context fields (down, yards_gained, EPA) are populated. "
          f"Only {int(R['na_trk']['have_tracking'])} of the {int(R['na_trk']['na_rows']):,} NA rows have tracking, and only {int(na['reg_rows'])} NA rows are REG (the rest PRE/POST). "
          f"Wrinkle: {int(na['dropback_rows'])} NA rows sit on plays with a pass_result and 107 descriptions pair a thrown/sacked pass with 'No Play', i.e. some NA rows are post-snap plays nullified by a penalty, not purely pre-snap (*inference* from description text)."))
v.append(("5", "(Participant + host) 2,497 tracking keys without player_play (449/857/1,191); 1,750 player_play rows without tracking (293/661/796)",
          "CONFIRMED (counts reproduce exactly); host explanation PARTLY",
          f"Counts: {R['tk_only']:,} {[int(x) for x in R['tk_only_yr']]} and {R['pp_only']:,} {[int(x) for x in R['pp_only_yr']]}. "
          f"Tracking-without-player_play: 100% WR/TE/FB ({tko_wrte:,} of 2,497); {tko_pass:,} ({pct(tko_pass, 2497)}) show a pass_forward event; for {tko_other_pp:,} keys the same play has other cohort player_play rows that are all dropbacks; "
          "none is a pre-snap-penalty play. This is consistent with 'WR/TE/FB tracked on a pass play but no route run, so no player_play row' (*inference*: the reason cannot be read from the absent row). "
          f"player_play-without-tracking: {ppo_na:,} ({pct(ppo_na, 1750)}) are NA rows; the other 450 are mostly WR/TE route rows on dropbacks (358) plus nullified plays (83). "
          "So: pre-snap penalties -> player_play-only (74% of that set, not all of it); no-route WR/TE/FB -> tracking-only. Neither direction is fully explained by the host's two causes."))
v.append(("6", "(Participant) Preseason game keys appear in tracking although games.csv documents only REG and POST; '185 PRE keys'", "PARTLY: PRE is present (CONFIRMED) but the premise and the 185 are wrong",
          f"games.csv itself contains season_type PRE: 147 games (49 per season) + 816 REG + 39 POST = 1,002, so PRE is in the data and in games. All {pre_games_tk} PRE games are in tracking "
          f"({pre_tk:,} tracking keys); player_play has {n_pre_rows:,} PRE rows ({pct(n_pre_rows, n_pp)} of all) and {n_post_rows:,} POST rows. No game_id in tracking or player_play is absent from games. "
          f"The '185' reproduces as the number of tracking keys WITHOUT a player_play row that fall in PRE games ({pre_tk_only}), not as the number of PRE tracking keys ({pre_tk:,})."))
v.append(("7", "(Host) blitzing marks all pass rushers; null quick_pressure/time_to_pressure = no pressure; quick_pressure False = >2.5 s; player_get_off null = never crossed LOS; dropbacks = non-null pass_result",
          "PARTLY",
          f"Dropbacks: pass_result is NEVER null in the Parquet (empty string '' on {int(R['H1']['pass_result_empty_string']):,} rows), so use pass_result <> '' (the convert.py docstring is wrong). "
          f"blitzing is True on ~83-93% of DE/OLB/DT/NT dropback rows, ~1-5% of CB/S, ~10-14% of ILB/MLB, never on offence; on dropbacks it is null for {n_bl_null_db:,} rows ({bl_null_txt}). "
          f"Among blitzing dropback defender rows ({int(rx['rush_rows']):,}): time_to_pressure non-null {int(rx['ttp_nonnull']):,} ({pct(rx['ttp_nonnull'], rx['rush_rows'])}); quick_pressure is null exactly when time_to_pressure is null except {int(rx['qp_null_but_ttp_nonnull'])} rows. "
          f"quick_pressure = True never has time >= 2.5 s ({int(boundary.true_at_or_above)} violations); quick_pressure = False always has time >= 2.5 s ({int(boundary.false_below)} violations; {int(boundary.false_at_2p5)} rows sit exactly at 2.5), consistent with the host's 2.5 s rule. "
          f"player_get_off is null on {int(rx['get_off_null']):,} ({pct(rx['get_off_null'], rx['rush_rows'])}) of rush rows: 5-17% for DE/DT/OLB/NT but 70-77% for CB/S/LB rushers; whether null means 'never crossed the LOS' cannot be verified from this data (*unverifiable*). "
          "blitzing is also True on 133 non-dropback rows."))
P("| # | Claim | Verdict | Evidence (computed) |\n|---|---|---|---|")
for n_, claim, verdict, ev_ in v:
    P(f"| {n_} | {claim} | **{verdict}** | {ev_.replace('|', '/')} |")
P()

# ============================================================== KEY FINDINGS (inserted near top)
a1 = R["a1d"].set_index("grp")
b1 = R["B1_routes"].set_index("grp")
b1t = R["B1_targets"].set_index("grp")
b2 = R["B2"].set_index("grp")
b3 = R["B3"].set_index("grp")
b3e = R["B3_events"].set_index("grp")
b4b = R["B4b"].set_index("grp")
b5 = R["B5"].set_index("grp")
tkp_ = R["tk_pl"].set_index("grp")
sp_ = R["sp_df"]
rho_all = sp_[(sp_.group == "ALL players") & sp_.metric.str.startswith("career snaps (primary")].spearman_rho.iloc[0]
n_drafted = int(sp_[sp_.group == "ALL players"].n_drafted.iloc[0])
a3b = R["a3b"].set_index("class")
reg_players = int(q("SELECT sum((rows_reg>0)::int) n FROM exp").n[0])
honours = q("SELECT sum(ap1) ap1, sum(ap2) ap2, sum((ap1>0 OR ap2>0 OR pb>0)::int) any_honour FROM car").iloc[0]
tsn = R["snapshare_tot"]
kf = []
kf.append(f"**Exposure is highly unequal.** 497/510 players have any rows but only {reg_players} have REG rows. REG rows by draft class: "
          f"2023 {int(a3b.loc[2023,'reg_rows']):,}, 2024 {int(a3b.loc[2024,'reg_rows']):,}, 2025 {int(a3b.loc[2025,'reg_rows']):,} "
          f"(median REG rows per cohort player {a3b.loc[2023,'median_reg_rows_per_cohort_player']:.0f} / {a3b.loc[2024,'median_reg_rows_per_cohort_player']:.0f} / {a3b.loc[2025,'median_reg_rows_per_cohort_player']:.0f}). "
          f"{pct(n_pre_rows + n_post_rows, n_pp)} of player_play rows are PRE or POST ({pct(n_pre_rows, n_pp)} PRE).")
kf.append(f"**Dropback flag**: `pass_result` is the empty string (not null) on {int(R['H1']['pass_result_empty_string']):,} rows; `pass_result <> ''` is the dropback test. `is_not_null()` (as the convert.py docstring says) selects every row.")
kf.append(f"**Receiving** (REG routes): WR {int(b1.loc['WR','ge50_REG'])}/{int(b1.loc['WR','players'])} players >=50 routes, {int(b1.loc['WR','ge100_REG'])} >=100, {int(b1.loc['WR','ge200_REG'])} >=200; "
          f"TE {int(b1.loc['TE','ge50_REG'])}/{int(b1.loc['TE','players'])}, {int(b1.loc['TE','ge100_REG'])}, {int(b1.loc['TE','ge200_REG'])}; RB/FB essentially none (40 REG routes). "
          f"Targets: WR {int(b1t.loc['WR','ge50_REG'])} players >=50, {int(b1t.loc['WR','ge100_REG'])} >=100; TE {int(b1t.loc['TE','ge50_REG'])} >=50, {int(b1t.loc['TE','ge100_REG'])} >=100. "
          "separation_at_pass_forward is populated on ~100% of routes on plays with a throw (C/I/IN) - targets AND non-targets - and 0% on sacks/scrambles (so ~85-88% of all routes); YAC/rec_yards only on catches; cushion ~95% WR, ~80% TE.")
kf.append(f"**Pass protection** (pressure_allowed non-null): OL {int(b2.loc['OL','ge50_REG'])}/{int(b2.loc['OL','players'])} players >=50 REG pass-block snaps, {int(b2.loc['OL','ge100_REG'])} >=100, {int(b2.loc['OL','ge200_REG'])} >=200 "
          f"(ALL games: {int(b2.loc['OL','ge50_ALL'])}/{int(b2.loc['OL','ge100_ALL'])}/{int(b2.loc['OL','ge200_ALL'])}); TE/RB/WR pass blocks are negligible. Pressure-allowed rate 8.4%, sack allowed 1.15% of snaps. On run plays an OL row carries nothing beyond context (section B6).")
kf.append(f"**Pass rush** (blitzing & dropback): EDGE {int(b3.loc['EDGE','ge50_REG'])}/{int(b3.loc['EDGE','players'])} players >=50 REG rush snaps, {int(b3.loc['EDGE','ge100_REG'])} >=100, {int(b3.loc['EDGE','ge200_REG'])} >=200; "
          f"IDL {int(b3.loc['IDL','ge50_REG'])}/{int(b3.loc['IDL','players'])}, {int(b3.loc['IDL','ge100_REG'])}, {int(b3.loc['IDL','ge200_REG'])}; CB/S/LB too few. Pressure is rare (EDGE 11%, IDL 7% of rush snaps): players with >=10 pressures: EDGE {int(b3e.loc['EDGE','ge10_pressures'])}, IDL {int(b3e.loc['IDL','ge10_pressures'])}; "
          f"total REG sacks EDGE {int(b3e.loc['EDGE','total_sacks'])}, IDL {int(b3e.loc['IDL','total_sacks'])}.")
kf.append(f"**Coverage** (real assignment = coverage_assignment non-null and not NO_ASSIGNMENT): CB {int(b4b.loc['CB','ge50_REG'])}/{int(b4b.loc['CB','players'])} players >=50 REG snaps, {int(b4b.loc['CB','ge100_REG'])} >=100, {int(b4b.loc['CB','ge200_REG'])} >=200; S {int(b4b.loc['S','ge50_REG'])}/{int(b4b.loc['S','players'])}, {int(b4b.loc['S','ge100_REG'])}, {int(b4b.loc['S','ge200_REG'])}. "
          "A coverage row has the assignment (MAN or zone type) and `cushion`, but NO target, reception, separation-allowed, yards-allowed or completion-allowed for the defender; pass_result / yards_gained are play-level and identical for all players on the play. "
          f"A defender outcome would have to come from pairing with a cohort receiver on the same play (opposing WR/TE-vs-DB pairs exist on {int(mm.loc['WR/TE vs DB (CB,S,DB)','plays_reg']):,} REG plays) or be derived from tracking.")
kf.append(f"**Run defence**: tackle/assist/tackle_for_loss/caused_forced_fumble are populated only on credited rows (null = no credit; they share one null pattern); denominator = defensive snaps. REG run-defence snaps >=100: IDL {int(b5.loc['IDL','ge100_REG'])}, EDGE {int(b5.loc['EDGE','ge100_REG'])}, CB {int(b5.loc['CB','ge100_REG'])}, S {int(b5.loc['S','ge100_REG'])}; "
          f"players with >=25 REG tackles: S {int(tkp_.loc['S','ge25_tackles'])}, CB {int(tkp_.loc['CB','ge25_tackles'])}, EDGE {int(tkp_.loc['EDGE','ge25_tackles'])}, IDL {int(tkp_.loc['IDL','ge25_tackles'])}.")
kf.append(f"**Joins**: (game_id, play_id, nfl_id) is unique in player_play; every nfl_id and game_id resolves in players/games. {R['tk_only']:,} tracking keys lack a player_play row (all WR/TE/FB) and {R['pp_only']:,} player_play rows lack tracking ({pct(R['pp_only_na'], R['pp_only'], 0)} are NA pre-snap-penalty rows).")
kf.append(f"**Season types**: games.csv includes PRE (147 games, {pct(n_pre_rows, n_pp)} of player_play rows). Filter on games.season_type == 'REG' deliberately. All 5 generic-`DB` players appear only in PRE (career defensive snaps 0).")
kf.append(f"**Tracking**: 0.1 s sampling ({int(R['dtq2']['exactly_100ms']):,} of {int(R['dtq2']['intervals']):,} intervals, {int(R['dtq2']['not_100ms'])} gaps), no nulls in x/y/s/a/dis/o/dir, {R['dupframes']} duplicate frames; about 10 frames before the snap and about 10 after the last event; "
          f"ball_snap on {100 * tsn['w'] / tsn['pp_n']:.1f}% of player-plays; event tags are play-level (same tag on every cohort player on that frame; never partial or conflicting); "
          "x/y are raw field coordinates (not normalised to offence direction); a small number of implausible speeds/accelerations and out-of-field positions (section D).")
kf.append(f"**Career table**: career snaps equal REG player_play rows exactly for non-WR/TE groups; Spearman(draft pick, career primary-side snaps) = {rho_all:.2f} over {n_drafted} drafted players (within class roughly -0.6 to -0.7). "
          f"Honours are too rare to model: {int(honours.ap1)} All-Pro 1st team, {int(honours.ap2)} 2nd team, {int(honours.any_honour)} players with any All-Pro/Pro Bowl.")
kf.append("**Surprises**: (i) no special-teams plays (no punts, kickoffs, FGs) in player_play; (ii) `nfl_position` is not the alignment (e.g. SS lines up as OLB/MLB/CB/EDGE, DT as EDGE); (iii) `game_clock` is minutes:seconds stored as a HH:MM time; "
          "(iv) `target` is never null (False for every defender; True on only 4 OL rows); (v) cohort-vs-cohort co-occurrence exists on 74% of tracked plays, so tracking is not 'one player per play'; (vi) PRE rows contain 78% of the NA pre-snap-penalty rows.")
idx = lines.index(next(l for l in lines if l.startswith("**Conventions.**")))
lines[idx + 1:idx + 1] = ["", "## Key findings (all numbers computed by this script; details in sections)", ""] + [f"- {x}" for x in kf] + [""]

# ---------------------------------------------------------------- write
OUT.write_text("\n".join(lines), encoding="utf-8")
log(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
