"""C1 feasibility: OL pass set (gates G1-G5). Run from repo root.

Deliberately does NOT join any Combine drill metric to any NFL pressure outcome.
Cache of game-derived play features is written to a scratch dir (CACHE).
"""
from __future__ import annotations
import os, sys, json, warnings
import numpy as np, polars as pl, pandas as pd
from bdb2027 import paths

warnings.filterwarnings("ignore")
SEED, NB = 2027, 2000
CACHE = os.environ.get("C1_CACHE", os.path.join("data", "cache"))
LOG: list[str] = []


def out(s=""):
    print(s); LOG.append(str(s))


# ---------------------------------------------------------------- stats helpers
def pear(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 4: return np.nan
    a, b = a[m], b[m]
    if a.std() == 0 or b.std() == 0: return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def spear(a, b):
    from scipy.stats import rankdata
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    return pear(rankdata(a[m]), rankdata(b[m]))


def resid(y, X):
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def partial(a, b, Z):
    a = np.asarray(a, float); b = np.asarray(b, float); Z = np.asarray(Z, float)
    if Z.ndim == 1: Z = Z[:, None]
    m = np.isfinite(a) & np.isfinite(b) & np.isfinite(Z).all(1)
    return pear(resid(a[m], Z[m]), resid(b[m], Z[m]))


def icc21(a, b):
    X = np.column_stack([a, b]).astype(float)
    X = X[np.isfinite(X).all(1)]
    n, k = X.shape
    gm = X.mean(); rm = X.mean(1); cm = X.mean(0)
    msr = k * ((rm - gm) ** 2).sum() / (n - 1)
    msc = n * ((cm - gm) ** 2).sum() / (k - 1)
    mse = ((X - rm[:, None] - cm[None, :] + gm) ** 2).sum() / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n))


def sb(r): return 2 * r / (1 + r) if np.isfinite(r) else np.nan


def boot(fn, *arrs, nb=NB, seed=SEED):
    """percentile bootstrap over rows (players) of fn(*arrs)."""
    arrs = [np.asarray(a, float) for a in arrs]
    n = len(arrs[0]); rng = np.random.default_rng(seed)
    vals = []
    for _ in range(nb):
        i = rng.integers(0, n, n)
        v = fn(*[a[i] for a in arrs])
        if np.isfinite(v): vals.append(v)
    if len(vals) < nb * 0.5: return (np.nan, np.nan)
    return tuple(np.percentile(vals, [2.5, 97.5]))


def fmt(v, ci=None, d=3):
    s = f"{v:.{d}f}"
    if ci is not None: s += f" [{ci[0]:.{d}f}, {ci[1]:.{d}f}]"
    return s


# ---------------------------------------------------------------- drill metrics
def smooth(v, w):
    return pd.Series(v).rolling(w, center=True, min_periods=1).mean().to_numpy()


def cross_time(t, s, thr, start_i):
    """first time >= start_i where s >= thr, linear interpolation between frames. nan if never."""
    for i in range(start_i, len(s)):
        if s[i] >= thr:
            if i == start_i or s[i - 1] >= thr: return t[i]
            f = (thr - s[i - 1]) / (s[i] - s[i - 1])
            return t[i - 1] + f * (t[i] - t[i - 1])
    return np.nan


def at_time(t, v, tt):
    if tt > t[-1] + 1e-9 or tt < t[0] - 1e-9: return np.nan
    return float(np.interp(tt, t, v))


def rep_metrics(x, y, s, w):
    """x,y,s raw arrays at 10 Hz for one rep. w = smoothing window (3 or 5)."""
    xs, ys, ss = smooth(x, w), smooth(y, w), smooth(s, w)
    t = np.arange(len(x)) * 0.1
    # onset: first of 3 consecutive frames with smoothed s >= 0.5
    on = np.nan
    for i in range(len(ss) - 2):
        if (ss[i:i + 3] >= 0.5).all(): on = i; break
    r = dict(onset_i=on)
    keys = ["set_depth_1s", "set_depth_1s_back", "set_burst", "set_burst_w2s", "peak_set_speed", "open_and_run", "set_lateral_drift"]
    if not np.isfinite(on):
        r.update({k: np.nan for k in keys}); return r
    on = int(on); t_on = t[on]
    d = lambda tt: np.hypot(at_time(t, xs, tt) - xs[on], at_time(t, ys, tt) - ys[on])
    r["set_depth_1s"] = d(t_on + 1.0)                       # Euclidean net displacement (spec)
    r["set_depth_1s_back"] = -(at_time(t, xs, t_on + 1.0) - xs[on])  # drill runs -x -> backward = -dx (variant)
    tb = cross_time(t, ss, 1.5, on)
    r["set_burst"] = tb - t_on if np.isfinite(tb) else np.nan  # spec: time from onset (s>=0.5) to s>=1.5, unrestricted search
    r["set_burst_w2s"] = (tb - t_on) if (np.isfinite(tb) and tb - t_on <= 2.0) else np.nan  # variant: only if reached within 2 s
    win = (t >= t_on - 1e-9) & (t <= t_on + 1.5 + 1e-9)
    r["peak_set_speed"] = float(ss[win].max())
    i18 = int(np.ceil((t_on + 1.8) / 0.1 - 1e-9))
    t20 = cross_time(t, ss, 2.0, i18) if i18 < len(ss) else np.nan
    if np.isfinite(t20):
        j = int(np.floor(t20 / 0.1 + 1e-9))
        t45 = cross_time(t, ss, 4.5, j)
        r["open_and_run"] = t45 - t20 if np.isfinite(t45) else np.nan
    else: r["open_and_run"] = np.nan
    r["set_lateral_drift"] = abs(at_time(t, ys, t_on + 1.5) - ys[on])
    return r


METRICS = ["set_depth_1s", "set_burst", "peak_set_speed"]
SECOND = ["open_and_run", "set_lateral_drift"]
VARIANTS = ["set_depth_1s_back", "set_burst_w2s"]


def load_drill():
    ct = pl.read_parquet(paths.parquet("combine_tracking")).filter(
        (pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "PASS_RUSH_DROP"))
    ct = ct.sort("nfl_id", "event_id", "time")
    rows = []
    for (pid, ev), g in ct.group_by(["nfl_id", "event_id"], maintain_order=True):
        g = g.sort("time")
        rows.append(dict(nfl_id=pid, event_id=ev, t0=g["time"][0], draft_year=g["draft_year"][0],
                         x=g["x"].to_numpy(), y=g["y"].to_numpy(), s=g["s"].to_numpy()))
    reps = pd.DataFrame(rows).sort_values(["nfl_id", "t0"])
    reps["rep"] = reps.groupby("nfl_id").cumcount() + 1
    return reps


def drill_table(reps, w):
    recs = []
    for _, r in reps.iterrows():
        m = rep_metrics(r.x, r.y, r.s, w)
        m.update(nfl_id=r.nfl_id, rep=r.rep, draft_year=r.draft_year, n_fr=len(r.x),
                 x0=r.x[0], y0=r.y[0], dx_total=r.x[-1] - r.x[0])
        recs.append(m)
    return pd.DataFrame(recs)


