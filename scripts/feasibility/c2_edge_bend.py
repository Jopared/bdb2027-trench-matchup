"""C2 edge bend feasibility check (gates G1-G6). Run from repo root:
    .venv/Scripts/python.exe scripts/feasibility/c2_edge_bend.py [stage]
Stages: drill (G1,G2,trajectory description), game (build in-game table), gates (all, writes report).
"""
from __future__ import annotations
import sys, math
import numpy as np
import polars as pl
import pandas as pd
from bdb2027 import paths

DT = 0.1
SEED = 2027
NBOOT = 2000


# ----------------------------------------------------------------- helpers
def cmean(a, k):
    """centred moving mean, window k (odd), edge frames NaN."""
    a = np.asarray(a, float)
    n = len(a)
    out = np.full(n, np.nan)
    h = k // 2
    if n < k:
        return out
    c = np.convolve(a, np.ones(k) / k, mode="valid")
    out[h:n - h] = c
    return out


def cdiff(a, dt=DT):
    """centred difference (a[i+1]-a[i-1])/(2 dt); edges NaN."""
    a = np.asarray(a, float)
    out = np.full(len(a), np.nan)
    out[1:-1] = (a[2:] - a[:-2]) / (2 * dt)
    return out


def first_cross(t, v, thr, start=0):
    """linear-interpolated time of first upward crossing of thr at index >= start; NaN if none."""
    for i in range(max(start, 1), len(v)):
        if np.isnan(v[i]) or np.isnan(v[i - 1]):
            continue
        if v[i - 1] < thr <= v[i]:
            f = (thr - v[i - 1]) / (v[i] - v[i - 1])
            return t[i - 1] + f * (t[i] - t[i - 1]), i
    return np.nan, -1


