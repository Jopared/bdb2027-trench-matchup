"""C3 feasibility: engaged-rep identification (G1) and rep-level power check (G2).

Run from repo root: .venv\\Scripts\\python.exe scripts\\feasibility\\c3_rep_matchup.py
Prints all results; the log is also written to LOGFILE.
"""
from __future__ import annotations
import os
import numpy as np, polars as pl, pandas as pd
import statsmodels.api as sm
from bdb2027 import paths

SCRATCH = os.path.join("data", "cache")
CACHE = os.path.join(SCRATCH, "c3_frames.parquet")
LOGFILE = os.path.join(SCRATCH, "c3_log.txt")
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 50)

# ---------------------------------------------------------------- pairs
pp = pl.read_parquet(paths.parquet("player_play"))
games = pl.read_parquet(paths.parquet("games")).select("game_id", "season", "season_type")
d = (pp.filter((pl.col("pass_result") != "") & (pl.col("lined_up_position") != "NA"))
       .join(games, on="game_id"))
ol = d.filter(pl.col("pressure_allowed").is_not_null()).select(
    "game_id", "play_id", "nfl_id", "team_abbr", "lined_up_position", "pressure_allowed",
    "peak_pressure_probability_allowed", "dropback_duration", "season", "season_type",
    "play_nullified_by_penalty")
ru = d.filter(pl.col("blitzing") == True).select(  # noqa: E712
    "game_id", "play_id", pl.col("nfl_id").alias("nfl_id_r"), pl.col("team_abbr").alias("team_r"),
    pl.col("lined_up_position").alias("pos_r"), pl.col("time_to_pressure").alias("ttp_r"))
pairs = (ol.join(ru, on=["game_id", "play_id"]).filter(pl.col("team_abbr") != pl.col("team_r"))
           .with_columns(pl.col("ttp_r").is_not_null().alias("rusher_pressure")))
log(f"all-season-type pairs: {pairs.height}")
log(str(pairs.group_by("season_type").agg(
    pl.len().alias("pairs"), pl.struct("game_id", "play_id").n_unique().alias("plays"),
    pl.col("nfl_id").n_unique().alias("ol"), pl.col("nfl_id_r").n_unique().alias("rushers"),
    pl.col("pressure_allowed").sum().alias("ol_pressure_pairs"),
    pl.col("rusher_pressure").sum().alias("rusher_pressure_pairs"))))
pairs = pairs.filter(pl.col("season_type").is_in(["REG", "POST"]))
play_keys = pairs.select("game_id", "play_id").unique()
player_keys = pl.concat([pairs.select("game_id", "play_id", "nfl_id"),
                         pairs.select("game_id", "play_id", pl.col("nfl_id_r").alias("nfl_id"))]).unique()

# ---------------------------------------------------------------- frames
if os.path.exists(CACHE):
    fr = pl.read_parquet(CACHE)
else:
    parts = []
    for y in (2023, 2024, 2025):
        lf = pl.scan_parquet(paths.parquet(f"game_tracking_{y}")).select(
            "game_id", "play_id", "nfl_id", "time", "x", "y", "event")
        parts.append(lf.join(player_keys.lazy(), on=["game_id", "play_id", "nfl_id"], how="semi").collect())
    fr = pl.concat(parts)
    fr.write_parquet(CACHE)
log(f"frames loaded: {fr.height}, plays with frames: {fr.select('game_id', 'play_id').unique().height} of {play_keys.height}")
log("event tags among loaded frames: " + str(
    fr["event"].drop_nulls().value_counts().sort("count", descending=True).head(25).to_dicts()))
dts = (fr.sort("game_id", "play_id", "nfl_id", "time")
         .with_columns(pl.col("time").diff().over("game_id", "play_id", "nfl_id").dt.total_milliseconds().alias("dt"))
         .filter(pl.col("dt") > 0))
log("frame dt (ms) value counts: " + str(dts["dt"].value_counts().sort("count", descending=True).head(5).to_dicts()))