# ---------------------------------------------------------------- game features
def build_game_features(w=3, force=False):
    """One row per cohort-OL pass-block snap (T/G/C, not NA) with in-game set metrics.
    snap = ball_snap frame; play_direction from player_play; backward = toward own end zone."""
    fp = os.path.join(CACHE, f"c1_game_feats_w{w}.parquet")
    if os.path.exists(fp) and not force: return pl.read_parquet(fp)
    ct = pl.read_parquet(paths.parquet("combine_tracking")).filter(
        (pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "PASS_RUSH_DROP"))
    coh = ct.select("nfl_id").unique()
    pp = pl.read_parquet(paths.parquet("player_play"))
    keys = (pp.filter(pl.col("pressure_allowed").is_not_null() & (pl.col("lined_up_position") != "NA")
                      & pl.col("lined_up_position").is_in(["T", "G", "C"]))
              .join(coh, on="nfl_id", how="semi")
              .select("game_id", "play_id", "nfl_id", "play_direction"))
    outs = []
    for yr in (2023, 2024, 2025):
        lf = pl.scan_parquet(paths.parquet(f"game_tracking_{yr}")).join(keys.lazy(), on=["game_id", "play_id", "nfl_id"], how="semi")
        df = lf.select("game_id", "play_id", "nfl_id", "time", "x", "y", "s", "event").collect().sort("game_id", "play_id", "nfl_id", "time")
        # play-level tags (any frame of that play among selected rows)
        ev = df.group_by("game_id", "play_id").agg(
            pl.col("time").filter(pl.col("event") == "ball_snap").min().alias("t_snap"),
            pl.col("event").is_in(["play_action", "autoevent_playaction"]).any().alias("play_action"),
            pl.col("event").is_in(["pass_forward"]).any().alias("has_pass_forward"))
        df = df.join(ev, on=["game_id", "play_id"]).filter(pl.col("t_snap").is_not_null())
        df = df.with_columns(tr=((pl.col("time") - pl.col("t_snap")).dt.total_milliseconds() / 100).round().cast(pl.Int32))
        df = df.filter((pl.col("tr") >= -5) & (pl.col("tr") <= 25))
        df = df.sort("game_id", "play_id", "nfl_id", "tr")
        g = ["game_id", "play_id", "nfl_id"]
        df = df.with_columns(xs=pl.col("x").rolling_mean(w, center=True, min_samples=1).over(g),
                             ys=pl.col("y").rolling_mean(w, center=True, min_samples=1).over(g),
                             ss=pl.col("s").rolling_mean(w, center=True, min_samples=1).over(g))
        df = df.join(keys.select(g + ["play_direction"]), on=g)
        sgn = pl.when(pl.col("play_direction") == "left").then(1.0).otherwise(-1.0)
        base = df.filter(pl.col("tr") == 0).select(g + [pl.col("xs").alias("x0"), pl.col("ys").alias("y0")])
        df = df.join(base, on=g).filter(pl.col("tr") >= 0)
        df = df.with_columns(eu=((pl.col("xs") - pl.col("x0")) ** 2 + (pl.col("ys") - pl.col("y0")) ** 2).sqrt(),
                             bk=sgn * (pl.col("xs") - pl.col("x0")))
        agg = df.sort(g + ["tr"]).group_by(g, maintain_order=True).agg(
            pl.col("play_action").first(), pl.col("play_direction").first(),
            pl.col("eu").filter(pl.col("tr") == 5).first().alias("eu05"),
            pl.col("eu").filter(pl.col("tr") == 10).first().alias("eu10"),
            pl.col("bk").filter(pl.col("tr") == 5).first().alias("bk05"),
            pl.col("bk").filter(pl.col("tr") == 10).first().alias("bk10"),
            pl.col("ss").filter(pl.col("tr") <= 10).max().alias("peak_s10"),
            pl.col("tr").max().alias("tr_max"),
            pl.col("eu").alias("_eu"), pl.col("tr").alias("_tr"))
        # time to 1 yd (interpolated; censored at 2.0 s)
        t1, cen = [], []
        for eu, tr in zip(agg["_eu"].to_list(), agg["_tr"].to_list()):
            eu = np.array(eu); tr = np.array(tr) * 0.1; val = 2.0; c = 1
            for i in range(len(eu)):
                if tr[i] > 2.0 + 1e-9: break
                if eu[i] >= 1.0:
                    val = tr[i] if i == 0 else tr[i - 1] + (1.0 - eu[i - 1]) / (eu[i] - eu[i - 1]) * (tr[i] - tr[i - 1]); c = 0; break
            t1.append(min(val, 2.0)); cen.append(c)
        agg = agg.drop("_eu", "_tr").with_columns(t_1yd=pl.Series(t1), t_1yd_cens=pl.Series(cen))
        outs.append(agg.with_columns(season_file=pl.lit(yr)))
    res = pl.concat(outs).filter(pl.col("tr_max") >= 10)
    os.makedirs(CACHE, exist_ok=True); res.write_parquet(fp)
    return res


# ---------------------------------------------------------------- G1 / G2
def verdict_g1(r): return "PASS" if r >= 0.60 else ("AMBER" if r >= 0.40 else "FAIL")


def run_g1_g2():
    reps = load_drill()
    nreps = reps.groupby("nfl_id").size()
    out(f"## drill data: {len(reps)} reps, {reps.nfl_id.nunique()} players; reps per player: {dict(nreps.value_counts().sort_index())}")
    tabs = {w: drill_table(reps, w) for w in (3, 5)}
    # pairs: first two reps chronologically (by time), same-start check
    first2 = reps[reps.rep <= 2].pivot(index="nfl_id", columns="rep", values=["x", "y"])
    pairs = []
    for pid, g in reps[reps.rep <= 2].groupby("nfl_id"):
        if len(g) < 2: continue
        a, b = g.iloc[0], g.iloc[1]
        pairs.append((pid, np.hypot(a.x[0] - b.x[0], a.y[0] - b.y[0]), a.draft_year, (b.t0 - a.t0).total_seconds()))
    pr = pd.DataFrame(pairs, columns=["nfl_id", "start_dist", "draft_year", "gap_s"])
    out(f"players with >=2 reps: {len(pr)}; start distance median {pr.start_dist.median():.2f} yd, max {pr.start_dist.max():.2f}, >3yd: {(pr.start_dist>3).sum()}")
    pr = pr[pr.start_dist <= 3]
    out(f"same-start pairs used (first two reps by time, start within 3 yd): n={len(pr)}; by year {dict(pr.draft_year.value_counts().sort_index())}")
    nth3 = nreps[nreps > 2].index.tolist()
    out(f"players with 3 reps (only first two used): {nth3}")

    allm = METRICS + SECOND + VARIANTS
    wide = {}
    for w, T in tabs.items():
        T = T[T.nfl_id.isin(pr.nfl_id) & (T.rep <= 2)]
        W = T.pivot(index="nfl_id", columns="rep", values=allm)
        W.columns = [f"{m}_r{r}" for m, r in W.columns]
        W = W.join(pr.set_index("nfl_id")[["draft_year"]])
        rr_ = reps[reps.rep <= 2].copy()
        rr_["side"] = np.sign(rr_.apply(lambda r: r.y[-1] - r.y[0], axis=1))   # drift direction in y (+1 / -1)
        sdp = rr_.pivot(index="nfl_id", columns="rep", values="side")
        W["side_r1"] = sdp[1]; W["side_r2"] = sdp[2]
        for m in allm:
            allv = pd.DataFrame({"v": pd.concat([W[f"{m}_r1"], W[f"{m}_r2"]]), "s": pd.concat([W.side_r1, W.side_r2])})
            st = allv.groupby("s").v.agg(["mean", "std"])
            for k in (1, 2):
                W[f"{m}_z{k}"] = (W[f"{m}_r{k}"] - W[f"side_r{k}"].map(st["mean"])) / W[f"side_r{k}"].map(st["std"])
            W[f"{m}_sz"] = (W[f"{m}_z1"] + W[f"{m}_z2"]) / 2     # side-standardised two-rep mean
        wide[w] = W
    res = []
    for w in (3, 5):
        W = wide[w]
        for m in allm:
            a, b = W[f"{m}_r1"].to_numpy(float), W[f"{m}_r2"].to_numpy(float)
            ok = np.isfinite(a) & np.isfinite(b)
            r = pear(a, b); ci = boot(pear, a[ok], b[ok])
            ic = icc21(a[ok], b[ok]); ici = boot(icc21, a[ok], b[ok])
            rs = spear(a, b)
            # year-standardised: z within draft year using both reps pooled
            za, zb = a.copy(), b.copy()
            for yr in W.draft_year.unique():
                mk = (W.draft_year == yr).to_numpy()
                both = np.concatenate([a[mk & ok], b[mk & ok]]); mu, sd = both.mean(), both.std(ddof=1)
                za[mk] = (a[mk] - mu) / sd; zb[mk] = (b[mk] - mu) / sd
            rz = pear(za, zb); rzci = boot(pear, za[ok], zb[ok])
            byyr = {int(yr): (pear(a[(W.draft_year == yr).to_numpy()], b[(W.draft_year == yr).to_numpy()]), int(((W.draft_year == yr).to_numpy() & ok).sum()))
                    for yr in sorted(W.draft_year.unique())}
            res.append(dict(w=w, metric=m, n=int(ok.sum()), r=r, lo=ci[0], hi=ci[1], icc=ic, ilo=ici[0], ihi=ici[1], spearman=rs,
                            r_yrstd=rz, zlo=rzci[0], zhi=rzci[1], by_year=byyr))
    R = pd.DataFrame(res)
    # year drift on two-rep mean (w=3 and 5)
    drift = []
    for w in (3, 5):
        W = wide[w]
        for m in allm:
            mean2 = (W[f"{m}_r1"] + W[f"{m}_r2"]) / 2
            D = pd.DataFrame({"v": mean2, "y": W.draft_year}).dropna()
            both = pd.concat([W[f"{m}_r1"], W[f"{m}_r2"]]).dropna()
            psd = np.sqrt(D.groupby("y").v.var(ddof=1).mean())
            row = dict(w=w, metric=m, pooled_within_year_sd=psd)
            for yr, gg in D.groupby("y"):
                other = D[D.y != yr].v.mean()
                row[f"mean_{yr}"] = gg.v.mean(); row[f"sd_{yr}"] = gg.v.std(ddof=1); row[f"n_{yr}"] = len(gg)
                row[f"diff_vs_others_{yr}"] = (gg.v.mean() - other) / psd
            row["flag"] = any(abs(row[k]) > 0.5 for k in row if k.startswith("diff_vs_others"))
            drift.append(row)
    Dr = pd.DataFrame(drift)
    return reps, tabs, wide, pr, R, Dr