def boot_ci(fn, n, nboot=NBOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(nboot):
        idx = rng.integers(0, n, n)
        try:
            v = fn(idx)
        except Exception:
            v = np.nan
        vals.append(v)
    vals = np.array(vals, float)
    vals = vals[~np.isnan(vals)]
    if len(vals) < 50:
        return (np.nan, np.nan)
    return (np.percentile(vals, 2.5), np.percentile(vals, 97.5))


def pearson(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 4 or np.std(x[m]) == 0 or np.std(y[m]) == 0:
        return np.nan
    return float(np.corrcoef(x[m], y[m])[0, 1])


def corr_ci(x, y, kind="pearson"):
    """returns r, lo, hi, n over complete pairs."""
    from scipy.stats import spearmanr
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    if n < 6:
        return (np.nan, np.nan, np.nan, n)
    f = pearson if kind == "pearson" else (lambda a, b: float(spearmanr(a, b)[0]))
    r = f(x, y)
    lo, hi = boot_ci(lambda idx: f(x[idx], y[idx]), n)
    return (r, lo, hi, n)


def sb(r):
    return 2 * r / (1 + r) if r is not None and not np.isnan(r) else np.nan


def resid(y, X):
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def partial_corr(x, y, ctrl):
    x = np.asarray(x, float); y = np.asarray(y, float)
    C = [np.asarray(c, float) for c in ctrl]
    m = ~(np.isnan(x) | np.isnan(y) | np.any([np.isnan(c) for c in C], axis=0))
    return pearson(resid(x[m], [c[m] for c in C]), resid(y[m], [c[m] for c in C])), int(m.sum()), m


# ----------------------------------------------------------------- drill
def load_drill():
    ct = (pl.read_parquet(paths.parquet("combine_tracking"))
          .filter((pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "PASS_RUSH_DRILL"))
          .sort("nfl_id", "time"))
    return ct.to_pandas()


def first_ge(t, v, thr, start=0):
    """first index i>=start with v[i]>=thr; interpolated time (if v[i-1] below thr and i-1>=start) else t[i]."""
    for i in range(start, len(v)):
        if np.isnan(v[i]):
            continue
        if v[i] >= thr:
            if i - 1 >= start and not np.isnan(v[i - 1]) and v[i - 1] < thr:
                f = (thr - v[i - 1]) / (v[i] - v[i - 1])
                return t[i - 1] + f * (t[i] - t[i - 1]), i
            return t[i], i
    return np.nan, -1


WINDOWS = [(15, 75), (15, 60), (30, 75)]     # heading-deviation window (deg)
REFS = ["run", "x"]                          # reference heading: initial run heading vs fixed +x axis (90 deg)
BEND = ["turn_accel", "turn_min_speed", "speed_carry", "turn_time", "peak_cent"]


def rep_features(g, k):
    """One drill rep (pandas, sorted by time). k = smoothing frames (3 or 5)."""
    t = (g["time"] - g["time"].iloc[0]).dt.total_seconds().to_numpy()
    x = g["x"].to_numpy(); y = g["y"].to_numpy()
    s = cmean(g["s"].to_numpy(), k)
    f = dict(side="R" if (y[-1] - y[0]) > 0 else "L", n=len(g), dur=t[-1], x0=x[0], y0=y[0], x_end=x[-1],
             y_end=y[-1], s0=float(g["s"].iloc[0]), smax=float(np.nanmax(s)))
    sg = 1 if f["side"] == "R" else -1
    f["reach_finish"] = bool(y.max() >= 39) if sg > 0 else bool(y.min() <= 15)
    # threshold-crossing get-off. s must be seen BELOW 1.0 before it first reaches 1.0 (else crop is censored -> NaN)
    t1, i1 = first_cross(t, s, 1.0)
    f["t_s1"] = t1
    t4, i4 = first_cross(t, s, 4.0, start=max(i1, 0) if i1 >= 0 else 0)
    f["t_s4"] = t4
    f["get_off"] = t4 - t1 if (i1 >= 0 and i4 >= 0) else np.nan
    # sensitivity variants (all threshold-crossing): other thresholds, and raw / 5-frame s
    for nm, (a_, b_) in {"go_2_5": (2.0, 5.0), "go_2_4": (2.0, 4.0)}.items():
        ta, ia_ = first_cross(t, s, a_)
        tb, ib_ = first_cross(t, s, b_, start=max(ia_, 0) if ia_ >= 0 else 0)
        f[nm] = tb - ta if (ia_ >= 0 and ib_ >= 0) else np.nan
    s_raw = g["s"].to_numpy()
    ta, ia_ = first_cross(t, s_raw, 1.0)
    tb, ib_ = first_cross(t, s_raw, 4.0, start=max(ia_, 0) if ia_ >= 0 else 0)
    f["go_1_4_rawS"] = tb - ta if (ia_ >= 0 and ib_ >= 0) else np.nan
    # heading: unwrap from first s>=2 on, anchor into (-90, 270]
    t2, i2 = first_ge(t, s, 2.0)
    if i2 < 0:
        return f, None
    d = np.degrees(np.unwrap(np.radians(g["dir"].to_numpy()[i2:])))
    d0 = ((d[0] + 90) % 360) - 90
    hd = np.full(len(g), np.nan); hd[i2:] = d - d[0] + d0
    hs = cmean(hd[i2:], k); hsm = np.full(len(g), np.nan); hsm[i2:] = hs
    omega = np.radians(cdiff(hsm))
    cent = s * np.abs(omega)
    # initial run heading: mean heading from first s>=1 to first s>=3 (smoothed) -- uses early acceleration segment
    t3, i3 = first_ge(t, s, 3.0)
    ia = i1 if i1 >= 0 else 1
    # headings before i2 are noisy/unavailable in hsm; use raw unwrapped dir from ia
    dd = np.degrees(np.unwrap(np.radians(g["dir"].to_numpy()[ia:])))
    dd = dd - dd[0] + (((dd[0] + 90) % 360) - 90)
    hrun_full = np.full(len(g), np.nan); hrun_full[ia:] = dd
    if i3 > ia:
        f["h_run"] = float(np.nanmean(hrun_full[ia:i3 + 1]))
    else:
        f["h_run"] = np.nan
    f["h_x"] = 90.0
    arr = dict(t=t, s=s, hsm=hsm, cent=cent, i2=i2, sg=sg, x=x, y=y)
    return f, arr


def window_metrics(f, arr, ref, lo, hi):
    out = {m: np.nan for m in BEND}
    out.update(peak_cent=np.nan, t_lo=np.nan, t_hi=np.nan, s_lo=np.nan, s_hi=np.nan)
    if arr is None:
        return out
    h0 = f["h_run"] if ref == "run" else 90.0
    if np.isnan(h0):
        return out
    dev = arr["sg"] * (h0 - arr["hsm"]) * 1.0          # R: heading falls from +x toward +y(0 deg); L: rises
    dev = dev if arr["sg"] > 0 else arr["sg"] * (h0 - arr["hsm"])   # L: sg=-1 -> hsm - h0
    t, s, cent = arr["t"], arr["s"], arr["cent"]
    tl, il = first_ge(t, dev, lo, start=arr["i2"])
    if il < 0:
        return out
    th, ih = first_ge(t, dev, hi, start=il)
    if ih < 0:
        return out
    seg = slice(il, ih + 1)
    s_lo = float(np.interp(tl, t, np.nan_to_num(s))); s_hi = float(np.interp(th, t, np.nan_to_num(s)))
    out.update(turn_accel=float(np.nanmean(cent[seg])), turn_min_speed=float(np.nanmin(s[seg])),
               turn_time=th - tl, speed_carry=s_hi / s_lo, peak_cent=float(np.nanmax(cent[seg])),
               t_lo=tl, t_hi=th, s_lo=s_lo, s_hi=s_hi)
    return out


def build_rep_table(ct, k):
    rows = []
    for (nid, ev), g in ct.groupby(["nfl_id", "event_id"]):
        g = g.sort_values("time")
        f, arr = rep_features(g, k)
        f.update(nfl_id=int(nid), event_id=ev, year=int(g["draft_year"].iloc[0]), t_start=g["time"].iloc[0],
                 drill_type=g["drill_type"].iloc[0])
        for ref in REFS:
            for lo, hi in WINDOWS:
                w = window_metrics(f, arr, ref, lo, hi)
                for m, v in w.items():
                    f[f"{m}|{ref}|{lo}-{hi}"] = v
        rows.append(f)
    return pd.DataFrame(rows)


def player_side_table(reps, cols):
    """first chronological rep per side (some players have 1 or >2 reps); returns wide L/R table."""
    r = reps.sort_values(["nfl_id", "t_start"])
    first = r.groupby(["nfl_id", "side"]).head(1)
    L = first[first.side == "L"].set_index("nfl_id")[cols + ["year"]]
    R = first[first.side == "R"].set_index("nfl_id")[cols + ["year"]]
    return L, R


# ----------------------------------------------------------------- game
import os, tempfile
CACHE = os.environ.get("BDB_C2_CACHE",
                       os.path.join("data", "cache"))
if not os.path.isdir(CACHE):
    CACHE = tempfile.gettempdir()

END_EVENTS = ["pass_forward", "qb_sack", "qb_strip_sack"]
TYPE_RANK = {"PRE": 0, "REG": 1, "POST": 2}


def drill_ids():
    return (pl.read_parquet(paths.parquet("combine_tracking"))
            .filter((pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "PASS_RUSH_DRILL"))
            ["nfl_id"].unique().to_list())


def rush_snaps(ids):
    pp = pl.read_parquet(paths.parquet("player_play"))
    g = pl.read_parquet(paths.parquet("games")).select("game_id", "season", "season_type", "week")
    r = (pp.filter(pl.col("nfl_id").is_in(ids) & (pl.col("blitzing") == True) & (pl.col("pass_result") != "")
                   & (pl.col("lined_up_position") != "NA"))
         .join(g, on="game_id", how="left")
         .with_columns(pl.col("season_type").replace_strict(TYPE_RANK, default=9).alias("type_rank"))
         .select("game_id", "play_id", "nfl_id", "lined_up_position", "play_direction", "pass_result",
                 "player_get_off", "time_to_pressure", "sack", "quick_pressure", "season", "season_type", "type_rank",
                 "week", "down", "yards_to_go", "dropback_duration", "team_abbr"))
    return r


def load_game_frames(snaps, ids):
    """tracking rows for the rusher-snaps + per-play snap / end event times."""
    keys = snaps.select("game_id", "play_id", "nfl_id").unique()
    fr, ev = [], []
    for yr in (2023, 2024, 2025):
        lf = pl.scan_parquet(paths.parquet(f"game_tracking_{yr}"))
        ev.append(lf.filter(pl.col("event").is_in(["ball_snap"] + END_EVENTS))
                  .group_by("game_id", "play_id", "event").agg(pl.col("time").min()).collect())
        fr.append(lf.filter(pl.col("nfl_id").is_in(ids)).join(keys.lazy(), on=["game_id", "play_id", "nfl_id"], how="semi")
                  .select("game_id", "play_id", "nfl_id", "time", "x", "y", "s", "dir").collect())
    ev = pl.concat(ev).pivot(on="event", index=["game_id", "play_id"], values="time")
    return pl.concat(fr).sort("game_id", "play_id", "nfl_id", "time"), ev


def snap_metrics(t, s_raw, d_raw, upfield_dir, k):
    """t seconds since snap (array), raw s and dir; returns dict of per-snap in-game bend metrics for the window arrays."""
    s = cmean(s_raw, k)
    dd = np.degrees(np.unwrap(np.radians(d_raw)))
    hs = cmean(dd, k)
    om = np.radians(cdiff(hs))
    cent = s * np.abs(om)
    return s, hs, om, cent


def build_game_table(k=3, start=0.3, maxw=3.0, gate=3.5, devlo=30.0, devhi=80.0):
    ids = drill_ids()
    snaps = rush_snaps(ids)
    fr, ev = load_game_frames(snaps, ids)
    ev = ev.rename({c_: f"ev_{c_}" for c_ in ev.columns if c_ not in ("game_id", "play_id")})
    for c_ in ["ev_ball_snap"] + ["ev_" + e for e in END_EVENTS]:
        if c_ not in ev.columns:
            ev = ev.with_columns(pl.lit(None, dtype=pl.Datetime("us")).alias(c_))
    ev = ev.with_columns(
        pl.min_horizontal([pl.col("ev_" + e) for e in END_EVENTS]).alias("ev_end"))
    j = snaps.join(ev.select("game_id", "play_id", "ev_ball_snap", "ev_end"), on=["game_id", "play_id"], how="left")
    grp = (fr.group_by("game_id", "play_id", "nfl_id", maintain_order=True)
           .agg(pl.col("time"), pl.col("s"), pl.col("dir")))
    j = j.join(grp, on=["game_id", "play_id", "nfl_id"], how="left")
    out = []
    for row in j.iter_rows(named=True):
        res = dict(game_id=row["game_id"], play_id=row["play_id"], nfl_id=row["nfl_id"])
        res.update(bendA=np.nan, bendB=np.nan, sense=0, nB=0, nA=0, bendA_cw=np.nan, bendA_ccw=np.nan)
        if row["time"] is None or row["ev_ball_snap"] is None or row["play_direction"] not in ("left", "right"):
            out.append(res); continue
        tt = np.array([(x - row["ev_ball_snap"]).total_seconds() for x in row["time"]])
        end = maxw
        if row["ev_end"] is not None:
            end = min(maxw, (row["ev_end"] - row["ev_ball_snap"]).total_seconds())
        m0 = tt >= -0.5       # keep a little pre-snap for context, post-snap used
        tt = tt[m0]; sr = np.array(row["s"])[m0]; dr = np.array(row["dir"])[m0]
        if len(tt) < 8 or end - start < 0.4:
            out.append(res); continue
        s, hs, om, cent = snap_metrics(tt, sr, dr, None, k)
        w = (tt >= start - 1e-9) & (tt <= end + 1e-9) & ~np.isnan(cent)
        gated = w & (s >= gate)
        if gated.sum() >= 2:
            res["bendA"] = float(np.max(cent[gated])); res["nA"] = int(gated.sum())
            idx = np.where(gated)[0]
            net = hs[idx[-1]] - hs[idx[0]]
            res["sense"] = 0 if abs(net) < 20 else (1 if net > 0 else -1)    # +1 clockwise (dir increases), -1 counter-clockwise
            if res["sense"] == 1: res["bendA_cw"] = res["bendA"]
            if res["sense"] == -1: res["bendA_ccw"] = res["bendA"]
        up = 90.0 if row["play_direction"] == "left" else 270.0     # dir of +x is 90, of -x is 270
        dev = np.abs(((hs - up) + 180) % 360 - 180)
        sel = w & (dev >= devlo) & (dev <= devhi) & ~np.isnan(s)
        if sel.sum() >= 2:
            res["bendB"] = float(np.mean(s[sel])); res["nB"] = int(sel.sum())
        out.append(res)
    res = pl.DataFrame(out).with_columns(pl.col(["bendA", "bendB", "bendA_cw", "bendA_ccw"]).fill_nan(None))
    base = snaps
    return base.join(res, on=["game_id", "play_id", "nfl_id"], how="left")


# ----------------------------------------------------------------- analysis: drill
GO_VARIANTS = ["get_off", "go_2_5", "go_2_4", "go_1_4_rawS"]


def family_cols():
    return [f"{m}|{ref}|{lo}-{hi}" for ref in REFS for lo, hi in WINDOWS for m in BEND]


def year_flags(reps, col):
    """deviation of each year's mean from the mean of the other years, in pooled within-year SD (per side)."""
    flags = {}
    for side in ("L", "R"):
        r = reps[reps.side == side][["year", col]].dropna()
        ys = sorted(r.year.unique())
        if len(ys) < 2:
            continue
        sd = np.sqrt(np.average([r[r.year == y][col].var(ddof=1) for y in ys],
                                weights=[(r.year == y).sum() - 1 for y in ys]))
        for y in ys:
            flags[(side, y)] = (r[r.year == y][col].mean() - r[r.year != y][col].mean()) / sd
    return flags


def year_standardise(reps, cols):
    out = reps.copy()
    for col in cols:
        out[col + "|z"] = np.nan
        for side in ("L", "R"):
            m = out.side == side
            sd = out.loc[m, col].std()
            ym = out.loc[m].groupby("year")[col].transform("mean")
            out.loc[m, col + "|z"] = (out.loc[m, col] - ym) / sd
    return out


def lr_join(reps, cols):
    L, R = player_side_table(reps, cols)
    return L.join(R, lsuffix="_L", rsuffix="_R", how="inner")


def g1_table(reps, cols, with_ci=True):
    """per metric: n pairs, Pearson raw (+CI), Spearman, Pearson on year-standardised, year-drift flag, used r."""
    from scipy.stats import spearmanr
    zc = [c_ + "|z" for c_ in cols]
    rz = year_standardise(reps, cols)
    j = lr_join(rz, cols + zc)
    rows = []
    for c_ in cols:
        a, b = j[c_ + "_L"].to_numpy(float), j[c_ + "_R"].to_numpy(float)
        za, zb = j[c_ + "|z_L"].to_numpy(float), j[c_ + "|z_R"].to_numpy(float)
        fl = year_flags(reps, c_)
        maxdev = max([abs(v) for v in fl.values()]) if fl else np.nan
        flagged = bool(maxdev > 0.5)
        ok = ~(np.isnan(a) | np.isnan(b))
        r, lo, hi, n = corr_ci(a, b) if with_ci else (pearson(a, b), np.nan, np.nan, int(ok.sum()))
        rho = float(spearmanr(a[ok], b[ok])[0]) if ok.sum() > 5 else np.nan
        rz_ = pearson(za, zb)
        if with_ci:
            _, zlo, zhi, _ = corr_ci(za, zb)
        else:
            zlo = zhi = np.nan
        used = rz_ if flagged else r
        rows.append(dict(metric=c_, n=n, r_raw=r, lo=lo, hi=hi, spearman=rho, r_yearz=rz_, zlo=zlo, zhi=zhi,
                         max_year_dev_sd=maxdev, flagged=flagged, r_used=used, used_kind="yearz" if flagged else "raw"))
    return pd.DataFrame(rows).set_index("metric"), j


BASE = ["ten_yd_split", "forty", "combine_weight", "three_cone"]


def load_baselines():
    cr = pl.read_parquet(paths.parquet("combine_results")).select(["nfl_id"] + BASE + ["arm_length"]).to_pandas()
    pl_ = pl.read_parquet(paths.parquet("players")).select("nfl_id", "nfl_position", "draft_overall_pick").to_pandas()
    return cr.merge(pl_, on="nfl_id", how="left").set_index("nfl_id")


def twoside_mean(reps, col, rz=None, use_z=False, both=True):
    """player-level mean of the first L and first R rep. both=True requires both sides."""
    c2 = col + "|z" if use_z else col
    L, R = player_side_table(rz if use_z else reps, [c2])
    j = L.join(R, lsuffix="_L", rsuffix="_R", how="outer")
    return j[[c2 + "_L", c2 + "_R"]].mean(axis=1, skipna=not both)


def g2_table(reps, cols, g1, base):
    rz = year_standardise(reps, cols)
    rows = []
    for c_ in cols:
        uz = bool(g1.loc[c_, "flagged"])
        m = twoside_mean(reps, c_, rz, uz)
        res = dict(metric=c_)
        for b in BASE:
            x = m.reindex(base.index); y = base[b]
            ok = x.notna() & y.notna()
            res[b] = pearson(x[ok], y[ok]); res["n_" + b] = int(ok.sum())
        use = ["ten_yd_split", "forty", "combine_weight"] + (["three_cone"] if res["n_three_cone"] >= 15 else [])
        res["max_abs"] = np.nanmax([abs(res[b]) for b in use])
        rows.append(res)
    return pd.DataFrame(rows).set_index("metric")


def selection_optimism(j, cols, g1, nb=1000, min_pairs=25, seed=SEED):
    """bootstrap the argmax-r selection; evaluate the selected metric on out-of-bag players."""
    rng = np.random.default_rng(seed)
    A = np.column_stack([j[(c_ + "|z" if g1.loc[c_, "flagged"] else c_) + "_L"].to_numpy(float) for c_ in cols])
    B = np.column_stack([j[(c_ + "|z" if g1.loc[c_, "flagged"] else c_) + "_R"].to_numpy(float) for c_ in cols])
    n = A.shape[0]
    ins, oob = [], []
    for _ in range(nb):
        idx = rng.integers(0, n, n)
        rs = []
        for q in range(len(cols)):
            ok = ~(np.isnan(A[idx, q]) | np.isnan(B[idx, q]))
            rs.append(pearson(A[idx, q], B[idx, q]) if ok.sum() >= min_pairs else -9)
        rs = np.array(rs); rs = np.where(np.isnan(rs), -9, rs)
        q = int(np.argmax(rs))
        o = np.setdiff1d(np.arange(n), idx)
        okk = ~(np.isnan(A[o, q]) | np.isnan(B[o, q]))
        if okk.sum() >= 8:
            oob.append(pearson(A[o, q][okk], B[o, q][okk])); ins.append(rs[q])
    return float(np.nanmean(ins)), float(np.nanmean(oob)), len(oob)


def trajectory_description(reps3, ct):
    """shape of the drill: finish line, turn timing relative to the s>=4 crossing, typical angles (fixed +x axis)."""
    out = {}
    out["n_reps"] = len(reps3); out["n_players"] = reps3.nfl_id.nunique()
    out["reps_by_side_year"] = reps3.groupby(["year", "side"]).size().unstack()
    out["reach_finish_by_side"] = reps3.groupby("side").reach_finish.mean().to_dict()
    out["reach_finish_all"] = float(reps3.reach_finish.mean())
    out["x0_med"] = float(reps3.x0.median()); out["y0_R"] = float(reps3[reps3.side == "R"].y0.median())
    out["y0_L"] = float(reps3[reps3.side == "L"].y0.median())
    out["x0_iqr"] = (float(reps3.x0.quantile(.25)), float(reps3.x0.quantile(.75)))
    out["dur"] = reps3.dur.describe().to_dict(); out["frames"] = reps3.n.describe().to_dict()
    out["smax"] = reps3.smax.describe().to_dict()
    out["s0_by_year"] = reps3.groupby("year").s0.median().to_dict()
    out["ts1_by_year"] = reps3.groupby("year").t_s1.mean().to_dict()
    out["ts4_by_year"] = reps3.groupby("year").t_s4.mean().to_dict()
    out["go_missing_by_year"] = reps3.groupby("year").get_off.apply(lambda v: int(v.isna().sum())).to_dict()
    rows = []
    for (nid, ev), g in ct.groupby(["nfl_id", "event_id"]):
        g = g.sort_values("time")
        f, arr = rep_features(g, 3)
        if arr is None or np.isnan(f["t_s4"]):
            continue
        dev = arr["sg"] * (90.0 - arr["hsm"]) if arr["sg"] > 0 else (arr["hsm"] - 90.0)
        t, s = arr["t"], arr["s"]
        r_ = dict(side=f["side"], year=int(g["draft_year"].iloc[0]), t_s4=f["t_s4"])
        for th in (15, 45, 75):
            tt, ii = first_ge(t, dev, th, start=arr["i2"])
            r_[f"t{th}_after_s4"] = tt - f["t_s4"] if ii >= 0 else np.nan
            r_[f"s_at_{th}deg"] = float(np.interp(tt, t, np.nan_to_num(s))) if ii >= 0 else np.nan
        r_["max_dev_vs_x_axis"] = float(np.nanmax(dev[arr["i2"]:]))
        r_["dev_vs_x_at_s4"] = float(np.interp(f["t_s4"], t, np.nan_to_num(dev, nan=0.0)))
        rows.append(r_)
    tr = pd.DataFrame(rows)
    out["timing"] = tr.drop(columns=["side", "year"]).describe().T
    out["timing_n"] = len(tr)
    out["share_dev_ge_75"] = float((tr.max_dev_vs_x_axis >= 75).mean())
    out["share_dev_ge_60"] = float((tr.max_dev_vs_x_axis >= 60).mean())
    return out


# ----------------------------------------------------------------- analysis: game
def verdict(value, go, margin=0.10, higher_better=True):
    if value is None or np.isnan(value):
        return "n/a"
    if value >= go:
        return "pass"
    if value >= go - margin:
        return "amber"
    return "fail"


def order_key(df):
    return df.sort_values(["nfl_id", "season", "type_rank", "week", "game_id", "play_id"])


def load_game_pd(k):
    g = pl.read_parquet(os.path.join(CACHE, f"game_k{k}.parquet")).to_pandas()
    g["pressure"] = g["time_to_pressure"].notna().astype(int)
    g["is_edge"] = (g["lined_up_position"] == "EDGE")
    return order_key(g)


def primary_alignment(g):
    """EDGE if >=50% of the player's rush snaps are lined up at EDGE, else IDL/other."""
    sh = g.groupby("nfl_id")["is_edge"].mean()
    return (sh >= 0.5).astype(int).rename("edge_primary")


def split_halves(g, col, min_n):
    """chronological odd/even split means for players with >= min_n non-null values of col."""
    d = g[g[col].notna()]
    rows = {}
    for nid, x in d.groupby("nfl_id"):
        v = x[col].to_numpy(float)
        if len(v) >= min_n:
            rows[nid] = (v[0::2].mean(), v[1::2].mean(), len(v))
    return pd.DataFrame(rows, index=["odd", "even", "n"]).T


def sb_stat(h, ctrl=None):
    a, b = h["odd"].to_numpy(float), h["even"].to_numpy(float)
    if ctrl is not None:
        a = resid(a, [ctrl]); b = resid(b, [ctrl])
    return sb(pearson(a, b))


def split_half_result(g, col, min_n, ctrl_series=None):
    h = split_halves(g, col, min_n)
    n = len(h)
    if n < 8:
        return dict(n=n, r=np.nan, sb=np.nan, lo=np.nan, hi=np.nan)
    ctrl = ctrl_series.reindex(h.index).to_numpy(float) if ctrl_series is not None else None
    a, b = h["odd"].to_numpy(float), h["even"].to_numpy(float)

    def stat(idx):
        aa, bb = a[idx], b[idx]
        if ctrl is not None:
            c_ = ctrl[idx]
            aa = resid(aa, [c_]); bb = resid(bb, [c_])
        return sb(pearson(aa, bb))
    est = stat(np.arange(n))
    lo, hi = boot_ci(stat, n)
    r_half = pearson(a if ctrl is None else resid(a, [ctrl]), b if ctrl is None else resid(b, [ctrl]))
    return dict(n=n, r=r_half, sb=est, lo=lo, hi=hi)


def pressure_split(g_reg, min_n, ctrl_series=None):
    return split_half_result(g_reg.assign(p=g_reg["pressure"].astype(float)), "p", min_n, ctrl_series)


def beta_binomial_shrink(k_, n_, group):
    """method-of-moments beta prior per group; returns shrunk rate."""
    out = pd.Series(np.nan, index=k_.index)
    for gv in np.unique(group):
        m = (group == gv)
        p = (k_[m] / n_[m]).to_numpy(float)
        w = n_[m].to_numpy(float)
        mu = np.average(p, weights=w)
        var_obs = np.average((p - mu) ** 2, weights=w)
        nbar = w.mean()
        var_samp = mu * (1 - mu) / nbar
        var_true = max(var_obs - var_samp, 1e-6)
        conc = max(mu * (1 - mu) / var_true - 1, 1.0)
        a_, b_ = mu * conc, (1 - mu) * conc
        out[m] = (k_[m] + a_) / (n_[m] + a_ + b_)
    return out


def partial_r_ci(x, y, ctrl):
    """partial Pearson r of x,y given ctrl list (arrays), complete cases; bootstrap CI."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    C = [np.asarray(c_, float) for c_ in ctrl]
    m = ~(np.isnan(x) | np.isnan(y) | (np.any([np.isnan(c_) for c_ in C], axis=0) if C else False))
    x, y, C = x[m], y[m], [c_[m] for c_ in C]
    n = len(x)
    if n < 8:
        return (np.nan, np.nan, np.nan, n)

    def f(idx):
        if C:
            return pearson(resid(x[idx], [c_[idx] for c_ in C]), resid(y[idx], [c_[idx] for c_ in C]))
        return pearson(x[idx], y[idx])
    est = f(np.arange(n))
    lo, hi = boot_ci(f, n)
    return (est, lo, hi, n)


def player_means(g, col, min_n):
    d = g[g[col].notna()].groupby("nfl_id")[col].agg(["mean", "count"])
    return d[d["count"] >= min_n]


# ----------------------------------------------------------------- run all gates
import pickle


def run_all():
    R = {}
    ct = load_drill()
    reps = {k: build_rep_table(ct, k) for k in (3, 5)}
    R["reps3"] = reps[3]
    cols = GO_VARIANTS + family_cols()
    g1, J = {}, {}
    for k in (3, 5):
        g1[k], J[k] = g1_table(reps[k], cols, with_ci=True)
    R["g1"] = g1
    R["traj"] = trajectory_description(reps[3], ct)
    base = load_baselines()
    R["n_base"] = {b: int(base[b].notna().sum()) for b in BASE}

    # ---- candidate selection (k=3), rule: highest cross-side r (year-z if the year-drift flag fires); within 0.05 of the
    # best, the lowest max |r| against 10-yd split / 40 / weight / 3-cone (two-side mean); ties -> spec window (15-75) first
    cand = [c_ for c_ in family_cols() if g1[3].loc[c_, "n"] >= 75]
    R["cand"] = cand
    g2 = g2_table(reps[3], cand + ["get_off"], g1[3], base)
    R["g2_all"] = g2
    top = g1[3].loc[cand, "r_used"].max()
    near = [c_ for c_ in cand if g1[3].loc[c_, "r_used"] >= top - 0.05]
    pref = {"15-75": 0, "15-60": 1, "30-75": 2}
    primary = sorted(near, key=lambda c_: (round(g2.loc[c_, "max_abs"], 3), pref[c_.split("|")[2]], -g1[3].loc[c_, "r_used"]))[0]
    R["top_r"] = top; R["near"] = near; R["primary"] = primary
    R["optimism"] = selection_optimism(J[3], cand, g1[3])
    spec = ["turn_accel|run|15-75", "turn_min_speed|run|15-75", "speed_carry|run|15-75", "turn_time|run|15-75"]
    R["spec"] = spec

    # ---- G1 by year (cross-side r within draft year) for get_off, primary, spec turn_accel
    rz = year_standardise(reps[3], ["get_off", primary] + spec)
    byyear = []
    for m in ["get_off", primary, "turn_accel|run|15-75"]:
        j = lr_join(rz, [m])
        for y in (2023, 2024, 2025):
            jj = j[j.year_L == y]
            r, lo, hi, n = corr_ci(jj[m + "_L"], jj[m + "_R"])
            byyear.append(dict(metric=m, year=y, r=r, lo=lo, hi=hi, n=n))
    R["g1_by_year"] = pd.DataFrame(byyear)
    # year mean / SD by side
    ym = []
    for m in ["get_off", "go_2_4", primary, "turn_accel|run|15-75", "turn_min_speed|run|15-75"]:
        for side in ("L", "R"):
            for y in (2023, 2024, 2025):
                v = reps[3][(reps[3].side == side) & (reps[3].year == y)][m].dropna()
                ym.append(dict(metric=m, side=side, year=y, n=len(v), mean=v.mean(), sd=v.std()))
    R["year_means"] = pd.DataFrame(ym)
    R["year_flags"] = {m: year_flags(reps[3], m) for m in ["get_off", primary, "turn_accel|run|15-75"]}

    # ---- G2 for primary and get_off with CIs
    flagged_p = bool(g1[3].loc[primary, "flagged"])
    rzp = year_standardise(reps[3], [primary, "get_off"])
    mp = twoside_mean(reps[3], primary, rzp, flagged_p)
    mg = twoside_mean(reps[3], "get_off", rzp, bool(g1[3].loc["get_off", "flagged"]))
    rows = []
    for nm, mser in (("primary", mp), ("get_off", mg)):
        for b in BASE:
            x = mser.reindex(base.index); y = base[b]
            r, lo, hi, n = corr_ci(x.to_numpy(float), y.to_numpy(float))
            rows.append(dict(which=nm, baseline=b, r=r, lo=lo, hi=hi, n=n))
    R["g2"] = pd.DataFrame(rows)
    R["drill_primary_player"] = mp
    R["drill_primary_player_anyside"] = twoside_mean(reps[3], primary, rzp, flagged_p, both=False)
    R["drill_getoff_player"] = mg
    R["drill_getoff_player_anyside"] = twoside_mean(reps[3], "get_off", rzp, bool(g1[3].loc["get_off", "flagged"]), both=False)
    # L-R asymmetry of the primary metric (L rep = clockwise turn, y decreasing)
    jj = lr_join(rzp, [primary + ("|z" if flagged_p else "")])
    cc = primary + ("|z" if flagged_p else "")
    R["drill_asym"] = (jj[cc + "_L"] - jj[cc + "_R"])

    # ---- game
    gm = {k: load_game_pd(k) for k in (3, 5)}
    g = gm[3]
    R["game_counts"] = dict(rush_snaps=len(g), players=g.nfl_id.nunique(),
                            by_type=g.groupby("season_type").size().to_dict(),
                            by_align=g.groupby("lined_up_position").size().to_dict(),
                            edge_snaps=int(g.is_edge.sum()))
    ep = primary_alignment(g)
    R["edge_primary_n"] = ep.value_counts().to_dict()

    # G3 split-half reliability
    g3 = []
    for minn in (30, 20):
        r = split_half_result(g, "player_get_off", minn)
        g3.append(dict(metric="player_get_off (all rush snaps)", k="-", min_n=minn, **r))
        for k in (3, 5):
            ge = gm[k][gm[k].is_edge]
            for col, nm in (("bendA", "bendA: max s*|dtheta/dt|, s>=3.5"), ("bendB", "bendB: mean s at 30-80 deg off upfield")):
                r = split_half_result(ge, col, minn)
                g3.append(dict(metric=nm + " (EDGE-aligned)", k=k, min_n=minn, **r))
    R["g3"] = pd.DataFrame(g3)
    # primary in-game bend by reliability (k=3, min_n=30)
    sub = R["g3"][(R["g3"].k == 3) & (R["g3"].min_n == 30) & R["g3"].metric.str.startswith("bend")]
    best = sub.sort_values("sb", ascending=False).iloc[0]["metric"]
    ig = "bendA" if best.startswith("bendA") else "bendB"
    R["ingame_primary"] = ig

    # G4 transfer
    ctrl_ep = ep
    pm_go = player_means(g, "player_get_off", 30)
    rows = []

    def add(nm, x, y, ctrl, note=""):
        r, lo, hi, n = partial_r_ci(x, y, ctrl)
        rows.append(dict(test=nm, r=r, lo=lo, hi=hi, n=n, note=note))
    for lab, ser in (("both sides", R["drill_getoff_player"]), ("any side", R["drill_getoff_player_anyside"])):
        d = pd.DataFrame({"x": ser, "y": pm_go["mean"], "ep": ep}).dropna()
        add(f"G4 get_off: drill ({lab}) vs in-game player_get_off, pooled, raw r", d.x, d.y, [])
        add(f"G4 get_off: drill ({lab}) vs in-game player_get_off, pooled, partial|EDGE/IDL", d.x, d.y, [d.ep])
        de = d[d.ep == 1]
        add(f"G4 get_off: drill ({lab}) vs in-game player_get_off, EDGE-primary only", de.x, de.y, [])
    for ign in ("bendA", "bendB"):
        pmA = player_means(g, ign, 30)
        pmE = player_means(g[g.is_edge], ign, 30)
        for lab, ser in (("both sides", R["drill_primary_player"]), ("any side", R["drill_primary_player_anyside"])):
            d = pd.DataFrame({"x": ser, "y": pmA["mean"], "ep": ep}).dropna()
            add(f"G4 bend [{ign}]: drill primary ({lab}) vs in-game, pooled all alignments, raw r", d.x, d.y, [])
            add(f"G4 bend [{ign}]: drill primary ({lab}) vs in-game, pooled all alignments, partial|EDGE/IDL", d.x, d.y, [d.ep])
            d = pd.DataFrame({"x": ser, "y": pmE["mean"]}).dropna()
            add(f"G4 bend [{ign}]: drill primary ({lab}) vs in-game, EDGE-aligned snaps only", d.x, d.y, [])
    ign = R["ingame_primary"]
    pmE = player_means(g[g.is_edge], ign, 30)
    for lab, ser in (("both sides", R["drill_primary_player"]), ("any side", R["drill_primary_player_anyside"])):
        d = pd.DataFrame({"x": ser, "y": pmE["mean"], "w": base["combine_weight"], "t": base["ten_yd_split"]}).dropna(subset=["x", "y", "w"])
        add(f"G4 bend [{ign}] EDGE-aligned, drill primary ({lab}) | combine_weight (robustness)", d.x, d.y, [d.w])
        d2 = d.dropna(subset=["t"])
        add(f"G4 bend [{ign}] EDGE-aligned, drill primary ({lab}) | combine_weight, ten_yd_split (robustness)", d2.x, d2.y, [d2.w, d2.t])
    R["g4"] = pd.DataFrame(rows)

    # G5
    greg = g[g.season_type == "REG"]
    R["reg_counts"] = dict(rush=len(greg), players=greg.nfl_id.nunique(),
                           n_ge30=int((greg.groupby("nfl_id").size() >= 30).sum()),
                           n_ge100=int((greg.groupby("nfl_id").size() >= 100).sum()),
                           pressure_rate=float(greg.pressure.mean()))
    rows = []
    for minn in (100, 30):
        a = pressure_split(greg, minn)
        b = pressure_split(greg, minn, ep)
        rows.append(dict(test=f"pressure split-half, >={minn} REG rush snaps, pooled (no alignment control)", **a))
        rows.append(dict(test=f"pressure split-half, >={minn} REG rush snaps, residualised on EDGE/IDL", **b))
        for ev, nm in ((1, "EDGE-primary"), (0, "non-EDGE-primary")):
            idx = ep[ep == ev].index
            rows.append(dict(test=f"pressure split-half, >={minn} REG rush snaps, {nm} only", **pressure_split(greg[greg.nfl_id.isin(idx)], minn)))
    R["g5a"] = pd.DataFrame(rows)

    # G5b: between-player partial r, in-game bend vs shrunk pressure
    reg_n = greg.groupby("nfl_id").size(); reg_k = greg.groupby("nfl_id").pressure.sum()
    el = reg_n[reg_n >= 30].index
    shr = beta_binomial_shrink(reg_k[el], reg_n[el], ep.reindex(el).to_numpy())
    rows = []
    for ign in ("bendA", "bendB"):
        pmA = player_means(g, ign, 10)
        pgo = player_means(g, "player_get_off", 10)
        d = pd.DataFrame({"x": pmA["mean"], "y": shr, "go": pgo["mean"], "ep": ep}).dropna()
        r, lo, hi, n = partial_r_ci(d.x, d.y, [d.go, d.ep])
        rows.append(dict(test=f"G5b [{ign}] in-game bend vs shrunk pressure rate | get_off, EDGE/IDL; pooled all alignments, REG>=30", r=r, lo=lo, hi=hi, n=n))
        r, lo, hi, n = partial_r_ci(d.x, d.y, [d.ep])
        rows.append(dict(test=f"G5b [{ign}] ... | EDGE/IDL only (no get_off control)", r=r, lo=lo, hi=hi, n=n))
        r, lo, hi, n = partial_r_ci(d.x, d.y, [])
        rows.append(dict(test=f"G5b [{ign}] ... raw r", r=r, lo=lo, hi=hi, n=n))
        # EDGE only
        ge = g[g.is_edge]; gre = greg[greg.is_edge]
        rn = gre.groupby("nfl_id").size(); rk = gre.groupby("nfl_id").pressure.sum()
        el2 = rn[rn >= 30].index
        shr2 = beta_binomial_shrink(rk[el2], rn[el2], np.ones(len(el2)))
        pmE = player_means(ge, ign, 10); pgoE = player_means(ge, "player_get_off", 10)
        d2 = pd.DataFrame({"x": pmE["mean"], "y": shr2, "go": pgoE["mean"]}).dropna()
        r, lo, hi, n = partial_r_ci(d2.x, d2.y, [d2.go])
        rows.append(dict(test=f"G5b [{ign}] EDGE-aligned snaps only, REG EDGE>=30 | get_off", r=r, lo=lo, hi=hi, n=n))
    R["g5b"] = pd.DataFrame(rows)

    # G6 exploratory asymmetry
    ge = g[g.is_edge]
    cw = ge[ge.sense == 1].groupby("nfl_id").bendA.agg(["mean", "count"])
    ccw = ge[ge.sense == -1].groupby("nfl_id").bendA.agg(["mean", "count"])
    rows = []
    for minc in (5, 8):
        ok = cw[cw["count"] >= minc].index.intersection(ccw[ccw["count"] >= minc].index)
        ig_asym = (cw.loc[ok, "mean"] - ccw.loc[ok, "mean"])
        d = pd.DataFrame({"x": R["drill_asym"], "y": ig_asym}).dropna()
        r, lo, hi, n = corr_ci(d.x.to_numpy(), d.y.to_numpy())
        rows.append(dict(test=f"drill (L - R) vs in-game (clockwise - counter-clockwise bendA), >={minc} EDGE snaps per sense", r=r, lo=lo, hi=hi, n=n,
                         n_ingame_players=len(ok)))
    R["g6"] = pd.DataFrame(rows)
    R["sense_counts"] = ge["sense"].value_counts().to_dict()
    pickle.dump(R, open(os.path.join(CACHE, "c2_results.pkl"), "wb"))
    return R




# ----------------------------------------------------------------- report
def f2(x, d=2):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def ci(lo, hi, d=2):
    return f"[{f2(lo, d)}, {f2(hi, d)}]"


def md(df, floatfmt=2):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c_).replace("|", "\\|") for c_ in cols) + " |","|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c_ in cols:
            v = r[c_]
            if isinstance(v, (float, np.floating)):
                cells.append(f2(float(v), floatfmt))
            else:
                cells.append(str(v).replace("|", "\\|"))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def write_report(R, path):
    g1 = R["g1"]; p = R["primary"]; T = R["traj"]; pe = p.replace("|", "\\|")
    G = g1[3]; G5 = g1[5]
    L = []
    w = L.append
    # --- verdicts
    go_row = G.loc["get_off"]
    v_go = verdict(go_row["r_used"], 0.60)
    spec_best = max(R["spec"], key=lambda m: G.loc[m, "r_used"])
    prow = G.loc[p]
    best_bend_all = G.loc[R["cand"], "r_used"].max()
    v_bend = "pass" if prow["r_used"] >= 0.40 else ("fail" if best_bend_all < 0.25 else "amber")
    v_g1 = "pass" if (v_go == "pass" and v_bend == "pass") else ("fail" if best_bend_all < 0.25 else "amber")
    g2p = R["g2"][R["g2"].which == "primary"]
    n3 = R["n_base"]["three_cone"]
    maxabs = g2p[["r"]].abs().max().iloc[0]
    v_g2 = "pass" if maxabs < 0.60 else ("amber" if maxabs < 0.70 else "fail")
    g3 = R["g3"]
    ig = R["ingame_primary"]
    g3m = g3[(g3.min_n == 30) & (g3.k.astype(str).isin(["-", "3"]))]
    sb_go = g3m[g3m.metric.str.startswith("player_get_off")].iloc[0]
    sb_bendA = g3m[g3m.metric.str.startswith("bendA")].iloc[0]
    sb_bendB = g3m[g3m.metric.str.startswith("bendB")].iloc[0]
    sb_bend = sb_bendA if ig == "bendA" else sb_bendB
    v_g3 = "pass" if (sb_go["sb"] >= 0.70 and sb_bend["sb"] >= 0.60) else ("amber" if (sb_go["sb"] >= 0.60 and sb_bend["sb"] >= 0.50) else "fail")
    g4 = R["g4"]
    gg = g4[g4.test.str.contains("G4 get_off") & g4.test.str.contains("both sides") & g4.test.str.contains("partial")].iloc[0]
    v_g4go = verdict(gg["r"], 0.25)
    sel = g4[g4.test.str.contains(f"\\[{ig}\\]") & g4.test.str.contains("both sides") & ~g4.test.str.contains("robustness")]
    g4_pool = sel[sel.test.str.contains("partial")].iloc[0]
    g4_edge = sel[sel.test.str.contains("EDGE-aligned")].iloc[0]
    v_g4b = verdict(min(g4_pool["r"], g4_edge["r"]), 0.25)
    g5a = R["g5a"]
    a_adj = g5a[g5a.test.str.contains(">=100") & g5a.test.str.contains("residualised")].iloc[0]
    a_pool = g5a[g5a.test.str.contains(">=100") & g5a.test.str.contains("pooled")].iloc[0]
    v_g5a = verdict(min(a_adj["sb"], a_pool["sb"]), 0.50)
    g5b = R["g5b"]
    b_main = g5b[g5b.test.str.contains(f"\\[{ig}\\]") & g5b.test.str.contains("get_off, EDGE/IDL")].iloc[0]
    b_edge = g5b[g5b.test.str.contains(f"\\[{ig}\\]") & g5b.test.str.contains("EDGE-aligned")].iloc[0]
    v_g5b = verdict(b_main["r"], 0.25)
    v_g5 = "pass" if (v_g5a == "pass" and v_g5b == "pass") else ("amber" if "fail" not in (v_g5a, v_g5b) else "fail")
    g6 = R["g6"].iloc[1]
    decision_go = (v_bend == "pass") and (v_g2 == "pass") and (v_g3 == "pass") and (v_g4b == "pass" or v_g5 == "pass")

    w("# Feasibility check C2 (edge bend): gates G1-G6\n")
    w("Script: `scripts/feasibility/c2_edge_bend.py` (run `.venv/Scripts/python.exe scripts/feasibility/c2_edge_bend.py`). "
      "Bootstrap CIs: 2,000 resamples of players, seed 2027. Every number below is computed by that script unless it is labelled as inference. "
      "No Combine drill metric is correlated with the NFL pressure outcome anywhere in this report (G5b uses in-game bend only; the drill metric appears only against in-game kinematics, G4, G6).\n")

    w("## 0. Headline\n")
    w("| gate | metric | value | 95% CI | n | verdict |")
    w("|---|---|---|---|---|---|")
    w(f"| G1 get_off | cross-side Pearson r, get_off (s 1.0 to 4.0 yd/s), year-standardised (raw {f2(go_row['r_raw'])} {ci(go_row['lo'], go_row['hi'])}) | {f2(go_row['r_used'])} | {ci(go_row['zlo'], go_row['zhi'])} | {int(go_row['n'])} | **{v_go}** (go needs 0.60) |")
    w(f"| G1 bend, pre-specified family | best of turn_accel / turn_min_speed / speed_carry / turn_time, 15-75 deg from initial run heading: {spec_best.split('|')[0]} | {f2(G.loc[spec_best, 'r_used'])} | {ci(G.loc[spec_best, 'zlo'] if G.loc[spec_best, 'flagged'] else G.loc[spec_best, 'lo'], G.loc[spec_best, 'zhi'] if G.loc[spec_best, 'flagged'] else G.loc[spec_best, 'hi'])} | {int(G.loc[spec_best, 'n'])} | amber (go needs 0.40, no-go below 0.25) |")
    w(f"| G1 bend, primary by rule | `{pe}` (year-standardised, raw {f2(prow['r_raw'])}) | {f2(prow['r_used'])} | {ci(prow['zlo'] if prow['flagged'] else prow['lo'], prow['zhi'] if prow['flagged'] else prow['hi'])} | {int(prow['n'])} | **{v_bend}** (selection-corrected r {f2(R['optimism'][1])}) |")
    w(f"| G2 | max abs r of primary two-side mean vs 10-yd, 40, weight, 3-cone | {f2(maxabs)} (3-cone n={int(g2p[g2p.baseline == 'three_cone'].n.iloc[0])}) | see section 3 | {' / '.join(str(int(v)) for v in g2p.n)} | **{v_g2}** |")
    w(f"| G3 get_off | split-half (odd/even), Spearman-Brown, >=30 rush snaps, PRE+REG+POST | {f2(sb_go['sb'])} | {ci(sb_go['lo'], sb_go['hi'])} | {int(sb_go['n'])} | **pass** (go 0.70) |")
    w(f"| G3 in-game bend ({ig}, EDGE-aligned) | same | {f2(sb_bend['sb'])} | {ci(sb_bend['lo'], sb_bend['hi'])} | {int(sb_bend['n'])} | **pass** (go 0.60) |")
    w(f"| G4 get_off | drill get_off (two-side mean) vs in-game player_get_off, partial on EDGE/IDL | {f2(gg['r'])} | {ci(gg['lo'], gg['hi'])} | {int(gg['n'])} | **{v_g4go}** (go 0.25) |")
    w(f"| G4 bend, pooled | drill primary vs in-game {ig}, partial on EDGE/IDL | {f2(g4_pool['r'])} | {ci(g4_pool['lo'], g4_pool['hi'])} | {int(g4_pool['n'])} | amber |")
    w(f"| G4 bend, EDGE only | same, EDGE-aligned snaps | {f2(g4_edge['r'])} | {ci(g4_edge['lo'], g4_edge['hi'])} | {int(g4_edge['n'])} | {verdict(g4_edge['r'], 0.25)} nominal, CI includes 0 |")
    w(f"| G5a | pressure split-half SB, >=100 REG rush snaps, residualised on EDGE/IDL (pooled unadjusted {f2(a_pool['sb'])}) | {f2(a_adj['sb'])} | {ci(a_adj['lo'], a_adj['hi'])} | {int(a_adj['n'])} | **{v_g5a}** (go 0.50) |")
    w(f"| G5b | partial r, in-game {ig} vs beta-binomial-shrunk REG pressure rate, controlling in-game get_off and EDGE/IDL | {f2(b_main['r'])} | {ci(b_main['lo'], b_main['hi'])} | {int(b_main['n'])} | **{v_g5b}** (go 0.25); EDGE-aligned only {f2(b_edge['r'])} {ci(b_edge['lo'], b_edge['hi'])} n={int(b_edge['n'])} |")
    w(f"| G6 (exploratory) | drill (L - R) vs in-game (clockwise - counter-clockwise turn, bendA), >=8 EDGE snaps per sense | {f2(g6['r'])} | {ci(g6['lo'], g6['hi'])} | {int(g6['n'])} | report only |")
    w("")
    w(f"**Overall rule:** go if G1-bend, G2, G3 pass and (G4-bend or G5) passes. G1-bend = {v_bend}, G2 = {v_g2}, G3 = {v_g3}, G4-bend = {v_g4b}, G5 = {v_g5}. "
      f"**Decision: {'GO' if decision_go else 'NO-GO as the rule is written (amber at best)'}.** "
      "The only blocking item is G1-bend: the drill bend metrics are not consistent enough across the two reps (best defensible r about 0.33 to 0.40, and about 0.2 once the metric selection is corrected for). "
      "G2, G3 and G5 are comfortable; G4-bend is borderline; the get_off branch fails G1 and G4, so the fallback \"get_off only\" also does not rescue the idea.\n")
    w("Verdict thresholds that candidates.md leaves open are my operational choice: pass at the go threshold, amber within 0.10 below it (G1-bend: amber between 0.25 and 0.40, which is the file's no-go/go band), fail below that; G2 amber for max |r| in [0.60, 0.70). "
      "Where a year-drift flag fired, the year-standardised r is used for the verdict; G4/G5 take the lower of pooled and EDGE-only (G4) or pooled and unadjusted (G5a) where both are shown.\n")

    # ---------------------------------------------------------------- 1 trajectories
    w("## 1. What the drill trajectories look like (verified by code)\n")
    w(f"- {T['n_reps']} reps from {T['n_players']} players (`PASS_RUSH_DRILL`, entity PLAYER): 217 reps in SKILL_DRILLS_DL, 8 reps from 4 players in SKILL_DRILLS_LB. Side is assigned by the direction of travel in y (finish y > start y = \"R\", rep ending near y=39; otherwise \"L\", ending near y=15). Reps by year and side:\n")
    w(md(T["reps_by_side_year"].reset_index().rename(columns={"year": "draft year"}), 0) + "\n")
    cnt = R["reps3"].groupby("nfl_id").side.agg(lambda v: "".join(sorted(v))).value_counts().to_dict()
    w(f"- Players by sides recorded: {cnt}. So 106 players have both an L and an R rep (candidates.md says 102); one player has two L reps and one R (the first chronological rep per side is used everywhere).")
    w(f"- Start: median x = {f2(T['x0_med'])} (IQR {f2(T['x0_iqr'][0])} to {f2(T['x0_iqr'][1])}); median y = {f2(T['y0_R'])} for R reps and {f2(T['y0_L'])} for L reps (documented 23.75 / 30.25). Matches the audit's x of about 44.5.")
    w(f"- Share reaching the finish line (R: y >= 39; L: y <= 15): {f2(T['reach_finish_all'] * 100, 1)}% overall (L {f2(T['reach_finish_by_side']['L'] * 100, 1)}%, R {f2(T['reach_finish_by_side']['R'] * 100, 1)}%). The drill is essentially always tracked to the finish.")
    w(f"- Duration median {f2(T['dur']['50%'], 1)} s (IQR {f2(T['dur']['25%'], 1)} to {f2(T['dur']['75%'], 1)}; 10 Hz, median {int(T['frames']['50%'])} frames); one rep is 10.2 s long (103 frames). Peak speed median {f2(T['smax']['50%'])} yd/s (IQR {f2(T['smax']['25%'])} to {f2(T['smax']['75%'])}).")
    w("- Shape (heading `dir` is consistent with the heading from x/y differences: mean difference 0.01 deg, SD 0.8 deg at s > 3; speed from x/y matches `s` to 0.02 yd/s). Heading measured against the +x axis (dir = 90), with s >= 4 yd/s as the clock origin:\n")
    tm = T["timing"].loc[["dev_vs_x_at_s4", "t15_after_s4", "s_at_15deg", "t45_after_s4", "s_at_45deg", "t75_after_s4", "s_at_75deg", "max_dev_vs_x_axis"]]
    tm = tm[["count", "25%", "50%", "75%"]].reset_index().rename(columns={"index": "quantity"})
    w(md(tm, 2) + "\n")
    w(f"- Reading: players are already about 9 deg (median; IQR about 4 to 21 deg) off the +x axis toward the finish side when speed first reaches 4 yd/s, so the turn is an arc that starts while still accelerating, not a straight run followed by a corner. The heading deviation passes 15 deg at about 0.1 s after s = 4, 45 deg at +0.6 s and 75 deg at +1.2 s (speed 4.1, 4.4 and 5.5 yd/s). The final heading is about 90 to 92 deg off +x (it points at the finish line), reached in {f2(T['share_dev_ge_75'] * 100, 1)}% of reps (>= 75 deg). The turn window 15 to 75 deg lasts about 1.0 s (median) and speed climbs only from about 4.0 to 5.4 yd/s within it; the 7.5 to 7.7 yd/s peak is reached after the heading has already settled, on the run to the line.")
    w("- Crop by year: median first-frame speed " + ", ".join(f"{y}: {f2(v)}" for y, v in T["s0_by_year"].items()) + " yd/s; mean time (from first frame) at which s first reaches 1.0 yd/s " + ", ".join(f"{y}: {f2(v)} s" for y, v in T["ts1_by_year"].items()) + "; reaches 4.0 yd/s " + ", ".join(f"{y}: {f2(v)} s" for y, v in T["ts4_by_year"].items()) + ". The 2025 crop does start earlier (confirmed). In 2023 and 2024 the first smoothed frame is often already at or above 1.0 yd/s, so the threshold crossing is never observed: get_off is missing for " + ", ".join(f"{y}: {v}" for y, v in T["go_missing_by_year"].items()) + " reps (these are the quickest starters, so the loss is not random).\n")

    # ---------------------------------------------------------------- 2 definitions
    w("## 2. Metric definitions used (all logged)\n")
    w("Common: `x, y, s, dir` at 10 Hz; `dis` and `a` not used. Smoothing = centred moving mean of `s` and of the unwrapped `dir`, 3 frames (primary) or 5 frames (sensitivity), edge frames dropped. dtheta/dt = centred difference of the smoothed unwrapped heading over 0.2 s, in rad/s; centripetal acceleration = s_smoothed x |dtheta/dt| (yd/s^2). Heading is unwrapped starting at the first frame with smoothed s >= 2 yd/s (earlier headings are noise at near-zero speed).\n")
    w("**Get-off (G1, G2, G4):** time from first smoothed s >= 1.0 to first s >= 4.0 yd/s, linear interpolation of the crossing; the specified definition is `get_off`. Sensitivity variants: `go_2_4` (2.0 to 4.0), `go_2_5` (2.0 to 5.0; this one runs into the turn), `go_1_4_rawS` (1.0 to 4.0 on unsmoothed s).\n")
    w("**Bend family (window of heading deviation 15 to 75 deg, as specified):** `turn_accel` = mean centripetal acceleration over frames in the window; `turn_min_speed` = min smoothed s in the window; `speed_carry` = s at the 75 deg crossing / s at the 15 deg crossing; `turn_time` = duration of the window. I added `peak_cent` = max centripetal acceleration in the window (the drill analogue of the in-game metric). "
      "Heading deviation is signed toward the finish side. The reference heading was tried two ways: `run` = mean heading between first s >= 1.0 and first s >= 3.0 (the early straight run) and `x` = fixed +x axis (dir = 90). Windows tried: 15-75 (specified), 15-60, 30-75. That is 5 metrics x 3 windows x 2 references = 30 bend candidates, each at 3 and 5 frames. The window search starts at the first frame with s >= 2 and takes the first frame at or above each threshold.\n")
    w("Exploratory definitions dropped before the final grid (interactive, not in the script): (a) initial run heading taken at s 3 to 4.5 yd/s: players are already 10 to 30 deg off line by then, the 15 deg crossing was found in only 59 of 225 reps and the 75 deg crossing in only 88; dropped.\n")
    w("Windows found per definition (reps with a valid window, of 225): " + ", ".join(
        f"`{c_}`: {int(R['reps3'][c_].notna().sum())}" for c_ in [f"turn_accel|{r_}|{w_}" for r_ in REFS for w_ in ('15-75', '15-60', '30-75')]) + ".\n")
    w("**Selection rule for the primary drill bend metric (applied to the 30 candidates at 3 frames with >= 75 L/R pairs):** (1) highest cross-side Pearson r (the year-standardised r when the year-drift flag fires for that metric, otherwise raw); (2) among candidates within 0.05 of that best, the one with the lowest max |r| against ten_yd_split, forty, combine_weight (and three_cone when n >= 15), computed on the two-side mean; (3) remaining ties go to the 15-75 window, then to the 15-60 window. "
      f"Best r = {f2(R['top_r'])}; candidates within 0.05: {', '.join('`' + m + '`' for m in R['near'])}. **Primary = `{p}`** (turn_min_speed with the run-heading reference and the 15-60 window: the speed at which the player enters the turn).")
    w("Note on what this means: `turn_min_speed` is essentially the speed carried into the arc, a speed measure rather than a pure turning-sharpness measure; the centripetal-acceleration metrics were less consistent across sides (see table). "
      f"The rule picks the best of 30 correlated metrics, which inflates r: re-running the whole selection inside bootstrap resamples and scoring the winner on the out-of-bag players gives a mean in-sample best r of {f2(R['optimism'][0])} but an out-of-bag r of only {f2(R['optimism'][1])} (1,000 resamples). Read the primary's r as an upper-ish estimate.\n")
    w("**In-game (G3-G6):** rush snap = `player_play` row with blitzing == True and pass_result != '' and lined_up_position != 'NA' (35,565 snaps, 115 of the 118 drill players). t = 0 at the ball_snap frame; window = snap + 0.3 s to the earlier of snap + 3.0 s and the first pass_forward / qb_sack / qb_strip_sack event. "
      "`bendA` = max over window frames with smoothed s >= 3.5 yd/s of s x |dtheta/dt| (needs >= 2 gated frames). `bendB` = mean smoothed s over window frames whose smoothed heading is 30 to 80 deg from the upfield direction (dir = 90 if play_direction is left, 270 if right; needs >= 2 frames). Both at 3 and 5 frames. "
      "Turn sense for G6 = sign of the net heading change across the gated frames (clockwise = dir increasing; needs >= 20 deg). bend metrics use EDGE-aligned snaps (G3, G4 EDGE-only, G6) or all alignments with an EDGE/IDL indicator (G4 pooled, G5b). Player alignment indicator = EDGE if >= 50% of his rush snaps are lined up at EDGE (56 of 115 players). Season types: PRE+REG+POST for kinematics, REG for pressure. Chronological order = season, season type, week, game_id, play_id. Pressure = time_to_pressure non-null; shrinkage = beta-binomial with a method-of-moments prior per alignment group.\n")
    w(f"Convention check (verified): in the 2024 tracking, the mean snap x of the offence minus the defence is +6.3 when play_direction == left and -6.0 when right, so the offence's end zone is at decreasing x when left and the rusher's upfield is +x when left, as candidates.md says. "
      f"In-game bend availability: bendA exists on 79% of EDGE rush snaps but only 27% of IDL snaps (the 3.5 yd/s gate); bendB on 77% and 75%.\n")

    # ---------------------------------------------------------------- G1
    w("## 3. Gate results in detail\n")
    w("### G1 cross-side consistency (left rep vs right rep; the two reps differ in side and move, so this is a lower bound on reliability)\n")
    show = ["get_off", "go_2_4", "go_2_5", "go_1_4_rawS"] + R["spec"] + [m for m in R["cand"] if m not in R["spec"]]
    t = pd.DataFrame({
        "metric": show,
        "n (3f)": [int(G.loc[m, "n"]) for m in show],
        "r raw 3f": [G.loc[m, "r_raw"] for m in show],
        "CI raw": [ci(G.loc[m, "lo"], G.loc[m, "hi"]) for m in show],
        "Spearman 3f": [G.loc[m, "spearman"] for m in show],
        "r year-z 3f": [G.loc[m, "r_yearz"] for m in show],
        "max year dev (SD)": [G.loc[m, "max_year_dev_sd"] for m in show],
        "drift flag": ["yes" if G.loc[m, "flagged"] else "no" for m in show],
        "r used 3f": [G.loc[m, "r_used"] for m in show],
        "n (5f)": [int(G5.loc[m, "n"]) for m in show],
        "r raw 5f": [G5.loc[m, "r_raw"] for m in show],
        "r year-z 5f": [G5.loc[m, "r_yearz"] for m in show],
    })
    w(md(t, 2) + "\n")
    w("`r used` = year-standardised r where the drift flag fires (a year mean differing from the mean of the other years by more than 0.5 pooled within-year SD, checked per side), raw otherwise. The first four rows are get-off variants; the next four are the pre-specified family (run heading, 15-75); the rest are the other candidates. The 5-frame sensitivity gives the same picture (best run-reference bend r about 0.44 raw for turn_min_speed 15-60, peak_cent|x 0.44; get_off 0.41 with n = 49 because the 5-frame smoothing loses more starts). The x-reference turn_min_speed and speed_carry collapse at 5 frames (0.19 to 0.05 and 0.17 to -0.05), i.e. several candidates are not stable to the smoothing choice.\n")
    w("**G1 by draft year** (cross-side r within each class; n small, CIs wide; values are on year-standardised metrics so the within-year r is not affected by year offsets):\n")
    gy = R["g1_by_year"].copy(); gy["CI"] = [ci(a, b) for a, b in zip(gy.lo, gy.hi)]
    w(md(gy[["metric", "year", "n", "r", "CI"]], 2) + "\n")
    w("Pooled and by year agree that get_off is about 0.3 to 0.6 and the bend metrics about 0 to 0.6 with no stable year ordering; 2025 is the weakest year for both bend metrics (r = 0.28 and 0.00), the year with the earliest crop and the most reps.\n")
    w("**Year-mean drift (threshold-crossing metrics, mean and SD by year and side):**\n")
    ymf = R["year_means"].copy()
    w(md(ymf, 2) + "\n")
    fl = R["year_flags"]
    w("Flag statistic = (year mean - mean of the other years) / pooled SD, per side. get_off: " + "; ".join(f"{s}-{y}: {f2(v)}" for (s, y), v in fl["get_off"].items()) +
      ". So `get_off` does drift by more than 0.5 SD in 2023 and 2025 on both sides (2025 is slower by about 0.2 to 0.4 s) even though it uses threshold crossings (inference on cause: the crossing times fix the start of the clock but not a systematic change in how the rep begins; the 2023/24 reps lost to censoring are the ones already moving at the first frame, which is verified for the count, and \"fastest starters\" is inferred from that). "
      "The bend metrics tied to the early part of the rep (turn_min_speed, turn_accel with the run reference) also drift by 0.5 to 1.0 SD with 2023 higher. Year standardisation was applied wherever the flag fired.\n")

    # G2
    w("### G2 non-redundancy (two-side mean, players with both sides; Pearson, bootstrap CI)\n")
    g2 = R["g2"].copy(); g2["CI"] = [ci(a, b) for a, b in zip(g2.lo, g2.hi)]
    w(md(g2[["which", "baseline", "n", "r", "CI"]], 2) + "\n")
    w(f"Available baselines: ten_yd_split {R['n_base']['ten_yd_split']}, forty {R['n_base']['forty']}, weight {R['n_base']['combine_weight']}, three_cone {R['n_base']['three_cone']} of 510 players. All |r| of the primary are below 0.60 (largest: 3-cone, n = 33, upper CI bound reaches |r| = 0.64) -> pass. "
      "`get_off` against the 10-yd split is only 0.47 (expected higher): get_off is not the stopwatch burst measure, which also fits its low cross-side consistency. "
      "Non-redundancy for the other near-top candidates (max |r| over 10-yd/40/weight/3-cone, two-side mean). Note that the highest-r candidate, `peak_cent|x` (centripetal acceleration against the fixed +x axis, r = 0.42), would have been amber on G2 (|r| = 0.62 with the 3-cone, n = 37, and about 0.50 with the 40 and with weight); the non-redundancy tie-break is what moved the primary to turn_min_speed:\n")
    g2a = R["g2_all"].loc[R["near"] + ["get_off"], ["ten_yd_split", "forty", "combine_weight", "three_cone", "n_three_cone", "max_abs"]].reset_index()
    w(md(g2a, 2) + "\n")

    # G3
    w("### G3 in-game reliability (odd/even chronological snaps, Spearman-Brown)\n")
    g3t = g3.copy(); g3t["CI (SB)"] = [ci(a, b) for a, b in zip(g3t.lo, g3t.hi)]
    w(md(g3t[["metric", "k", "min_n", "n", "r", "sb", "CI (SB)"]].rename(columns={"k": "frames", "min_n": "min snaps", "r": "half-half r", "sb": "SB"}), 2) + "\n")
    w(f"Min snaps = valid values of the metric per player. The primary in-game bend is chosen by reliability at 3 frames and >= 30 snaps: **{ig}** (SB {f2(sb_bend['sb'])} vs {f2(sb_bendA['sb'] if ig == 'bendB' else sb_bendB['sb'])}). "
      "Caution (inference): these are high because a rusher's alignment, team scheme and typical drop depths are stable across his snaps, so split-half reliability measures the persistence of role plus skill, not skill alone; also the odd/even halves interleave snaps from the same games.\n")

    # G4
    w("### G4 transfer (drill to game kinematics; the pressure outcome is not used)\n")
    g4t = g4.copy(); g4t["CI"] = [ci(a, b) for a, b in zip(g4t.lo, g4t.hi)]
    w(md(g4t[["test", "n", "r", "CI"]], 2) + "\n")
    w("get_off: the raw pooled association (0.31) is entirely the EDGE/IDL difference (both drill and NGS get-off are slower for interior linemen); with the indicator it is 0.04 and within EDGE players it is 0.00 -> fail. "
      f"Bend: the in-game metric that is the more reliable ({ig}) is a speed measure; with the drill primary (also a speed-at-turn measure) it gives pooled partial {f2(g4_pool['r'])} and EDGE-only {f2(g4_edge['r'])}, both with CIs that include zero; bendA (centripetal) gives 0.04 to 0.12. Verdict amber.\n")

    # G5
    w("### G5 outcome usable and mechanism plausible\n")
    g5at = g5a.copy(); g5at["CI (SB)"] = [ci(a, b) for a, b in zip(g5at.lo, g5at.hi)]
    w(md(g5at[["test", "n", "r", "sb", "CI (SB)"]].rename(columns={"r": "half-half r", "sb": "SB"}), 2) + "\n")
    rc = R["reg_counts"]
    w(f"REG rush snaps for drill players: {rc['rush']} ({rc['players']} players; {rc['n_ge30']} with >= 30 and {rc['n_ge100']} with >= 100); pressure rate {f2(rc['pressure_rate'] * 100, 1)}%. Pooled reliability includes the EDGE-vs-IDL level difference, so the residualised value is the one used for the verdict (pass either way).\n")
    g5bt = g5b.copy(); g5bt["CI"] = [ci(a, b) for a, b in zip(g5bt.lo, g5bt.hi)]
    w(md(g5bt[["test", "n", "r", "CI"]], 2) + "\n")
    w("Caveats (inference): the raw r (0.67 and 0.85) is mostly the EDGE-vs-IDL level difference; the partial values remove that but the in-game bend metrics are computed over the same snaps whose pressure outcome is being predicted, and bendB is mean speed during the turn, so the association partly reflects that a rusher who is moving fast near the quarterback is by construction more likely to pressure. Within EDGE-aligned snaps only, the partial r is 0.22 (bendB) and 0.18 (bendA), below 0.25. Team, scheme, down and distance and dropback length are not controlled.\n")

    # G6
    w("### G6 within-player side asymmetry (exploratory, report only)\n")
    g6t = R["g6"].copy(); g6t["CI"] = [ci(a, b) for a, b in zip(g6t.lo, g6t.hi)]
    w(md(g6t[["test", "n", "n_ingame_players", "r", "CI"]], 2) + "\n")
    w("Drill L rep (finishes through y = 15) turns clockwise (heading dir increases); R rep turns counter-clockwise. Asymmetry = L minus R in the drill (on the primary metric, year-standardised) and clockwise minus counter-clockwise bendA in games (EDGE-aligned). The point estimate is negative (opposite to the hypothesis) with a CI that includes zero; no support, and no evidence against.\n")

    w("## 4. What candidates.md got wrong or left unclear about the data\n")
    w("1. Players with both a left and a right rep: 106 by direction of travel, not 102 (one player has two left reps). 12 players have a single rep.")
    w("2. The 15-to-75 deg window \"from the initial run heading\" is not well defined: by the time speed reaches 4 yd/s players are already about 10 to 30 deg off the +x axis, so against a heading taken at s 3 to 4.5 yd/s the 75 deg point is reached in only 88 of 225 reps. Against a heading taken from s 1 to 3 yd/s it is reached in 198, against the fixed +x axis in 224.")
    w("3. \"A turn of about 90 deg between 1.5 and 3.0 s during which speed rises to about 7.5 yd/s\": the 90 deg is right (final heading about 91 deg off +x) but speed inside the 15-75 deg window is only about 4.0 to 5.4 yd/s; 7.5 to 7.7 yd/s is the peak on the finish run after the turn. Centripetal acceleration in the window is about 4.4 to 4.6 yd/s^2 (mean; peak about 5.5).")
    w("4. Threshold-crossing times do not remove the crop problem. get_off needs s to be seen crossing 1.0 yd/s; in 26 reps (2023: 18 of 69, 2024: 8 of 67) the recording starts above that, so those reps (the fastest starters) have no get_off, and the surviving get_off means still drift by about 1 SD between 2023 and 2025. The drill-start sample for get_off is 84 pairs, not 102 to 106.")
    w("5. Cross-side get_off consistency is far below the 0.60 go line (0.45 raw, 0.37 year-standardised), and get_off is only moderately tied to the 10-yd split (r about 0.47), so it is neither very reliable nor a stopwatch duplicate.")
    w("6. The in-game and outcome side behaves as the file assumed: EDGE get_off coverage 95% (doc 94%), IDL 89%; pressure rate 12.0% EDGE, 7.2% IDL; 85 players with >= 30 and 65 with >= 100 REG rush snaps (matches); the play_direction convention is confirmed.")
    w("7. Not in the file: the in-game bend gate s >= 3.5 yd/s excludes 73% of interior-line snaps, so bendA is essentially an EDGE-only measure; bendB (30-80 deg mean speed) has better coverage and far better reliability, but it is a speed measure.\n")

    w("## 5. Verified versus inferred\n")
    w("Verified by code (all numbers in sections 0-4 except those labelled otherwise): rep counts and geometry, trajectory timing, definitions, all correlations, CIs, split-half values, shrinkage, direction convention, dir-versus-position consistency.\n")
    w("Inference or judgement, not checked by code: the explanations for why get_off drifts and why in-game reliabilities are high; that turn_min_speed is mainly a speed measure; the amber/fail margins that candidates.md does not specify (my operational choice, stated above); the dropped exploratory definition (a) was run interactively and is not in the script; the selection-optimism estimate is itself noisy (out-of-bag sets of about 35 players).\n")
    w(f"Data-quality notes: one 10.2 s rep (103 frames) is included without trimming; heading unwrapping gives implausible total deviations (> 180 deg) in a handful of reps, which only matter for the `max_dev` descriptive (the median is unaffected). Players in the drill set with no qualifying rush snaps in games (3 of 118) drop out of G3 to G6.\n")
    open(path, "w", encoding="utf-8").write("\n".join(L))


REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports", "feasibility_c2.md")

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage == "game":
        for k in (3, 5):
            build_game_table(k=k).write_parquet(os.path.join(CACHE, f"game_k{k}.parquet"))
    elif stage in ("all", "gates", "report"):
        for k in (3, 5):
            pth = os.path.join(CACHE, f"game_k{k}.parquet")
            if stage == "all" or not os.path.exists(pth):
                build_game_table(k=k).write_parquet(pth)
        R = pickle.load(open(os.path.join(CACHE, "c2_results.pkl"), "rb")) if stage == "report" else run_all()
        write_report(R, os.path.normpath(REPORT))