# ---------------------------------------------------------------- play event times
def first_event(name):
    return fr.filter(pl.col("event") == name).group_by("game_id", "play_id").agg(pl.col("time").min().alias(name))


ev = play_keys
for e_ in ("ball_snap", "pass_forward", "qb_sack"):
    ev = ev.join(first_event(e_), on=["game_id", "play_id"], how="left")
log(f"plays lacking ball_snap in loaded frames: {ev['ball_snap'].is_null().sum()}; with pass_forward: "
    f"{ev['pass_forward'].is_not_null().sum()}; with qb_sack: {ev['qb_sack'].is_not_null().sum()}")
ev = ev.filter(pl.col("ball_snap").is_not_null()).with_columns(
    pl.min_horizontal(pl.col("ball_snap") + pl.duration(milliseconds=3000),
                      pl.col("pass_forward"), pl.col("qb_sack")).alias("t_end"),
    (pl.col("ball_snap") + pl.duration(milliseconds=200)).alias("t_start"))

w = (fr.join(ev.select("game_id", "play_id", "t_start", "t_end"), on=["game_id", "play_id"])
       .filter((pl.col("time") >= pl.col("t_start")) & (pl.col("time") <= pl.col("t_end")))
       .select("game_id", "play_id", "nfl_id", "time", "x", "y"))
a = w.rename({"x": "xo", "y": "yo"})
b = w.rename({"nfl_id": "nfl_id_r", "x": "xr", "y": "yr"})
pj = (pairs.select("game_id", "play_id", "nfl_id", "nfl_id_r")
      .join(a, on=["game_id", "play_id", "nfl_id"])
      .join(b, on=["game_id", "play_id", "nfl_id_r", "time"])
      .with_columns(((pl.col("xo") - pl.col("xr")) ** 2 + (pl.col("yo") - pl.col("yr")) ** 2).sqrt().alias("d")))
nwin = ev.with_columns(((pl.col("t_end") - pl.col("t_start")).dt.total_milliseconds() / 100 + 1).round(0).alias("n_win"))
log("window length in frames across plays: " + str(nwin["n_win"].describe().to_dicts()))
log(f"share of plays with window shorter than 4 frames (cannot be engaged under primary): {(nwin['n_win'] < 4).mean():.4f}")

base = pairs.join(ev.select("game_id", "play_id"), on=["game_id", "play_id"])
log(f"pairs with a snap-tagged play: {base.height}; pairs with >=1 overlapping frame in window: "
    f"{pj.select('game_id', 'play_id', 'nfl_id', 'nfl_id_r').unique().height}")


def engaged_flags(thr, k):
    cnt = (pj.group_by("game_id", "play_id", "nfl_id", "nfl_id_r")
             .agg((pl.col("d") <= thr).sum().alias("n_close"), pl.len().alias("n_common")))
    return cnt.with_columns((pl.col("n_close") >= k).alias("engaged"))