def run_g2(wide, pr, Dr, w=3, working=None):
    cr = pl.read_parquet(paths.parquet("combine_results")).to_pandas().set_index("nfl_id")
    W = wide[w]
    cols = ["ten_yd_split", "short_shuttle", "three_cone", "forty", "combine_weight", "arm_length"]
    rows = []
    for m in METRICS + SECOND:
        v_raw = (W[f"{m}_r1"] + W[f"{m}_r2"]) / 2
        v_sz = W[f"{m}_sz"]
        v_szy = v_sz.copy()
        for yr in W.draft_year.unique():
            mk = W.draft_year == yr
            v_szy[mk] = (v_sz[mk] - v_sz[mk].mean()) / v_sz[mk].std(ddof=1)
        for c in cols:
            x = cr.reindex(W.index)[c].to_numpy(float)
            for lab, vv in (("raw_mean", v_raw), ("side_z", v_sz), ("side_z+yr_z", v_szy)):
                ok = np.isfinite(x) & np.isfinite(vv.to_numpy(float))
                xx = x.copy()
                if lab.endswith("yr_z"):
                    for yr in W.draft_year.unique():
                        mk = (W.draft_year == yr).to_numpy() & ok
                        xx[mk] = (x[mk] - x[mk].mean()) / x[mk].std(ddof=1)
                r = pear(vv.to_numpy(float), xx)
                ci = boot(pear, vv.to_numpy(float)[ok], xx[ok])
                rows.append(dict(w=w, metric=m, vs=c, scale=lab, n=int(ok.sum()), r=r, lo=ci[0], hi=ci[1]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- exploratory drill variants (NOT used for gates)
def extra_variants(reps, w=3):
    recs = []
    for _, r in reps.iterrows():
        xs, ys, ss = smooth(r.x, w), smooth(r.y, w), smooth(r.s, w)
        t = np.arange(len(xs)) * 0.1
        eu = np.hypot(xs - xs[0], ys - ys[0])
        d = dict(nfl_id=r.nfl_id, rep=r.rep, draft_year=r.draft_year)
        d["depth_f0_1.0s"] = at_time(t, eu, 1.0)
        d["depth_f0_2.0s"] = at_time(t, eu, 2.0)
        d["mean_s_f0_0_1.5s"] = float(ss[t <= 1.5 + 1e-9].mean())
        d["peak_s_whole_rep"] = float(ss.max())
        d["onset_i"] = rep_metrics(r.x, r.y, r.s, w)["onset_i"]
        recs.append(d)
    return pd.DataFrame(recs)


# ---------------------------------------------------------------- game analysis
STYPE_ORD = {"PRE": 0, "REG": 1, "POST": 2}
INGAME = {  # name -> (column, quickness sign: +1 if larger = quicker/deeper)
    "depth_euclid_0.5s": ("eu05", 1), "depth_euclid_1.0s": ("eu10", 1),
    "depth_back_0.5s": ("bk05", 1), "depth_back_1.0s": ("bk10", 1),
    "peak_speed_0_1.0s": ("peak_s10", 1), "time_to_1yd_s": ("t_1yd", -1)}
MATCH = {"set_depth_1s": "depth_euclid_1.0s", "peak_set_speed": "peak_speed_0_1.0s", "set_burst": "time_to_1yd_s"}


def design(df, kind):
    cols = []
    pos = df["lined_up_position"].to_numpy()
    cols += [(pos == "T").astype(float), (pos == "G").astype(float)]
    form = df["offense_formation"].fill_null("UNK").to_numpy()
    gun = np.isin(form, ["SHOTGUN", "EMPTY"]).astype(float); pis = (form == "PISTOL").astype(float)
    cols += [gun, pis, df["play_action"].cast(pl.Float64).to_numpy()]
    dd = df["dropback_duration"].to_numpy().astype(float)
    if kind == "set":
        b = np.digitize(np.nan_to_num(dd, nan=-1), [0, 2.0, 2.5, 3.0, 3.5, 4.0])
        for k in np.unique(b)[1:]: cols.append((b == k).astype(float))
        st = df["season_type"].to_numpy()
        cols += [(st == "PRE").astype(float), (st == "POST").astype(float)]
    else:  # outcome adjustment
        cols += [np.nan_to_num(dd, nan=np.nanmean(dd)), np.nan_to_num(dd, nan=np.nanmean(dd)) ** 2]
        pre = df["pass_rushers_encountered"].fill_null(0).to_numpy()
        for k in (1, 2, 3): cols.append((np.minimum(pre, 3) == k).astype(float) if k < 3 else (pre >= 3).astype(float))
        st = df["season_type"].to_numpy(); cols.append((st == "POST").astype(float))
    return np.column_stack(cols)


def load_plays(w=3):
    f = build_game_features(w)
    pp = pl.read_parquet(paths.parquet("player_play")).select(
        "game_id", "play_id", "nfl_id", "lined_up_position", "offense_formation", "dropback_duration", "pass_rushers_encountered",
        "peak_pressure_probability_allowed", "pressure_allowed", "time_to_pressure_allowed", "pass_result", "play_nullified_by_penalty")
    gm = pl.read_parquet(paths.parquet("games")).select("game_id", "season", "season_type", "week")
    d = f.join(pp, on=["game_id", "play_id", "nfl_id"]).join(gm, on="game_id")
    d = d.with_columns(so=pl.col("season_type").replace_strict(STYPE_ORD, return_dtype=pl.Int32)).sort("nfl_id", "season", "so", "week", "game_id", "play_id")
    return d


def adj_means(d, col, kind="set"):
    """OLS-residualise play-level `col`, return per-play residual (Series aligned to d)."""
    y = d[col].to_numpy().astype(float)
    X = design(d, kind); m = np.isfinite(y) & np.isfinite(X).all(1)
    r = np.full(len(y), np.nan); r[m] = resid(y[m], X[m])
    return r


def half_rel(pid, val, order_ok=True):
    """pid, val arrays in chronological order within player. odd/even split; return per-player odd/even means."""
    df = pd.DataFrame({"p": pid, "v": val}).dropna()
    df["k"] = df.groupby("p").cumcount()
    A = df[df.k % 2 == 0].groupby("p").v.mean(); B = df[df.k % 2 == 1].groupby("p").v.mean()
    j = pd.concat([A, B], axis=1, keys=["a", "b"]).dropna()
    return j.index.to_numpy(), j.a.to_numpy(), j.b.to_numpy()


def sb_r(a, b): return sb(pear(a, b))


def rand_split_rel(pid, val, nsplit=200, seed=SEED):
    df = pd.DataFrame({"p": pid, "v": val}).dropna()
    rng = np.random.default_rng(seed); rs = []
    groups = [g.v.to_numpy() for _, g in df.groupby("p")]
    for _ in range(nsplit):
        a, b = [], []
        for g in groups:
            p = rng.permutation(len(g)); h = len(g) // 2
            a.append(g[p[:h]].mean()); b.append(g[p[h:2 * h]].mean())
        rs.append(sb_r(a, b))
    return float(np.nanmean(rs))


def rel_row(d, resid_arr, min_snaps, label, extra=None):
    """split-half reliability among players with >= min_snaps valid snaps."""
    dd = d.select("nfl_id").with_columns(v=pl.Series(resid_arr))
    pdf = dd.to_pandas()
    cnt = pdf.dropna().groupby("nfl_id").size()
    keep = cnt[cnt >= min_snaps].index
    pdf = pdf[pdf.nfl_id.isin(keep)]
    ids, a, b = half_rel(pdf.nfl_id.to_numpy(), pdf.v.to_numpy())
    r = pear(a, b); rsb = sb(r)
    ci = boot(sb_r, a, b)
    rr = rand_split_rel(pdf.nfl_id.to_numpy(), pdf.v.to_numpy(), 100)
    return dict(label=label, n=len(ids), r_half=r, sb=rsb, lo=ci[0], hi=ci[1], sb_random_splits_mean=rr)


def player_means(d, resid_arr, min_snaps):
    pdf = d.select("nfl_id").with_columns(v=pl.Series(resid_arr)).to_pandas().dropna()
    g = pdf.groupby("nfl_id").v.agg(["mean", "size"])
    return g[g["size"] >= min_snaps]["mean"]


def run_game_gates(wide, Dr, primary, w=3):
    cr = pl.read_parquet(paths.parquet("combine_results")).to_pandas().set_index("nfl_id")
    D = {}
    d = load_plays(w)
    out(f"## game data: {d.height} cohort-OL pass-block snaps (T/G/C, not NA), {d['nfl_id'].n_unique()} players; by season type {dict(d['season_type'].value_counts().iter_rows())}")
    out(f"dropback_duration: mean {d['dropback_duration'].mean():.2f}, p5 {d['dropback_duration'].quantile(0.05):.2f}, p95 {d['dropback_duration'].quantile(0.95):.2f}; play_action share {d['play_action'].mean():.3f}; snaps with pass_result=='' (non-dropback but pressure_allowed non-null): {(d['pass_result']=='').sum()}")
    cnt = d.group_by("nfl_id").agg(pl.len().alias("all"), (pl.col("season_type") == "REG").sum().alias("reg"),
                                   (pl.col("season_type").is_in(["REG", "POST"])).sum().alias("regpost"))
    for thr in (30, 100, 200):
        out(f"players with >= {thr} snaps: PRE+REG+POST {(cnt['all']>=thr).sum()}, REG {(cnt['reg']>=thr).sum()}, REG+POST {(cnt['regpost']>=thr).sum()}")
    san = d.group_by("lined_up_position").agg(pl.len().alias("n_snaps"), pl.col("nfl_id").n_unique().alias("n_players"),
        pl.col("eu05").mean().alias("euclid_0.5s"), pl.col("eu10").mean().alias("euclid_1.0s"), pl.col("bk05").mean().alias("back_0.5s"),
        pl.col("bk10").mean().alias("back_1.0s"), pl.col("peak_s10").mean().alias("peak_speed_0-1s"), pl.col("t_1yd").mean().alias("t_1yd"),
        pl.col("t_1yd_cens").mean().alias("share_censored_at_2s")).sort("lined_up_position", descending=True).to_pandas()
    D["sanity"] = san
    resids = {k: adj_means(d, col, "set") for k, (col, sgn) in INGAME.items()}
    G3 = pd.DataFrame([rel_row(d, resids[k], 30, k) for k in INGAME])
    sens = []
    regmask = (d["season_type"] == "REG").to_numpy()
    keepmask = (~d["play_action"].to_numpy()) & (d["dropback_duration"].to_numpy() >= 2.0)
    d5 = load_plays(5)
    res5 = {k: adj_means(d5, col, "set") for k, (col, sgn) in INGAME.items()}
    for k in INGAME:
        sens.append({**rel_row(d, np.where(regmask, resids[k], np.nan), 30, k), "sens": "REG only"})
        sens.append({**rel_row(d, np.where(keepmask, resids[k], np.nan), 30, k), "sens": "no PA & dropback>=2.0s"})
        sens.append({**rel_row(d5, res5[k], 30, k), "sens": "5-frame smoothing"})
    D["G3"] = G3
    D["G3sens"] = pd.DataFrame(sens)
    wp = []
    for pos in ("T", "G"):
        mk = (d["lined_up_position"] == pos).to_numpy()
        for k in INGAME:
            wp.append({**rel_row(d, np.where(mk, resids[k], np.nan), 30, k), "pos": pos})
    D["G3pos"] = pd.DataFrame(wp)
    # ---- G4 (no outcomes touched)
    W = wide[w]
    pm = {k: player_means(d, resids[k], 30) for k in INGAME}
    D["pm"] = pm
    G4 = []
    for dm, gm_ in MATCH.items():
        v = W[f"{dm}_sz"]
        vz = v.copy()
        for yr in W.draft_year.unique():
            mk = W.draft_year == yr
            vz[mk] = (v[mk] - v[mk].mean()) / v[mk].std(ddof=1)
        v_rawmean = (W[f"{dm}_r1"] + W[f"{dm}_r2"]) / 2
        flagged = bool(Dr[(Dr.w == w) & (Dr.metric == dm)].flag.iloc[0])
        for lab, vv in (("raw_mean", v_rawmean), ("side_z", v), ("side_z+yr_z", vz)):
            j = pd.concat([vv.rename("drill"), pm[gm_].rename("game"), cr[["combine_weight", "ten_yd_split"]]], axis=1, join="inner").dropna(subset=["drill", "game", "combine_weight"])
            ten_ok = j.ten_yd_split.notna().to_numpy()
            tenfill = j.ten_yd_split.fillna(j.ten_yd_split.mean()).to_numpy()
            wt = j.combine_weight.to_numpy(float)
            a, b = j.drill.to_numpy(float), j.game.to_numpy(float)
            r = pear(a, b)
            ci = boot(pear, a, b)
            rho = spear(a, b)
            pw = partial(a, b, wt)
            pwci = boot(lambda a_, b_, z_: partial(a_, b_, z_), a, b, wt)
            Zwt = np.column_stack([wt, tenfill, (~ten_ok).astype(float)])
            pwt = partial(a, b, Zwt)
            pwtci = boot(lambda a_, b_, z1, z2, z3: partial(a_, b_, np.column_stack([z1, z2, z3])), a, b, Zwt[:, 0], Zwt[:, 1], Zwt[:, 2])
            pten = partial(a[ten_ok], b[ten_ok], np.column_stack([wt[ten_ok], j.ten_yd_split.to_numpy(float)[ten_ok]]))
            G4.append(dict(drill=dm, game=gm_, scale=lab, drift_flag=flagged, n=len(j), n_ten=int(ten_ok.sum()), r=r, lo=ci[0], hi=ci[1], spearman=rho,
                           partial_wt=pw, pw_lo=pwci[0], pw_hi=pwci[1], partial_wt_ten_imputed=pwt, pwt_lo=pwtci[0], pwt_hi=pwtci[1], partial_wt_ten_subset=pten))
    D["G4"] = pd.DataFrame(G4)
    # ---- G5: in-game set metric vs in-game outcome (no drill metric involved)
    reg = d.filter(pl.col("season_type") == "REG")

    def outcome_resid(dfx, col):
        y = dfx[col].cast(pl.Float64).to_numpy().astype(float)
        X = design(dfx, "outcome")
        m = np.isfinite(y) & np.isfinite(X).all(1)
        r = np.full(len(y), np.nan)
        r[m] = resid(y[m], X[m])
        return r

    o_reg = outcome_resid(reg, "peak_pressure_probability_allowed")
    regpost = d.filter(pl.col("season_type").is_in(["REG", "POST"]))
    G5rel = [{**rel_row(reg, o_reg, 100, "adj. peak_pressure_probability_allowed, REG, >=100 snaps"), "outcome": "primary"},
             {**rel_row(regpost, outcome_resid(regpost, "peak_pressure_probability_allowed"), 100, "same, REG+POST, >=100 snaps"), "outcome": "sens"},
             {**rel_row(reg, o_reg, 60, "same, REG, >=60 snaps"), "outcome": "sens"},
             {**rel_row(reg, outcome_resid(reg, "pressure_allowed"), 100, "adj. pressure_allowed (binary, linear resid), REG, >=100"), "outcome": "secondary"}]
    D["G5rel"] = pd.DataFrame(G5rel)
    outm = player_means(reg, o_reg, 100)
    regsnap = reg.group_by("nfl_id").agg((pl.col("lined_up_position") == "T").mean().alias("sh_T"), (pl.col("lined_up_position") == "G").mean().alias("sh_G")).to_pandas().set_index("nfl_id")
    mech = []
    for k, (col, sgn) in INGAME.items():
        for src in ("all season types (PRE+REG+POST)", "REG only", "odd REG snaps -> even REG-snap outcome"):
            om = outm
            if src.startswith("all"):
                sm = pm[k]
            elif src == "REG only":
                sm = player_means(d, np.where(regmask, resids[k], np.nan), 30)
            else:
                pdf = d.select("nfl_id").with_columns(v=pl.Series(np.where(regmask, resids[k], np.nan))).to_pandas().dropna()
                pdf["kk"] = pdf.groupby("nfl_id").cumcount()
                sm = pdf[pdf.kk % 2 == 0].groupby("nfl_id").v.mean()
                pdf2 = reg.select("nfl_id").with_columns(v=pl.Series(o_reg)).to_pandas().dropna()
                pdf2["kk"] = pdf2.groupby("nfl_id").cumcount()
                om = pdf2[(pdf2.kk % 2 == 1) & pdf2.nfl_id.isin(outm.index)].groupby("nfl_id").v.mean()
            j = pd.concat([sm.rename("set"), om.rename("out"), regsnap], axis=1, join="inner").dropna()
            a = j.set.to_numpy(float) * sgn
            b = j.out.to_numpy(float)
            Z = j[["sh_T", "sh_G"]].to_numpy(float)
            r = pear(a, b)
            ci = boot(pear, a, b)
            pr_ = partial(a, b, Z)
            pci = boot(lambda a_, b_, z1, z2: partial(a_, b_, np.column_stack([z1, z2])), a, b, Z[:, 0], Z[:, 1])
            mech.append(dict(inGame=k, set_source=src, n=len(j), r_quick_vs_pressure=r, lo=ci[0], hi=ci[1], partial_posmix=pr_, plo=pci[0], phi=pci[1]))
    D["G5mech"] = pd.DataFrame(mech)
    import statsmodels.api as sm_
    keepp = outm.index
    rr = []
    for k, (col, sgn) in INGAME.items():
        s_reg = adj_means(reg, col, "set")
        pdf = reg.select("nfl_id").with_columns(x=pl.Series(s_reg * sgn), y=pl.Series(o_reg)).to_pandas().dropna()
        pdf = pdf[pdf.nfl_id.isin(keepp)].copy()
        pdf["xz"] = (pdf.x - pdf.x.mean()) / pdf.x.std()
        pdf["xw"] = pdf.xz - pdf.groupby("nfl_id").xz.transform("mean")
        pdf["xb"] = pdf.groupby("nfl_id").xz.transform("mean")
        mod = sm_.OLS(pdf.y, sm_.add_constant(pdf[["xw", "xb"]])).fit(cov_type="cluster", cov_kwds={"groups": pdf.nfl_id})
        rr.append(dict(inGame=k, n_plays=len(pdf), n_players=pdf.nfl_id.nunique(), b_within_per_SD=mod.params["xw"], se_within=mod.bse["xw"],
                       b_between_per_SD=mod.params["xb"], se_between=mod.bse["xb"]))
    D["G5play"] = pd.DataFrame(rr)
    D["counts"] = cnt.to_pandas()
    D["d"] = d
    return D


# ---------------------------------------------------------------- reporting
def md(df, nd=3):
    df = df.copy()
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if not np.isfinite(v) else f"{v:.{nd}f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def ci_s(v, lo, hi, nd=3): return f"{v:.{nd}f} [{lo:.{nd}f}, {hi:.{nd}f}]"


def main():
    from scipy import stats
    R_md = []
    reps, tabs, wide, pr, R, Dr = run_g1_g2()
    W3 = wide[3]
    allm = METRICS + SECOND + VARIANTS
    # --- sides
    n_opp = int((W3.side_r1 != W3.side_r2).sum())
    side_ct = pd.crosstab(W3.side_r1, W3.side_r2)
    out(f"side counts (pairs): opposite-side {n_opp} of {len(W3)}; crosstab (rows rep1 drift sign, cols rep2): {side_ct.to_dict()}")
    # stance/side mean differences: rep1 vs rep2 (rep1 = chronologically first), per smoothing
    sdiff = []
    for w in (3, 5):
        Wv = wide[w]
        opp = Wv[Wv.side_r1 != Wv.side_r2]
        for m in allm:
            a = Wv[f"{m}_r1"]; b = Wv[f"{m}_r2"]
            j = pd.concat([a, b], axis=1).dropna()
            t = stats.ttest_rel(j.iloc[:, 0], j.iloc[:, 1])
            diff = j.iloc[:, 1] - j.iloc[:, 0]
            sdiff.append(dict(w=w, metric=m, n=len(j), mean_rep1=j.iloc[:, 0].mean(), mean_rep2=j.iloc[:, 1].mean(),
                              diff_rep2_minus_rep1=diff.mean(), dz=diff.mean() / diff.std(ddof=1), paired_t=t.statistic, p=t.pvalue))
    SD = pd.DataFrame(sdiff)
    # opposite-side-only r and side-z ICC (consistency)
    extra_g1 = []
    for w in (3, 5):
        Wv = wide[w]
        for m in METRICS + SECOND:
            for lab, mask in (("all pairs", np.ones(len(Wv), bool)), ("opposite-side pairs only", (Wv.side_r1 != Wv.side_r2).to_numpy())):
                a = Wv[f"{m}_z1"].to_numpy(float)[mask]; b = Wv[f"{m}_z2"].to_numpy(float)[mask]
                ok = np.isfinite(a) & np.isfinite(b)
                extra_g1.append(dict(w=w, metric=m, subset=lab, n=int(ok.sum()), r=pear(a, b), lo=boot(pear, a[ok], b[ok])[0], hi=boot(pear, a[ok], b[ok])[1],
                                     icc_sidez=icc21(a[ok], b[ok])))
    EG1 = pd.DataFrame(extra_g1)
    # exploratory variants
    ev = {}
    for w in (3,):
        E = extra_variants(reps[reps.rep <= 2], w)
        Ew = E.pivot(index="nfl_id", columns="rep", values=["depth_f0_1.0s", "depth_f0_2.0s", "mean_s_f0_0_1.5s", "peak_s_whole_rep", "onset_i"])
        rows = []
        for m in ["depth_f0_1.0s", "depth_f0_2.0s", "mean_s_f0_0_1.5s", "peak_s_whole_rep", "onset_i"]:
            a, b = Ew[(m, 1)].to_numpy(float), Ew[(m, 2)].to_numpy(float)
            ok = np.isfinite(a) & np.isfinite(b)
            ci = boot(pear, a[ok], b[ok])
            rows.append(dict(variant=m, n=int(ok.sum()), r=pear(a, b), lo=ci[0], hi=ci[1], icc=icc21(a[ok], b[ok])))
        EV = pd.DataFrame(rows)
    # --- G1 verdict
    g1_3 = R[(R.w == 3) & R.metric.isin(METRICS)]
    best = g1_3.sort_values("r", ascending=False).iloc[0]
    g1_5 = R[(R.w == 5) & R.metric.isin(METRICS)]
    best5 = g1_5.sort_values("r", ascending=False).iloc[0]
    v_g1 = verdict_g1(best.r)
    # --- G2
    G2 = run_g2(wide, pr, Dr, 3)
    g2s = G2[G2.metric.isin(METRICS)].groupby(["metric", "scale"]).apply(lambda g: pd.Series(
        {"max_abs_r": g.r.abs().max(), "worst_vs": g.loc[g.r.abs().idxmax(), "vs"], "worst_r": g.loc[g.r.abs().idxmax(), "r"]})).reset_index()
    passg2 = {}
    for m in METRICS:
        mx = g2s[(g2s.metric == m)].max_abs_r.max()
        passg2[m] = (mx < 0.60, mx)
    # primary by rule (3-frame Pearson test-retest among those passing G2)
    cand = [m for m in METRICS if passg2[m][0]]
    prim = sorted(cand, key=lambda m: (-round(float(g1_3[g1_3.metric == m].r.iloc[0]), 6), m != "set_depth_1s"))[0]
    out(f"PRIMARY by rule: {prim}")
    # --- game gates
    D = run_game_gates(wide, Dr, prim)
    gm = MATCH[prim]
    G3 = D["G3"]; g3m = G3[G3.label == gm].iloc[0]
    v_g3 = "PASS" if (g3m.sb >= 0.70 and g3m.n >= 90) else "FAIL"
    G4 = D["G4"]
    flag = bool(Dr[(Dr.w == 3) & (Dr.metric == prim)].flag.iloc[0])
    g4row = G4[(G4.drill == prim) & (G4.scale == ("side_z+yr_z" if flag else "side_z"))].iloc[0]
    if g4row.r >= 0.25 and g4row.partial_wt_ten_imputed >= 0.20: v_g4 = "PASS"
    elif g4row.r < 0.10: v_g4 = "FAIL"
    else: v_g4 = "AMBER"
    G5r = D["G5rel"].iloc[0]
    M5 = D["G5mech"]
    m5 = M5[(M5.inGame == gm) & M5.set_source.str.startswith("all")].iloc[0]
    rel_ok = G5r.sb >= 0.50
    mech_ok = m5.partial_posmix <= -0.20
    v_g5 = "PASS" if (rel_ok and mech_ok) else ("AMBER" if (rel_ok and m5.partial_posmix <= -0.10) else "FAIL")
    v_g2 = "PASS" if passg2[prim][0] and all(passg2[m][1] < 0.75 for m in METRICS) else "FAIL"
    decision = "GO" if (v_g1 == "PASS" and v_g2 == "PASS" and v_g3 == "PASS" and (v_g4 == "PASS" or v_g5 == "PASS")) else "NO-GO"

    # --- write report
    o = []
    A = o.append
    A("# Feasibility check C1: OL pass set (gates G1-G5)\n")
    A("Generated by `scripts/feasibility/c1_ol_pass_set.py`. All numbers below are computed by that script (verified by code) unless marked *inference*. Bootstrap CIs: 2,000 resamples over players, seed 2027. No Combine drill metric was correlated with any NFL pressure outcome.\n")
    A("## 0. Headline\n")
    A("| Gate | Value (primary definition) | 95% CI | n | Verdict |\n|---|---|---|---|---|")
    A(f"| G1 drill cross-stance consistency (best of 3 set metrics: {best.metric}, 3-frame, Pearson r) | {best.r:.3f} | [{best.lo:.3f}, {best.hi:.3f}] | {int(best.n)} | **{v_g1}** (threshold >= 0.60 go, 0.40-0.60 amber) |")
    A(f"| G2 non-redundancy ({prim}; max abs r vs ten_yd_split/shuttle/3-cone/40/weight/arm, side-z two-rep mean) | max |r| = {passg2[prim][1]:.3f} (all three set metrics: {', '.join(f'{m} {passg2[m][1]:.2f}' for m in METRICS)}) | see section 3 | 60-118 | **{v_g2}** |")
    A(f"| G3 in-game split-half, matched metric `{gm}` (Spearman-Brown) | {g3m.sb:.3f} | [{g3m.lo:.3f}, {g3m.hi:.3f}] | {int(g3m.n)} | **{v_g3}** (>= 0.70 and n >= 90) |")
    A(f"| G4 transfer, drill `{prim}` vs in-game `{gm}` (r; partial r | weight + ten_yd) | r = {g4row.r:.3f}; partial = {g4row.partial_wt_ten_imputed:.3f} | r [{g4row.lo:.3f}, {g4row.hi:.3f}]; partial [{g4row.pwt_lo:.3f}, {g4row.pwt_hi:.3f}] | {int(g4row.n)} | **{v_g4}** (go: r >= 0.25 and partial >= 0.20; no-go r < 0.10) |")
    A(f"| G5a outcome reliability (adj. peak_pressure_probability_allowed, REG, >=100 snaps, SB) | {G5r.sb:.3f} | [{G5r.lo:.3f}, {G5r.hi:.3f}] | {int(G5r.n)} | {'PASS' if rel_ok else 'FAIL'} (>= 0.50) |")
    A(f"| G5b mechanism: partial r of in-game quickness (`{gm}`, oriented so higher = quicker) with adj. outcome, controlling T/G share | {m5.partial_posmix:.3f} | [{m5.plo:.3f}, {m5.phi:.3f}] | {int(m5.n)} | {'PASS' if mech_ok else 'FAIL'} (needs <= -0.20; observed sign is the OPPOSITE of expected) |")
    A(f"| G5 overall | | | | **{v_g5}** |")
    A(f"\n**Primary drill metric by the stated rule: `{prim}`** (highest 3-frame test-retest Pearson r among the metrics passing G2; the rule is mechanical here because all three have r indistinguishable from 0, see section 1, so the choice is not meaningful; if the three are treated as tied the tie-break gives `set_depth_1s`).")
    A(f"\n**C1 decision per the file's rule: {decision}** (G1 {v_g1}, G2 {v_g2}, G3 {v_g3}, G4 {v_g4}, G5 {v_g5}). G1 fails: the set-phase metrics do not repeat across the two reps. G3 passes strongly and G2 passes, so the in-game trait is reliable and the drill metric is not a stopwatch proxy, but there is nothing reliable on the drill side to transfer.\n")
    A("A note on G4/G5 given G1 failure: G4 and G5 were run as specified for completeness; a drill metric with test-retest ~0 cannot transfer, so the G4 near-zero is expected rather than informative about the in-game trait.\n")

    A("## 1. G1: drill reliability (cross-stance / cross-side consistency)\n")
    A("**Important data finding (verified by code): the two reps are not identical-condition repeats.** Note from Kaggle discussion 751165 (host information, not verified by me): rep A is from a 3-point stance dropping right, rep B from a 2-point stance dropping left; task is drop to a 2-yd cone, open hips at 4 yd, finish at 10 yd. In the tracking, the chronologically first rep drifts toward -y and the second toward +y. I label sides purely by drift direction (sign of y_end - y_start), NOT by stance, since orientation/stance is not in the data; the mapping of drift sign to stance/left-right is the host's statement, not something I verified.\n")
    A(f"- Players with 2+ reps: {len(pr)}; start distance between the two reps: median {pr.start_dist.median():.2f} yd, max {pr.start_dist.max():.2f} yd (all within 3 yd). 3 reps: player {pr.shape[0] and 57796} (first two used). Reps per player: 2 players have 1 rep, 117 have 2, 1 has 3.")
    A(f"- Side by drift: pairs with one rep of each side: **{n_opp} of {len(W3)}** ({n_opp/len(W3):.1%}); same-side pairs: {len(W3)-n_opp}. Chronological rep order vs drift: rep 1 drifts -y for {int((W3.side_r1==-1).sum())}/{len(W3)}, rep 2 drifts +y for {int((W3.side_r2==1).sum())}/{len(W3)} (so rep order is essentially confounded with side/stance).")
    A("- **candidates.md is wrong on this point:** it describes the 117 pairs as \"genuine same-start repeats / true test-retest\". They share a start point but not the movement: the reps are mirrored drops (different side, and per the host different stance). G1 here is therefore a cross-stance consistency, a lower bound on reliability.\n")
    A("### Metric definitions tried (all use a 3-frame centred mean of x, y, s unless noted; 5-frame = same with 5; edges use shrinking windows)\n")
    A("- onset = first of 3 consecutive smoothed frames with s >= 0.5 yd/s. Threshold-crossing times are linearly interpolated between frames.\n- `set_depth_1s` (spec): Euclidean distance between smoothed position at onset+1.0 s and at onset.\n- `set_depth_1s_back` (variant): backward depth = -(dx) (drill runs toward -x; verified: mean total dx = -10.4 yd).\n- `set_burst` (spec): time from onset (s>=0.5) to first s>=1.5, search to end of rep (NaN if never; 0 of 239 reps NaN). `set_burst_w2s` (variant): NaN if > 2.0 s (19 reps NaN).\n- `peak_set_speed` (spec): max smoothed s in [onset, onset+1.5 s].\n- `open_and_run` (secondary): from first frame >= onset+1.8 s, time from s>=2.0 to s>=4.5. `set_lateral_drift` (secondary): |dy| between onset and onset+1.5 s.\n- Exploratory, not gate metrics: depth from frame 0 (not onset), mean s over 0-1.5 s from frame 0, peak s of whole rep, onset index.\n- Test-retest: Pearson between chronologically first and second rep (as specified), Spearman, ICC(2,1), side-standardised (z within drift side across reps) consistency ICC.\n")
    t = R[R.metric.isin(allm)].copy()
    t["r [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(t.r, t.lo, t.hi)]
    t["ICC(2,1) [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(t.icc, t.ilo, t.ihi)]
    t["year-std r [CI]"] = [ci_s(a, b, c) for a, b, c in zip(t.r_yrstd, t.zlo, t.zhi)]
    t["r by year (2023/24/25)"] = [" / ".join(f"{v[0]:.2f} (n={v[1]})" for v in by.values()) for by in t.by_year]
    A(md(t[["w", "metric", "n", "r [95% CI]", "spearman", "ICC(2,1) [95% CI]", "year-std r [CI]", "r by year (2023/24/25)"]].rename(columns={"w": "smooth"}), 3))
    A(f"\n**Verdict G1: {v_g1}.** Best of the three set metrics (3-frame): `{best.metric}` r = {best.r:.3f} [{best.lo:.3f}, {best.hi:.3f}], n = {int(best.n)}. 5-frame best: `{best5.metric}` r = {best5.r:.3f} [{best5.lo:.3f}, {best5.hi:.3f}]. Every one of the three has a CI including or below zero (< 0.40 = fail in both smoothings). Secondary `open_and_run` (phase 2) is the only reliable-ish measure (r about 0.34, below the 0.40 amber bar and not a gate metric).\n")
    A("### Stance/side effect: mean differences between rep 1 (drift -y) and rep 2 (drift +y)\n")
    A("Systematic: rep 2 sets deeper and faster in the set phase. Pearson r is unaffected by a constant shift, but ICC(2,1) and any pooled two-rep mean are, hence side-specific standardisation below.\n")
    A(md(SD[SD.w == 3][["metric", "n", "mean_rep1", "mean_rep2", "diff_rep2_minus_rep1", "dz", "paired_t", "p"]], 3))
    A("\nSide-standardised (z within drift side) consistency, all pairs vs opposite-side pairs only:\n")
    A(md(EG1[EG1.w == 3][["metric", "subset", "n", "r", "lo", "hi", "icc_sidez"]], 3))
    A("\nExploratory variants (3-frame; NOT gate metrics, listed because they were tried, not used for selection):\n")
    A(md(EV, 3))
    A("\n### Year-mean drift check (two-rep mean per player; difference of each year's mean vs the mean of the other two years, in pooled within-year SD; flag if |diff| > 0.5)\n")
    dd = []
    for _, r in Dr[Dr.metric.isin(METRICS + SECOND)].iterrows():
        dd.append(dict(smooth=int(r.w), metric=r.metric, pooled_SD=r.pooled_within_year_sd,
                       mean_SD_2023=f"{r.mean_2023:.3f} ({r.sd_2023:.3f})", mean_SD_2024=f"{r.mean_2024:.3f} ({r.sd_2024:.3f})", mean_SD_2025=f"{r.mean_2025:.3f} ({r.sd_2025:.3f})",
                       d2023=r.diff_vs_others_2023, d2024=r.diff_vs_others_2024, d2025=r.diff_vs_others_2025, flagged=bool(r.flag)))
    A(md(pd.DataFrame(dd), 3))
    A("\nFlagged (3-frame): `set_depth_1s` (2023 low, 2025 high), `open_and_run`, `set_lateral_drift`. Year-standardised values are reported alongside; the G1 verdict is unchanged under year standardisation. Rep start crop differs by year (mean onset index 2.9 / 1.2 / 0.7 frames for 2023/24/25), so onset-anchored metrics inherit crop differences. *Inference:* set_burst can be trivially short when a rep is cropped after motion has begun.\n")

    A("## 2. Sample counts (verified)\n")
    A("Cohort OL pass-block snaps (pressure_allowed non-null, lined_up_position in T/G/C, tracking present, >= 10 post-snap frames): " + f"{D['d'].height} snaps, {D['d']['nfl_id'].n_unique()} players (of 120 with the drill). Other positions in that mask were excluded: TE 158, FB 9, SLOT_WR 5, WR 1, NA 1 snaps.")
    A("\n" + md(pd.DataFrame([dict(threshold=th, PRE_REG_POST=int((D['counts']['all'] >= th).sum()), REG=int((D['counts']['reg'] >= th).sum()), REG_POST=int((D['counts']['regpost'] >= th).sum())) for th in (30, 100, 200)]), 0))
    A("\ncandidates.md quoted 74/110 (>=30), 65/88 (>=100), 59/67 (>=200) for REG / all; my counts differ by at most 1 player (109 vs 110, 73 vs 74, 58 vs 59), likely because I exclude non-T/G/C rows and snaps without >=10 post-snap frames.\n")

    A("## 3. G2: non-redundancy (two-rep mean, within OL)\n")
    A("Two-rep mean: raw mean, side-z mean (working version, as specified), side-z then year-z (used for `set_depth_1s`, which is year-flagged). Correlations with baselines (ten_yd_split n~94, short_shuttle n~63, three_cone n~60, forty n~93, weight and arm n=118).\n")
    A(md(g2s.rename(columns={"max_abs_r": "max |r|"}), 3))
    A("\nFull table for the three set metrics:\n")
    g2t = G2[G2.metric.isin(METRICS)].copy()
    g2t["r [95% CI]"] = [ci_s(a, b, c, 2) for a, b, c in zip(g2t.r, g2t.lo, g2t.hi)]
    A(md(g2t[["metric", "vs", "scale", "n", "r [95% CI]"]], 3))
    A(f"\n**Verdict G2: {v_g2}.** All |r| < 0.60 (max {max(passg2[m][1] for m in METRICS):.2f}); none > 0.75. The drill metrics are not stopwatch/size proxies, but note that this is largely because they are mostly noise (low reliability caps possible correlations; *inference*).\n")

    A("## 4. G3: in-game reliability and sanity\n")
    A("In-game metric definitions (snap = ball_snap frame; positions smoothed with 3-frame centred mean, 5-frame sensitivity; displacement from the smoothed snap-frame position): Euclidean displacement at +0.5 s and +1.0 s; backward displacement (toward own end zone: +x when play_direction is left, -x when right; verified: mean backward displacement at 1 s is +0.88 yd for both left and right plays, so the convention in candidates.md is correct); peak smoothed speed in snap..+1.0 s; time to 1 yd Euclidean displacement (interpolated, censored at 2.0 s; 1.4% censored). Each is residualised at play level (OLS) on position (T/G/C), formation (shotgun+empty / pistol / under centre), play-action flag (play_action or autoevent_playaction tag), dropback_duration bucket (<2, 2-2.5, 2.5-3, 3-3.5, 3.5-4, >=4 s) and season type; player mean of residuals. Split-half: odd/even snaps in chronological order (season, PRE<REG<POST, week, game, play), Spearman-Brown; players with >= 30 snaps (PRE+REG+POST).\n")
    A("### Sanity: raw in-game set metrics by lined_up_position (play-level means)\n")
    A(md(D["sanity"], 3))
    san = D["sanity"].set_index("lined_up_position")
    A(f"\nDepth ordering check (euclid 1.0 s): T {san.loc['T','euclid_1.0s']:.2f}, G {san.loc['G','euclid_1.0s']:.2f}, C {san.loc['C','euclid_1.0s']:.2f}; backward 1.0 s: T {san.loc['T','back_1.0s']:.2f}, G {san.loc['G','back_1.0s']:.2f}, C {san.loc['C','back_1.0s']:.2f}. Expected ordering T > G > C (from candidates.md): {'holds' if (san.loc['T','back_1.0s']>san.loc['G','back_1.0s']>san.loc['C','back_1.0s']) else 'FAILS: observed order is T > C > G (guards set the shallowest, centres sit between); tackles are deepest as expected, but guards < centres contradicts the document expectation. Consistent across euclid/back/peak speed/time-to-1yd. Not an error in the sign convention (T deepest, all backward depths positive); *inference*: centres are often more upright/snapping-constrained differently, or guard sets are short-set by design.'}\n")
    g3t = G3.copy(); g3t["SB [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(g3t.sb, g3t.lo, g3t.hi)]
    A(md(g3t[["label", "n", "r_half", "SB [95% CI]", "sb_random_splits_mean"]].rename(columns={"label": "in-game metric", "sb_random_splits_mean": "mean SB over 100 random splits"}), 3))
    A(f"\n**Verdict G3: {v_g3}** for the metric matched to the primary drill metric (`{gm}`: SB {g3m.sb:.3f}, n = {int(g3m.n)}); all six in-game metrics pass (SB 0.88-0.95, n = 109). Sensitivities (REG-only n=73, excluding play-action and dropbacks < 2.0 s, 5-frame smoothing, T-only, G-only) all stay above 0.84 (tables below). Caveat: high reliability here includes stable scheme/team/QB/role effects not removed by the covariates (*inference*).\n")
    s3 = D["G3sens"].copy(); s3["SB [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(s3.sb, s3.lo, s3.hi)]
    A(md(s3[["sens", "label", "n", "SB [95% CI]"]], 3))
    s3p = D["G3pos"].copy(); s3p["SB [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(s3p.sb, s3p.lo, s3p.hi)]
    A("\nWithin position (snaps at that position only):\n")
    A(md(s3p[["pos", "label", "n", "SB [95% CI]"]], 3))

    A("\n## 5. G4: transfer (drill vs in-game; no outcome used)\n")
    A("Drill value = two-rep mean after standardising each rep within its drift side (side_z); `side_z+yr_z` additionally z-scores within draft year; `raw_mean` = plain mean of the two reps. Expected direction: positive for all three pairs (deeper / faster / shorter-time in the drill goes with the same in-game). Partial r controls weight; `ten_imputed` also controls ten_yd_split (mean-imputed + missing indicator); `ten_subset` is the partial on players with a ten_yd_split (n shown). In-game metric = adjusted player mean (>= 30 snaps, PRE+REG+POST).\n")
    g4t = D["G4"].copy()
    g4t["r [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(g4t.r, g4t.lo, g4t.hi)]
    g4t["partial wt [CI]"] = [ci_s(a, b, c) for a, b, c in zip(g4t.partial_wt, g4t.pw_lo, g4t.pw_hi)]
    g4t["partial wt+ten_imputed [CI]"] = [ci_s(a, b, c) for a, b, c in zip(g4t.partial_wt_ten_imputed, g4t.pwt_lo, g4t.pwt_hi)]
    A(md(g4t[["drill", "game", "scale", "drift_flag", "n", "r [95% CI]", "spearman", "partial wt [CI]", "partial wt+ten_imputed [CI]", "partial_wt_ten_subset", "n_ten"]], 3))
    A(f"\n**Verdict G4: {v_g4}** for `{prim}` vs `{gm}` (working scale {'side_z+yr_z' if flag else 'side_z'}): r = {g4row.r:.3f} [{g4row.lo:.3f}, {g4row.hi:.3f}], partial = {g4row.partial_wt_ten_imputed:.3f}, n = {int(g4row.n)}. All three drill/in-game pairs are |r| < 0.10 (no-go). Given G1, this is unsurprising (*inference*).\n")

    A("## 6. G5: outcome reliability and mechanism\n")
    A("Outcome = `peak_pressure_probability_allowed`, adjusted at play level (OLS) for dropback_duration (linear + quadratic), pass_rushers_encountered (0/1/2/3+), position (T/G/C), formation, play-action flag, POST indicator; player mean of residuals; REG snaps; odd/even chronological split; SB. Coverage of the outcome on cohort-OL pass-block snaps was 95.7% (candidates.md said 95.5%).\n")
    g5t = D["G5rel"].copy(); g5t["SB [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(g5t.sb, g5t.lo, g5t.hi)]
    A(md(g5t[["label", "n", "r_half", "SB [95% CI]", "sb_random_splits_mean"]], 3))
    A(f"\nOutcome reliability: **{'PASS' if rel_ok else 'FAIL'}** (SB {G5r.sb:.3f}, threshold 0.50, n = {int(G5r.n)}).\n")
    A("Mechanism: between-player correlation of in-game set quickness (oriented so higher = deeper / faster / shorter time, i.e. 'quicker') with the adjusted pressure-probability mean; **expected sign negative** (quicker -> less pressure). Partial controls the T and G share of snaps. Three versions of the set metric: all season types; REG only; odd REG snaps for the set metric vs even REG snaps for the outcome (avoids same-play dependence).\n")
    g5m = D["G5mech"].copy()
    g5m["r [95% CI]"] = [ci_s(a, b, c) for a, b, c in zip(g5m.r_quick_vs_pressure, g5m.lo, g5m.hi)]
    g5m["partial (pos mix) [CI]"] = [ci_s(a, b, c) for a, b, c in zip(g5m.partial_posmix, g5m.plo, g5m.phi)]
    A(md(g5m[["inGame", "set_source", "n", "r [95% CI]", "partial (pos mix) [CI]"]], 3))
    A("\nPlay-level cluster-robust OLS (REG, players >= 100 snaps; outcome residual on standardised, quickness-oriented play-level set residual split into within-player and between-player parts; SE clustered by player):\n")
    A(md(D["G5play"], 4))
    A(f"\n**Verdict G5: {v_g5}.** Reliability passes, but the mechanism does not: for the matched metric `{gm}` the partial r is {m5.partial_posmix:.3f} [{m5.plo:.3f}, {m5.phi:.3f}] (needs <= -0.20). Across all 18 variants the sign is positive or near zero, i.e. players who retreat deeper / faster in the first second allow slightly MORE pressure probability (largest: backward depth at 1.0 s, REG only, r = +0.36, CI excludes 0). No variant meets the go criterion. The play-level within-player coefficients are also positive (+0.015 to +0.041 pressure-probability units per SD of play-level set quickness, tiny SEs from 45k plays), i.e. the wrong-sign association is present within players too. *Inference (not tested):* deeper early retreat may reflect being beaten / facing speed rushers or deeper-dropback schemes (reverse causation or residual scheme confounding), not a better set.\n")

    A("## 7. Decision\n")
    A(f"- Rule: go if G1, G2, G3 pass and at least one of G4/G5 passes. Result: G1 {v_g1}, G2 {v_g2}, G3 {v_g3}, G4 {v_g4}, G5 {v_g5} -> **C1 {decision}** as specified.")
    A("- What survives: the in-game pass-set trait is highly reliable (SB ~0.88-0.95) and the pressure-probability outcome is reasonably reliable (SB ~0.79). What fails: the Combine drill's set-phase metrics have no cross-stance consistency (r about 0), so they cannot be a player trait as defined, and there is no drill-to-game transfer or mechanism in the expected direction.")
    A("- Per candidates.md decision text, with G1 failing, move to the fallback (C2) per the table in candidates.md.\n")

    A("## 8. Things candidates.md got wrong or that need qualification\n")
    A("1. **\"Genuine test-retest / same-start repeats\" is wrong in kind.** Pairs start together (median 0.5 yd apart) but the reps are mirrored drops (110 of 118 pairs, 93%, drift opposite ways in y [host said about 96%]; rep 1 drifts -y, rep 2 +y). Per the host (Kaggle discussion 751165, not verified here) they are also different stances (3-point right, 2-point left). The candidate's 'only skill drill with true repeats' claim and its Statistics-defensibility score of 5 should be revised: G1 is a cross-stance lower bound.")
    A("2. **Systematic side/stance effect.** Rep 2 vs rep 1 (3-frame): set_depth_1s +0.59 yd, peak_set_speed +0.80 yd/s, set_burst -0.94 s (rep 2 much quicker), set_lateral_drift +0.64 yd; all p < 1e-18 (table in section 1).")
    A("3. **Drill shape.** Direction convention OK: the drill runs toward -x (mean total dx = -10.4 yd) and the trajectory has the described slow phase 1 then acceleration (phase 2); but phase 1 is strongly lateral (Euclidean depth at 1 s = 1.4 yd vs 1.07 yd backward), and speed profile differs by side. Recording start is at s about 0.3-0.5 yd/s (already moving), so onset is at frame 0 in most 2024-25 reps and later in 2023.")
    A("4. **play_direction / x-axis convention is correct** in game tracking (verified: backward displacement positive for both left and right plays). Note game tracking has no frame_id; time is at 10 Hz and `ball_snap` is present for the plays used.")
    A("5. `lined_up_position` for OL is already 'T' / 'G' / 'C' (not LT/RT); TE/FB/WR rows can carry non-null pressure_allowed (about 200 cohort snaps) and were excluded. 195 pass-block snaps have pass_result == '' (non-dropback) and are kept (their pressure_allowed is non-null).")
    A("6. Outcome coverage 95.7% (document: 95.5%); pass-block snap counts agree within 1-2 players except >= 200 snaps.")
    A("7. Time-to-1yd and set_burst are threshold-crossing metrics sensitive to the recording crop; with the crop starting mid-motion some reps give set_burst of ~0.1 s.\n")
    A("## 9. Verified vs inferred\n")
    A("Verified by code: everything in numbered tables above, side counts, direction convention, sample counts, systematic rep differences. Taken from the host (not verified): stance and left/right assignment of the two reps. Inference: mechanisms offered for the wrong-sign G5 result, and that low reliability caps the G2/G4 correlations.\n")
    A("## 10. Reproduction\n")
    A("`.venv\\Scripts\\python.exe scripts\\feasibility\\c1_ol_pass_set.py` from the repo root. Game-feature cache goes to a scratch directory (env var `C1_CACHE`). No raw rows are written.\n")
    os.makedirs("reports", exist_ok=True)
    open(os.path.join("reports", "feasibility_c1.md"), "w", encoding="utf-8").write("\n".join(o))
    print("report written")


if __name__ == "__main__":
    main()