# ---------------------------------------------------------------- G1
variants = [(1.5, 4), (1.25, 4), (2.0, 4), (1.5, 3), (1.5, 6)]
rows, det = [], {}
for thr, k in variants:
    cnt = engaged_flags(thr, k)
    m = (base.join(cnt.select("game_id", "play_id", "nfl_id", "nfl_id_r", "n_close", "engaged"),
                   on=["game_id", "play_id", "nfl_id", "nfl_id_r"], how="left")
             .with_columns(pl.col("engaged").fill_null(False)))
    det[(thr, k)] = m
    e = m.filter(pl.col("engaged"))
    ne = m.filter(~pl.col("engaged"))
    olc = e.group_by("nfl_id").len()
    rc = e.group_by("nfl_id_r").len()
    dbl = e.group_by("game_id", "play_id", "nfl_id_r").agg(pl.col("nfl_id").n_unique().alias("n_ol"))
    eng_plays = e.select("game_id", "play_id").unique().height
    dbl_play = dbl.filter(pl.col("n_ol") > 1).select("game_id", "play_id").unique().height
    # share of engaged (play, rusher) units that are double teamed
    units = dbl.height
    dbl_units = dbl.filter(pl.col("n_ol") > 1).height

    def coh(x):
        s = x.filter(pl.col("pressure_allowed"))
        return s["rusher_pressure"].mean(), s.height

    ce, ne_n = coh(e)
    cn, nn_n = coh(ne)
    rows.append(dict(variant=f"{thr} yd / {k} fr", eng_reps_REG_POST=e.height,
                     eng_REG=e.filter(pl.col("season_type") == "REG").height,
                     distinct_OL=e["nfl_id"].n_unique(), distinct_rushers=e["nfl_id_r"].n_unique(),
                     OL_ge10=int((olc["len"] >= 10).sum()), rushers_ge10=int((rc["len"] >= 10).sum()),
                     plays_engaged=eng_plays, plays_with_double=dbl_play,
                     double_share_of_plays=dbl_play / eng_plays,
                     rusher_units=units, double_units=dbl_units, double_share_of_rusher_units=dbl_units / units,
                     coh_engaged=ce, n_eng_OLpress=ne_n, coh_nonengaged=cn, n_non_OLpress=nn_n,
                     ratio=ce / cn if cn else float("nan"),
                     OLpress_rate_eng=e["pressure_allowed"].mean(), OLpress_rate_non=ne["pressure_allowed"].mean(),
                     rushpress_rate_eng=e["rusher_pressure"].mean(), rushpress_rate_non=ne["rusher_pressure"].mean()))
g1 = pd.DataFrame(rows)
log(g1.set_index("variant").T.to_string())

m = det[(1.5, 4)]
e = m.filter(pl.col("engaged"))
ne = m.filter(~pl.col("engaged"))


def coh_tab(x):
    s = x.filter(pl.col("pressure_allowed"))
    return round(s["rusher_pressure"].mean(), 4), s.height


for name, flt in [("REG only", pl.col("season_type") == "REG"),
                  ("penalty-nullified plays removed", pl.col("play_nullified_by_penalty") != "Y")]:
    mm = m.filter(flt)
    log(f"coherence [{name}]: engaged {coh_tab(mm.filter(pl.col('engaged')))}, non-engaged {coh_tab(mm.filter(~pl.col('engaged')))}")
log(f"P(rusher pressure | engaged & OL NOT pressured) = {e.filter(~pl.col('pressure_allowed'))['rusher_pressure'].mean():.4f}; "
    f"non-engaged = {ne.filter(~pl.col('pressure_allowed'))['rusher_pressure'].mean():.4f}")
log(f"P(OL pressure | engaged & rusher pressured) = {e.filter(pl.col('rusher_pressure'))['pressure_allowed'].mean():.4f}; "
    f"non-engaged = {ne.filter(pl.col('rusher_pressure'))['pressure_allowed'].mean():.4f}")

rng = np.random.default_rng(2027)


def boot(x, B=1000):
    s = x.filter(pl.col("pressure_allowed")).select("game_id", "play_id", "rusher_pressure").to_pandas()
    s["pk"] = s.game_id.astype(str) + "_" + s.play_id.astype(str)
    g = s.groupby("pk").rusher_pressure.agg(["sum", "count"])
    sm_, ct = g["sum"].values, g["count"].values
    out = []
    for _ in range(B):
        i = rng.integers(0, len(g), len(g))
        out.append(sm_[i].sum() / ct[i].sum())
    return np.round(np.percentile(out, [2.5, 97.5]), 4)


log(f"coherence 95% CI (play-cluster bootstrap, 1000, seed 2027): engaged {boot(e)}, non-engaged {boot(ne)}")

log("engaged by season_type x season: " + str(e.group_by("season_type", "season").len().sort("season_type", "season").to_dicts()))
log("all pairs by season: " + str(m.group_by("season").agg(pl.len(), pl.col("engaged").mean()).sort("season").to_dicts()))
log("engaged by OL lined_up_position: " + str(e.group_by("lined_up_position").len().sort("len", descending=True).to_dicts()))
log("engaged by rusher lined_up_position: " + str(e.group_by("pos_r").len().sort("len", descending=True).to_dicts()))
log("engagement rate by OL position: " + str(m.group_by("lined_up_position").agg(pl.len(), pl.col("engaged").mean()).sort("len", descending=True).to_dicts()))
log("engagement rate by rusher position: " + str(m.group_by("pos_r").agg(pl.len(), pl.col("engaged").mean()).sort("len", descending=True).to_dicts()))
olc = e.group_by("nfl_id").len()["len"]
rc = e.group_by("nfl_id_r").len()["len"]
log(f"engaged reps per OL quantiles(0,25,50,75,100): {np.percentile(olc, [0, 25, 50, 75, 100])}; per rusher: {np.percentile(rc, [0, 25, 50, 75, 100])}")
log(f"share of engaged reps held by top-10 OL: {olc.sort(descending=True)[:10].sum() / olc.sum():.3f}; top-10 rushers: {rc.sort(descending=True)[:10].sum() / rc.sum():.3f}")
eo = e.filter(pl.col("lined_up_position").is_in(["T", "G", "C"]))
log(f"engaged reps T/G/C blockers only: {eo.height}, distinct OL {eo['nfl_id'].n_unique()}, distinct rushers {eo['nfl_id_r'].n_unique()}, "
    f"OL>=10: {(eo.group_by('nfl_id').len()['len'] >= 10).sum()}, rushers>=10: {(eo.group_by('nfl_id_r').len()['len'] >= 10).sum()}")
er = e.filter(pl.col("lined_up_position").is_in(["T", "G", "C"]) & pl.col("pos_r").is_in(["EDGE", "INTERIOR_LINE"]))
log(f"engaged reps T/G/C blocker AND EDGE/INTERIOR_LINE rusher: {er.height}, OL>=10: {(er.group_by('nfl_id').len()['len'] >= 10).sum()}, rushers>=10: {(er.group_by('nfl_id_r').len()['len'] >= 10).sum()}")
log(f"distinct OL x rusher dyads among engaged: {e.select('nfl_id', 'nfl_id_r').unique().height}; dyads with >=2 reps: {(e.group_by('nfl_id', 'nfl_id_r').len()['len'] >= 2).sum()}")
log(f"OL pressure_allowed rate: all pairs {m['pressure_allowed'].mean():.4f}, engaged {e['pressure_allowed'].mean():.4f}, non-engaged {ne['pressure_allowed'].mean():.4f}")
pe = e.group_by("game_id", "play_id", "nfl_id").len()
log(f"engaged reps per (play, OL): mean {pe['len'].mean():.3f}; (play, OL) with >1 engaged cohort rusher: {(pe['len'] > 1).sum()} of {pe.height}")

# ---------------------------------------------------------------- G2
cr = pl.read_parquet(paths.parquet("combine_results")).select("nfl_id", "combine_weight")
attr = (pl.read_parquet(paths.parquet("players")).select("nfl_id", "draft_overall_pick")
          .join(cr, on="nfl_id", how="left")
          .with_columns(pl.col("draft_overall_pick").fill_null(262)))
log(f"players: {attr.height}; weight null: {attr['combine_weight'].null_count()}; max pick: {attr['draft_overall_pick'].max()}; "
    f"undrafted (pick==262 after fill): {(attr['draft_overall_pick'] == 262).sum()}")


def prep(sub, ol_only=False):
    x = sub
    if ol_only:
        x = x.filter(pl.col("lined_up_position").is_in(["T", "G", "C"]))
    x = (x.join(attr.select("nfl_id", pl.col("draft_overall_pick").alias("pick_o"), pl.col("combine_weight").alias("w_o")), on="nfl_id")
           .join(attr.select(pl.col("nfl_id").alias("nfl_id_r"), pl.col("draft_overall_pick").alias("pick_r"),
                             pl.col("combine_weight").alias("w_r")), on="nfl_id_r"))
    n0 = x.height
    x = x.drop_nulls(["pick_o", "pick_r", "w_o", "w_r", "dropback_duration", "pressure_allowed"])
    df = x.to_pandas()
    df["dpick"] = df.pick_r - df.pick_o
    df["dwt"] = df.w_r - df.w_o
    df["z_dpick"] = (df.dpick - df.dpick.mean()) / df.dpick.std()
    df["z_dwt"] = (df.dwt - df.dwt.mean()) / df.dwt.std()
    df["y"] = df.pressure_allowed.astype(int)
    return df, n0


def g2(sub, label, ol_only=False):
    df, n0 = prep(sub, ol_only)
    X = sm.add_constant(df[["z_dpick", "z_dwt", "dropback_duration"]].astype(float))
    res = sm.Logit(df.y, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(df.nfl_id)[0]})
    log(f"\nG2 [{label}] n={len(df)} (dropped {n0 - len(df)} missing), OL clusters={df.nfl_id.nunique()}, "
        f"rushers={df.nfl_id_r.nunique()}, OL pressure rate={df.y.mean():.4f}")
    log(f"  SD of pick diff = {df.dpick.std():.1f} picks, of weight diff = {df.dwt.std():.1f} lb")
    t = pd.DataFrame({"coef": res.params, "se": res.bse, "z": res.tvalues, "p": res.pvalues, "OR": np.exp(res.params)})
    log(t.round(4).to_string())
    return res, df


G2 = {}
G2["primary"] = g2(det[(1.5, 4)].filter(pl.col("engaged")), "PRIMARY: engaged reps (1.5 yd / 4 fr), all blockers")
g2(det[(1.5, 4)].filter(pl.col("engaged")), "engaged, T/G/C blockers only", ol_only=True)
g2(det[(1.5, 4)].filter(pl.col("engaged") & (pl.col("season_type") == "REG")), "engaged, REG only")
g2(det[(1.5, 4)], "reference: ALL co-occurring pairs (no engagement filter)")
g2(det[(1.5, 4)].filter(~pl.col("engaged")), "placebo: NON-engaged pairs")
for thr, k in [(1.25, 4), (2.0, 4), (1.5, 3), (1.5, 6)]:
    g2(det[(thr, k)].filter(pl.col("engaged")), f"sensitivity engaged {thr} yd / {k} frames")

res, df = G2["primary"]
X = sm.add_constant(df[["z_dpick", "z_dwt", "dropback_duration"]].astype(float))
r2 = sm.Logit(df.y, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(df.nfl_id_r)[0]})
log(f"\nprimary G2 with SEs clustered by RUSHER: z_dpick {r2.params['z_dpick']:.4f} se {r2.bse['z_dpick']:.4f} p {r2.pvalues['z_dpick']:.4f}; "
    f"z_dwt {r2.params['z_dwt']:.4f} se {r2.bse['z_dwt']:.4f} p {r2.pvalues['z_dwt']:.4f}")
# two-way clustering by OL and rusher (Cameron-Gelbach-Miller): V = V_ol + V_r - V_intersection
def cluster_cov(res_, df_, groups):
    return sm.Logit(df_.y, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]}).cov_params()
V = (cluster_cov(res, df, df.nfl_id) + cluster_cov(res, df, df.nfl_id_r)
     - cluster_cov(res, df, df.nfl_id.astype(str) + "_" + df.nfl_id_r.astype(str)))
se2 = np.sqrt(np.diag(V))
from scipy import stats
for i, nme in enumerate(res.params.index):
    z = res.params.iloc[i] / se2[i]
    log(f"two-way cluster (OL, rusher) {nme}: coef {res.params.iloc[i]:.4f} se {se2[i]:.4f} p {2 * stats.norm.sf(abs(z)):.4f}")
df["yr"] = df.rusher_pressure.astype(int)
r3 = sm.Logit(df.yr, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(df.nfl_id_r)[0]})
log(f"secondary outcome rusher pressure (cluster by rusher): z_dpick {r3.params['z_dpick']:.4f} se {r3.bse['z_dpick']:.4f} p {r3.pvalues['z_dpick']:.4f}; "
    f"z_dwt {r3.params['z_dwt']:.4f} se {r3.bse['z_dwt']:.4f} p {r3.pvalues['z_dwt']:.4f}")
df["z_pr"] = (df.pick_r - df.pick_r.mean()) / df.pick_r.std()
df["z_po"] = (df.pick_o - df.pick_o.mean()) / df.pick_o.std()
r4 = sm.Logit(df.y, sm.add_constant(df[["z_pr", "z_po", "z_dwt", "dropback_duration"]].astype(float))).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(df.nfl_id)[0]})
log("decomposed (rusher pick, OL pick separately), cluster by OL:\n" + pd.DataFrame({"coef": r4.params, "se": r4.bse, "p": r4.pvalues}).round(4).to_string())
log(f"corr(dpick, dwt) in engaged sample: {df[['dpick', 'dwt']].corr().iloc[0, 1]:.3f}; "
    f"dyads {df[['nfl_id', 'nfl_id_r']].drop_duplicates().shape[0]}")
# dropback_duration among engaged vs all, and a pick-only model w/o duration for transparency
r5 = sm.Logit(df.y, sm.add_constant(df[["z_dpick", "z_dwt"]].astype(float))).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(df.nfl_id)[0]})
log(f"no dropback_duration control: z_dpick {r5.params['z_dpick']:.4f} se {r5.bse['z_dpick']:.4f} p {r5.pvalues['z_dpick']:.4f}")

with open(LOGFILE, "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))

# ---------------------------------------------------------------- robustness: position controls and OL-position split
res, df = G2["primary"]
df["rush_interior"] = (df.pos_r == "INTERIOR_LINE").astype(float)
df["rush_other"] = (~df.pos_r.isin(["INTERIOR_LINE", "EDGE"])).astype(float)
df["ol_T"] = (df.lined_up_position == "T").astype(float)
df["ol_C"] = (df.lined_up_position == "C").astype(float)
df["ol_skill"] = (~df.lined_up_position.isin(["T", "G", "C"])).astype(float)
cols = ["z_dpick", "z_dwt", "dropback_duration", "rush_interior", "rush_other", "ol_T", "ol_C", "ol_skill"]
r6 = sm.Logit(df.y, sm.add_constant(df[cols].astype(float))).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(df.nfl_id)[0]})
log("primary + rusher-position and blocker-position dummies, cluster by OL:\n"
    + pd.DataFrame({"coef": r6.params, "se": r6.bse, "p": r6.pvalues}).round(4).to_string())
for pos in ("T", "G", "C"):
    s = df[df.lined_up_position == pos]
    Xs = sm.add_constant(s[["z_dpick", "z_dwt", "dropback_duration"]].astype(float))
    rr = sm.Logit(s.y, Xs).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(s.nfl_id)[0]})
    log(f"  OL position {pos}: n={len(s)} z_dpick {rr.params['z_dpick']:.4f} se {rr.bse['z_dpick']:.4f} p {rr.pvalues['z_dpick']:.4f}; z_dwt {rr.params['z_dwt']:.4f} p {rr.pvalues['z_dwt']:.4f}")
log(f"engaged reps per season share: {df.groupby('season').size().to_dict()}")
log(f"OL with >=10 engaged reps by season (any): " + str({s_: int((df[df.season == s_].groupby('nfl_id').size() >= 10).sum()) for s_ in sorted(df.season.unique())}))
with open(LOGFILE, "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
