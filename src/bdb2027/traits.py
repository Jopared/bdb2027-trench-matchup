"""Combine-trait pipeline: closed pool O1-O5 / D1-D6, reliability / redundancy / coverage gates, side composites.

Pre-registered design, step 1 (reports/candidates_v2.md section 3.2). Touches Combine tracking and Combine
results ONLY: never reads player_play or game tracking.

Conventions (reports/candidates.md, "Shared conventions"):
  * PLAYER rows only; order a player's reps by `time` (never by `attempt`); `dis` never used; `a` never used.
  * 3-frame centred mean smoothing (full window, edge frames NaN) with a 5-frame sensitivity.
  * time metrics are threshold-crossing based, never "time from frame 0".
  * bootstrap 95% CI: 2,000 resamples over players, seed 2027.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import polars as pl

from bdb2027 import paths

warnings.filterwarnings("ignore")

SEED, NBOOT, DT = 2027, 2000, 0.1
OFFICIAL = ["forty", "ten_yd_split", "short_shuttle", "three_cone", "combine_weight", "arm_length"]

DRILLS = {
    "drop": ["PASS_RUSH_DROP"],
    "rush": ["PASS_RUSH_DRILL"],
    "mirror": ["PASS_PRO-MIRROR_DRILL", "PASS_PRO_MIRROR_DRILL"],       # renamed across years
    "wave": ["FRONT_START_WAVE_DRILL_AND_LATERAL_REACTION"],
    "forty": ["FORTY_YARD_DASH"],
}


# --------------------------------------------------------------------------- numeric helpers
def cmean(a, k):
    """centred moving mean, window k (odd); edge frames (incomplete window) are NaN."""
    a = np.asarray(a, float)
    n, h = len(a), k // 2
    out = np.full(n, np.nan)
    if n >= k:
        out[h:n - h] = np.convolve(a, np.ones(k) / k, mode="valid")
    return out


def cdiff(a, dt=DT):
    """centred difference (a[i+1]-a[i-1])/(2 dt); edges NaN."""
    a = np.asarray(a, float)
    out = np.full(len(a), np.nan)
    out[1:-1] = (a[2:] - a[:-2]) / (2 * dt)
    return out


def pmean(v, w):
    """c1_ol_pass_set.smooth: pandas centred rolling mean with min_periods=1 (used only by O2, tested C1 code)."""
    return pd.Series(v).rolling(w, center=True, min_periods=1).mean().to_numpy()


def first_cross(t, v, thr, start=0):
    """linear-interpolated time and index of the first UPWARD crossing of thr at index >= start; (nan,-1) if none."""
    for i in range(max(start, 1), len(v)):
        if np.isnan(v[i]) or np.isnan(v[i - 1]):
            continue
        if v[i - 1] < thr <= v[i]:
            f = (thr - v[i - 1]) / (v[i] - v[i - 1])
            return t[i - 1] + f * (t[i] - t[i - 1]), i
    return np.nan, -1


def first_ge(t, v, thr, start=0):
    """first index i>=start with v[i]>=thr; interpolated time when v[i-1]<thr else t[i]."""
    for i in range(start, len(v)):
        if np.isnan(v[i]):
            continue
        if v[i] >= thr:
            if i - 1 >= start and not np.isnan(v[i - 1]) and v[i - 1] < thr:
                f = (thr - v[i - 1]) / (v[i] - v[i - 1])
                return t[i - 1] + f * (t[i] - t[i - 1]), i
            return t[i], i
    return np.nan, -1


def pear(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 4:
        return np.nan
    a, b = a[m], b[m]
    if a.std() == 0 or b.std() == 0:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def boot_r(a, b, nb=NBOOT, seed=SEED):
    """percentile bootstrap (over rows = players) 95% CI of the Pearson r; vectorised."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    n = len(a)
    if n < 6:
        return (np.nan, np.nan)
    idx = np.random.default_rng(seed).integers(0, n, (nb, n))
    A, B = a[idx], b[idx]
    A = A - A.mean(1, keepdims=True); B = B - B.mean(1, keepdims=True)
    den = np.sqrt((A ** 2).sum(1) * (B ** 2).sum(1))
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (A * B).sum(1) / den
    r = r[np.isfinite(r)]
    if len(r) < nb * 0.5:
        return (np.nan, np.nan)
    return tuple(np.percentile(r, [2.5, 97.5]))


def sb(r):
    return 2 * r / (1 + r) if np.isfinite(r) else np.nan


def zscore(v):
    v = np.asarray(v, float)
    sd = np.nanstd(v, ddof=1)
    return (v - np.nanmean(v)) / sd if sd > 0 else v * np.nan


def z_within(df, col, by):
    """z-score of df[col] within groups `by` (list); groups with <3 values or zero SD -> NaN."""
    g = df.groupby(by)[col]
    mu, sd, n = g.transform("mean"), g.transform("std"), g.transform("count")
    z = (df[col] - mu) / sd
    return z.where(n >= 3)


def mosier_reliability(Z, rel):
    """Reliability of an equal-weighted mean of k standardised components (Mosier).
    Z: DataFrame (players x components, pairwise-complete correlations); rel: list of component reliabilities.
    rel_c = 1 - sum_i (1-r_ii) / (k + 2 sum_{i<j} r_ij)."""
    k = Z.shape[1]
    if k == 1:
        return float(rel[0])
    C = Z.corr().to_numpy()
    sij = sum(C[i, j] for i in range(k) for j in range(i + 1, k))
    return float(1 - sum(1 - r for r in rel) / (k + 2 * sij))


# --------------------------------------------------------------------------- loading
def load_combine_results():
    return pl.read_parquet(paths.parquet("combine_results")).to_pandas()


def load_reps(names, positions=None):
    """One row per drill rep (PLAYER rows, one rep = one event_id), ordered by time within player.
    Columns: nfl_id, event_id, draft_year, t0 (first timestamp), rep (1-based chronological per player within
    the given drill-name set), x, y, s, dir (numpy arrays), combine_position."""
    ct = (pl.read_parquet(paths.parquet("combine_tracking"))
          .filter((pl.col("entity_type") == "PLAYER") & pl.col("drill_name").is_in(names))
          .sort("nfl_id", "event_id", "time"))
    rows = []
    for (pid, ev), g in ct.group_by(["nfl_id", "event_id"], maintain_order=True):
        rows.append(dict(nfl_id=int(pid), event_id=ev, draft_year=int(g["draft_year"][0]), t0=g["time"][0],
                         x=g["x"].to_numpy(), y=g["y"].to_numpy(), s=g["s"].to_numpy(), dir=g["dir"].to_numpy()))
    reps = pd.DataFrame(rows).sort_values(["nfl_id", "t0"]).reset_index(drop=True)
    reps["rep"] = reps.groupby("nfl_id").cumcount() + 1
    cr = load_combine_results()[["nfl_id", "combine_position"]]
    reps = reps.merge(cr, on="nfl_id", how="left")
    if positions is not None:
        reps = reps[reps.combine_position.isin(positions)].reset_index(drop=True)
    return reps


# --------------------------------------------------------------------------- rep-level metrics
def peak_speed(s, k):
    """O1 / D1: whole-rep max of the k-frame centred-mean speed."""
    v = cmean(s, k)
    return float(np.nanmax(v)) if np.isfinite(v).any() else np.nan


def _peak(s, k, variant=""):
    if variant == "raw":
        return float(np.max(s))                                  # unsmoothed (variant only)
    if variant == "pm1":
        return float(np.max(pmean(s, k)))                        # min_periods=1 smoothing (variant only)
    return peak_speed(s, k)


def drift_side_y(y):
    """+1 if the rep drifts to +y, else -1 (PASS_RUSH_DROP: drift side; PASS_RUSH_DRILL: right=+1 / left=-1)."""
    return 1 if (y[-1] - y[0]) > 0 else -1


def start_side_rush(x, y):
    """PASS_RUSH_DRILL side by start: nearer (45, 23.75) = right (+1), nearer (45, 30.25) = left (-1)."""
    dr = np.hypot(x[0] - 45, y[0] - 23.75)
    dl = np.hypot(x[0] - 45, y[0] - 30.25)
    return 1 if dr < dl else -1


def open_and_run(x, y, s, w):
    """O2: C1 definition (scripts/feasibility/c1_ol_pass_set.py rep_metrics.open_and_run, ported verbatim in logic).
    onset = first of 3 consecutive frames with smoothed s >= 0.5; time from s >= 2.0 (searched from onset + 1.8 s)
    to s >= 4.5 yd/s. NaN if either threshold is never reached. Uses min_periods=1 smoothing as in C1."""
    ss = pmean(s, w)
    t = np.arange(len(s)) * DT
    on = -1
    for i in range(len(ss) - 2):
        if (ss[i:i + 3] >= 0.5).all():
            on = i
            break
    if on < 0:
        return np.nan

    def ct(thr, i0):
        for i in range(i0, len(ss)):
            if ss[i] >= thr:
                if i == i0 or ss[i - 1] >= thr:
                    return t[i]
                f = (thr - ss[i - 1]) / (ss[i] - ss[i - 1])
                return t[i - 1] + f * (t[i] - t[i - 1])
        return np.nan

    i18 = int(np.ceil((t[on] + 1.8) / DT - 1e-9))
    if i18 >= len(ss):
        return np.nan
    t20 = ct(2.0, i18)
    if not np.isfinite(t20):
        return np.nan
    t45 = ct(4.5, int(np.floor(t20 / DT + 1e-9)))
    return t45 - t20 if np.isfinite(t45) else np.nan


def rush_features(s_raw, direction, y, k, side):
    """D2 / D3 from c2_edge_bend.py rep_features + window_metrics (ref='run', window 15-60 deg).
    get_off = time from the upward crossing of s=1.0 to the upward crossing of s=4.0 yd/s (threshold-crossing,
    censored -> NaN if s never seen below 1.0 or never reaches 4.0). turn_min_speed = min smoothed s while the
    heading deviates 15 -> 60 deg from the initial run heading. side: +1 right / -1 left."""
    n = len(s_raw)
    t = np.arange(n) * DT
    s = cmean(s_raw, k)
    t1, i1 = first_cross(t, s, 1.0)
    t4, i4 = first_cross(t, s, 4.0, start=max(i1, 0) if i1 >= 0 else 0)
    get_off = t4 - t1 if (i1 >= 0 and i4 >= 0) else np.nan
    out = dict(get_off=get_off, turn_min_speed=np.nan)
    t2, i2 = first_ge(t, s, 2.0)
    if i2 < 0:
        return out
    d = np.degrees(np.unwrap(np.radians(direction[i2:])))
    d0 = ((d[0] + 90) % 360) - 90
    hd = np.full(n, np.nan); hd[i2:] = d - d[0] + d0
    hsm = np.full(n, np.nan); hsm[i2:] = cmean(hd[i2:], k)
    t3, i3 = first_ge(t, s, 3.0)
    ia = i1 if i1 >= 0 else 1
    dd = np.degrees(np.unwrap(np.radians(direction[ia:])))
    dd = dd - dd[0] + (((dd[0] + 90) % 360) - 90)
    hrun = np.full(n, np.nan); hrun[ia:] = dd
    if not i3 > ia:
        return out
    h0 = float(np.nanmean(hrun[ia:i3 + 1]))
    dev = side * (h0 - hsm)
    tl, il = first_ge(t, dev, 15, start=i2)
    if il < 0:
        return out
    th, ih = first_ge(t, dev, 60, start=il)
    if ih < 0:
        return out
    out["turn_min_speed"] = float(np.nanmin(s[il:ih + 1]))
    return out


def reversal_times(y, k, thr=1.0, min_run=1):
    """O3 / D4: lateral reversal times. vy = centred difference of the k-frame smoothed y. A reversal is a pair of
    consecutive frames with |vy| >= thr and opposite sign: time = (first frame in the new direction) - (last frame in
    the old direction). min_run (variant only): require >= min_run consecutive qualifying frames in each direction.
    Returns list of reversal durations in chronological order."""
    vy = cdiff(cmean(y, k))
    q = np.where(np.isfinite(vy) & (np.abs(vy) >= thr))[0]
    if len(q) < 2:
        return []
    sg = np.sign(vy[q])
    # runs of same-sign qualifying frames (consecutive in the qualifying sequence)
    runs, start = [], 0
    for j in range(1, len(q) + 1):
        if j == len(q) or sg[j] != sg[j - 1]:
            runs.append((q[start], q[j - 1], sg[start], j - start))
            start = j
    out = []
    for a, b in zip(runs[:-1], runs[1:]):
        if a[3] >= min_run and b[3] >= min_run:
            out.append((b[0] - a[1]) * DT)           # first frame new direction - last frame old direction
    return out


def accel_shape(s, k, interp=False, lo=2.0, frac=0.9):
    """O4 / D5: time from the first frame with k-smoothed s >= 2.0 yd/s to the first frame at >= 0.9 x this run's
    own top speed (top speed = max of the k-smoothed s). The run must be seen BELOW 2.0 first (else censored -> NaN).
    interp=True (variant) uses linearly interpolated crossing times."""
    ss = cmean(s, k)
    if not np.isfinite(ss).any():
        return np.nan, np.nan
    top = np.nanmax(ss)
    t = np.arange(len(s)) * DT
    i2 = next((i for i in range(len(ss)) if ss[i] >= lo), -1)
    if i2 < 1 or np.isnan(ss[i2 - 1]) or ss[i2 - 1] >= lo:
        return np.nan, top
    i9 = next((i for i in range(i2, len(ss)) if ss[i] >= frac * top), -1)
    if i9 < 0:
        return np.nan, top
    if interp:
        ta = t[i2 - 1] + (lo - ss[i2 - 1]) / (ss[i2] - ss[i2 - 1]) * DT
        tb = t[i9] if i9 == i2 or ss[i9 - 1] >= frac * top else t[i9 - 1] + (frac * top - ss[i9 - 1]) / (ss[i9] - ss[i9 - 1]) * DT
        return tb - ta, top
    return t[i9] - t[i2], top


# --------------------------------------------------------------------------- trait registry
@dataclass
class Trait:
    tid: str
    side: str                  # "OL" | "DL"
    drill: str
    short: str
    definition: str
    orient: int                # +1 higher raw value = more athletic ; -1 lower raw value = more athletic
    kind: str                  # "cross" (>=2 slots) | "within" (single rep, odd/even)
    grouped: bool = False      # z within side(group) x year at the rep level (prescribed or decided)
    prescribed_z: bool = False
    note: str = ""
    oob_note: str = ""


POOL = [
    Trait("O1", "OL", "PASS_RUSH_DROP", "drop peak speed",
          "Whole-rep max of the 3-frame centred-mean speed (edge frames excluded); each rep z-scored within drift side (sign of y_end - y_start) x draft year; player value = mean of the (up to) two rep z-scores.",
          +1, "cross", True, True),
    Trait("O2", "OL", "PASS_RUSH_DROP", "drop open_and_run",
          "C1 open_and_run: onset = first of 3 consecutive frames with smoothed s >= 0.5; time from s >= 2.0 (searched from onset + 1.8 s) to s >= 4.5 yd/s (linear-interpolated crossings, C1 min_periods=1 smoothing). Seconds; lower = more athletic. Z within drift side x year (decision, same treatment as O1).",
          -1, "cross", True, False,
          note="Depends on the inferred 'open hips and run' phase timing (onset + 1.8 s)."),
    Trait("O3", "OL", "PASS_PRO(-/_)MIRROR_DRILL", "mirror reversal time",
          "Median lateral reversal time of the single rep: vy = centred difference of 3-frame smoothed y; reversal = consecutive frames with |vy| >= 1.0 yd/s of opposite sign, time = first frame in the new direction minus last frame in the old direction. Needs >= 4 reversals. Lower = more athletic. Reliability = odd- vs even-numbered reversals (median of each half).",
          -1, "within"),
    Trait("O4", "OL", "FORTY_YARD_DASH", "40 acceleration shape",
          "Time (s) from the first frame with 3-frame smoothed s >= 2.0 yd/s (run must be seen below 2.0 first) to the first frame at >= 0.9 x that run's own top speed (max of smoothed s); mean over the two runs. Lower = more athletic.",
          -1, "cross"),
    Trait("O5", "OL", "FORTY_YARD_DASH", "40 top speed",
          "Max of the 3-frame smoothed s within the run (yd/s); mean over the two runs. Higher = more athletic.",
          +1, "cross"),
    Trait("D1", "DL", "PASS_RUSH_DRILL", "rush-drill peak speed",
          "Whole-rep max of the 3-frame centred-mean speed (edge frames excluded); each rep z-scored within side (left/right by drift in y) x draft year; player value = mean of the first chronological left and right rep z-scores (>=1 rep).",
          +1, "cross", True, True),
    Trait("D2", "DL", "PASS_RUSH_DRILL", "rush turn_min_speed",
          "C2 turn_min_speed (run reference heading, 15-60 deg window): min smoothed s while the heading has turned 15 -> 60 deg from the initial run heading. Z within side x year (decision).",
          +1, "cross", True, False,
          oob_note="Pool records out-of-bag r = 0.22 (selected from a search in C2); the in-sample number computed here is optimistic."),
    Trait("D3", "DL", "PASS_RUSH_DRILL", "rush get_off",
          "C2 get_off: threshold-crossing time (s) from s first crossing 1.0 to s first crossing 4.0 yd/s (3-frame smoothed; NaN if s is never seen below 1.0). Lower = more athletic. Z within side x year (decision).",
          -1, "cross", True, False,
          oob_note="Pool records r = 0.37 (C2)."),
    Trait("D4", "DL", "FRONT_START_WAVE_DRILL_AND_LATERAL_REACTION", "wave reversal time",
          "Median lateral reversal time of the single rep, same definition as O3. Needs >= 4 reversals. Lower = more athletic. Reliability = odd vs even reversals.",
          -1, "within"),
    Trait("D5", "DL", "FORTY_YARD_DASH", "40 acceleration shape",
          "Same definition as O4 (time from smoothed s >= 2.0 yd/s to 0.9 x own top speed, mean of runs). Lower = more athletic.",
          -1, "cross"),
    Trait("D6", "DL", "FORTY_YARD_DASH", "40 top speed",
          "Same definition as O5 (max smoothed s in the 40, mean of runs). Higher = more athletic.",
          +1, "cross"),
]
TRAITS = {t.tid: t for t in POOL}


# --------------------------------------------------------------------------- per-trait rep tables
def rep_table(tid: str, reps: dict, k: int = 3, variant: str = "") -> pd.DataFrame:
    """Rep/slot-level raw values for one trait.
    cross: columns nfl_id, draft_year, slot (1/2), grp (+1/-1 or 0), val.
    within: columns nfl_id, draft_year, n_rev, val_all, val_odd, val_even."""
    tr = TRAITS[tid]
    rows = []
    if tid in ("O1", "O2"):
        R = reps["drop"]
        R = R[R.combine_position == "OL"]
        for _, r in R.iterrows():
            if r.rep > 2:
                continue
            start_ok = True
            if r.rep == 2:      # same-start pair rule (C1): rep 2 dropped if it starts > 3 yd from rep 1
                a = R[(R.nfl_id == r.nfl_id) & (R.rep == 1)].iloc[0]
                start_ok = np.hypot(a.x[0] - r.x[0], a.y[0] - r.y[0]) <= 3
            if tid == "O1":
                v = _peak(r.s, k, variant)
            else:
                v = open_and_run(r.x, r.y, r.s, k)
            rows.append(dict(nfl_id=r.nfl_id, draft_year=r.draft_year, slot=r.rep, grp=drift_side_y(r.y),
                             val=v if start_ok else np.nan))
    elif tid in ("D1", "D2", "D3"):
        R = reps["rush"]
        R = R[R.combine_position == "DL"].copy()
        R["side"] = [drift_side_y(y) for y in R.y]
        R["side_start"] = [start_side_rush(x, y) for x, y in zip(R.x, R.y)]
        first = R.groupby(["nfl_id", "side"]).head(1)           # first chronological rep per side
        for _, r in first.iterrows():
            if tid == "D1":
                v = _peak(r.s, k, variant)
            else:
                f = rush_features(r.s, r.dir, r.y, k, r.side)
                v = f["turn_min_speed"] if tid == "D2" else f["get_off"]
            rows.append(dict(nfl_id=r.nfl_id, draft_year=r.draft_year, slot=1 if r.side == -1 else 2, grp=r.side, val=v))
    elif tid in ("O4", "O5", "D5", "D6"):
        pos = "OL" if tid[0] == "O" else "DL"
        R = reps["forty"]
        R = R[(R.combine_position == pos) & (R.rep <= 2)]
        for _, r in R.iterrows():
            if tid in ("O4", "D5"):
                v, _top = accel_shape(r.s, k, interp=(variant == "interp"))
            else:
                v = _peak(r.s, k, variant)
            rows.append(dict(nfl_id=r.nfl_id, draft_year=r.draft_year, slot=r.rep, grp=0, val=v))
    elif tid in ("O3", "D4"):
        R = reps["mirror"] if tid == "O3" else reps["wave"]
        R = R[R.combine_position == ("OL" if tid == "O3" else "DL")]
        mr = 2 if variant == "minrun2" else 1
        thr = 0.5 if variant == "thr0.5" else 1.0
        for _, r in R.iterrows():
            rv = reversal_times(r.y, k, thr=thr, min_run=mr)
            ok = len(rv) >= 4
            rows.append(dict(nfl_id=r.nfl_id, draft_year=r.draft_year, n_rev=len(rv),
                             val_all=float(np.median(rv)) if ok else np.nan,
                             val_odd=float(np.median(rv[0::2])) if ok else np.nan,
                             val_even=float(np.median(rv[1::2])) if ok else np.nan))
        return pd.DataFrame(rows)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- gate computations
def year_drift(df, col, pid="nfl_id", year="draft_year"):
    """per-year mean deviation from the mean of the other years, in pooled within-year SDs. Returns dict + max abs."""
    d = df[[col, year]].dropna()
    psd = np.sqrt(d.groupby(year)[col].var(ddof=1).mean())
    dev = {}
    for y, g in d.groupby(year):
        dev[int(y)] = (g[col].mean() - d[d[year] != y][col].mean()) / psd
    return dev, max(abs(v) for v in dev.values()), {int(y): (g[col].mean(), g[col].std(ddof=1), len(g)) for y, g in d.groupby(year)}


def engaged_populations():
    """Side populations of the engaged-rep set (data/processed/engaged_pairs.parquet; no outcome columns read):
    blockers = distinct blocker_nfl_id with engaged_primary, lined up T/G/C, combine_position OL;
    rushers = distinct rusher_nfl_id with engaged_primary and combine_position DL."""
    d = pl.read_parquet(paths.parquet("engaged_pairs"),
                        columns=["blocker_nfl_id", "rusher_nfl_id", "engaged_primary", "blocker_lined_up_position",
                                 "blocker_combine_position", "rusher_combine_position"]).filter(pl.col("engaged_primary"))
    ol = d.filter(pl.col("blocker_lined_up_position").is_in(["T", "G", "C"]) & (pl.col("blocker_combine_position") == "OL"))["blocker_nfl_id"].unique().to_list()
    dl = d.filter(pl.col("rusher_combine_position") == "DL")["rusher_nfl_id"].unique().to_list()
    return {"OL": set(ol), "DL": set(dl)}


def evaluate_trait(tid, reps, cr, k=3, variant="", pop=None):
    """Everything for one trait at smoothing window k. Returns dict with per-player table `player` (index nfl_id)
    columns: value (gate-scale player value, before final position x year z), raw (unstandardised mean), n_slots."""
    tr = TRAITS[tid]
    T = rep_table(tid, reps, k, variant)
    res = dict(tid=tid, k=k)
    side_players = cr[cr.combine_position == tr.side]
    n_side = len(side_players)
    res["n_side"] = n_side
    if tr.kind == "within":
        T = T.copy()
        T["base"] = T["val_all"]
        dev, mx, ym = year_drift(T.dropna(subset=["val_all"]), "val_all")
        flag = mx > 0.5
        res.update(drift=dev, drift_max=mx, drift_flag=flag, year_means=ym, year_applied=flag)
        if flag:
            for c in ("val_all", "val_odd", "val_even"):
                both = pd.concat([T[["draft_year", "val_odd"]].rename(columns={"val_odd": "v"}),
                                  T[["draft_year", "val_even"]].rename(columns={"val_even": "v"})])
                mu = both.groupby("draft_year").v.mean(); sd = both.groupby("draft_year").v.std(ddof=1)
                T[c + "_g"] = (T[c] - T.draft_year.map(mu)) / T.draft_year.map(sd)
        else:
            for c in ("val_all", "val_odd", "val_even"):
                T[c + "_g"] = T[c]
        ok = T.val_odd.notna() & T.val_even.notna()
        a, b = T.loc[ok, "val_odd_g"].to_numpy(), T.loc[ok, "val_even_g"].to_numpy()
        r = pear(a, b); lo, hi = boot_r(a, b)
        res.update(n=int(ok.sum()), r=r, lo=lo, hi=hi, r_sb=sb(r), rel_item=sb(r))
        P = T.set_index("nfl_id")
        player = pd.DataFrame({"value": P["val_all_g"], "raw": P["val_all"], "n_slots": P["n_rev"]})
        res["n_rev_dist"] = T.n_rev.describe().to_dict()
        res["reps_total"] = len(T)
    else:
        T = T.copy()
        if tr.grouped:
            # side-only standardisation (drift check scale), then side x year (gate scale)
            T["z_side"] = z_within(T, "val", ["grp"])
            T["gate"] = z_within(T, "val", ["grp", "draft_year"])
            base = "z_side"
            applied = True
        else:
            base = "val"
            applied = False
        pl_ = T.groupby("nfl_id").agg(b=(base, "mean"), draft_year=("draft_year", "first"))
        dev, mx, ym = year_drift(pl_.reset_index(), "b")
        flag = mx > 0.5
        res.update(drift=dev, drift_max=mx, drift_flag=flag, year_means=ym)
        if not tr.grouped:
            if flag:
                T["gate"] = z_within(T, "val", ["draft_year"])
                applied = True
            else:
                T["gate"] = T["val"]
        res["year_applied"] = applied
        W = T.pivot_table(index="nfl_id", columns="slot", values="gate", aggfunc="first")
        Wr = T.pivot_table(index="nfl_id", columns="slot", values="val", aggfunc="first")
        Wb = T.pivot_table(index="nfl_id", columns="slot", values=base, aggfunc="first")
        if W.shape[1] < 2:
            raise ValueError(f"{tid}: fewer than two slots")
        a, b = W[1].to_numpy(), W[2].to_numpy()
        okm = np.isfinite(a) & np.isfinite(b)
        r = pear(a, b); lo, hi = boot_r(a, b)
        res.update(n=int(okm.sum()), r=r, lo=lo, hi=hi, r_sb=sb(r), rel_item=sb(r),
                   r_raw=pear(Wr[1], Wr[2]), r_sideonly=pear(Wb[1], Wb[2]))
        res["n_both_slots"] = int(okm.sum())
        gm = W.mean(axis=1, skipna=True)
        rawm = Wr.mean(axis=1, skipna=True)
        player = pd.DataFrame({"value": gm, "raw": rawm, "n_slots": W.notna().sum(axis=1)})
        player = player[player.n_slots > 0]
        res["reps_total"] = len(T)
    player = player[player.index.isin(side_players.nfl_id)]
    res["player"] = player
    res["coverage_all_n"] = int(player["value"].notna().sum())
    res["coverage_all"] = res["coverage_all_n"] / n_side
    if pop is not None:
        ids = pop[tr.side]
        res["n_pop"] = len(ids)
        res["coverage_n"] = int(player["value"].dropna().index.isin(list(ids)).sum())
        res["coverage"] = res["coverage_n"] / len(ids)
    else:
        res["n_pop"] = n_side
        res["coverage_n"], res["coverage"] = res["coverage_all_n"], res["coverage_all"]
    # redundancy: |r| vs each official measure, within side, gate-scale player value
    cp = side_players.set_index("nfl_id")
    red, red_raw = {}, {}
    for c in OFFICIAL:
        x = cp[c].reindex(player.index).to_numpy(float)
        ok = np.isfinite(x) & player["value"].notna().to_numpy()
        n_ = int(ok.sum())
        if c == "three_cone" and n_ < 30:
            red[c] = (np.nan, n_, "n<30: skipped")
            red_raw[c] = (np.nan, n_)
            continue
        red[c] = (pear(player["value"].to_numpy(), x), n_, "")
        red_raw[c] = (pear(player["raw"].to_numpy(), x), n_)
    res["red"], res["red_raw"] = red, red_raw
    res["max_abs_r"] = max((abs(v[0]) for v in red.values() if np.isfinite(v[0])), default=np.nan)
    res["max_abs_r_raw"] = max((abs(v[0]) for v in red_raw.values() if np.isfinite(v[0])), default=np.nan)
    res["argmax"] = max(((c, abs(v[0])) for c, v in red.items() if np.isfinite(v[0])), key=lambda z: z[1], default=("", np.nan))[0]
    return res


def gate_verdicts(res):
    tr = TRAITS[res["tid"]]
    if tr.kind == "within":
        rel = bool(res["r"] >= 0.60)
        rel_rule = "within-rep odd/even r >= 0.60"
    else:
        rel = bool(res["r"] >= 0.50 and res["lo"] >= 0.30)
        rel_rule = "cross-rep r >= 0.50 and CI lower >= 0.30"
    red = bool(res["max_abs_r"] < 0.75)
    cov = bool(res["coverage"] >= 0.80)
    return dict(rel=rel, red=red, cov=cov, passed=rel and red and cov, rel_rule=rel_rule)


# --------------------------------------------------------------------------- composites
def build_composites(results, verdicts, cr):
    """Per player (OL and DL): oriented within-position x within-draft-year z of every passing trait; equal-weighted
    mean (>= 1 component). Returns (player DataFrame, composite info per side)."""
    out = cr[cr.combine_position.isin(["OL", "DL"])][["nfl_id", "combine_position", "draft_year"]].set_index("nfl_id").copy()
    info = {}
    for side in ("OL", "DL"):
        tids = [t for t in TRAITS if TRAITS[t].side == side]
        for t in tids:
            P = results[t]["player"]
            df = out[out.combine_position == side][["draft_year"]].join(P[["value", "raw", "n_slots"]])
            z = z_within(df.assign(c=df["value"]), "c", ["draft_year"]) * TRAITS[t].orient
            out.loc[df.index, f"{t}_value"] = df["raw"]
            out.loc[df.index, f"{t}_n_slots"] = df["n_slots"]
            out.loc[df.index, f"{t}_z"] = z
        passing = [t for t in tids if verdicts[t]["passed"]]
        m = out.combine_position == side
        if passing:
            Z = out.loc[m, [f"{t}_z" for t in passing]]
            comp = Z.mean(axis=1, skipna=True)
            ncomp = Z.notna().sum(axis=1)
            out.loc[m, "composite"] = comp.where(ncomp > 0)
            out.loc[m, "composite_n_components"] = ncomp
            rel = [results[t]["rel_item"] if np.isfinite(results[t]["rel_item"]) else np.nan for t in passing]
            comp_full = Z.dropna()
            info[side] = dict(passing=passing, n_comp=int((ncomp > 0).sum()), n_all_components=len(comp_full),
                              mosier=mosier_reliability(comp_full, rel) if len(comp_full) > 5 else np.nan,
                              mosier_uncorrected=mosier_reliability(comp_full, [results[t]["r"] for t in passing]) if len(comp_full) > 5 else np.nan,
                              corr=comp_full.corr() if len(passing) > 1 else None, rel=rel,
                              ncomp_dist=ncomp.value_counts().sort_index().to_dict())
        else:
            out.loc[m, "composite"] = np.nan
            out.loc[m, "composite_n_components"] = 0
            info[side] = dict(passing=[], n_comp=0)
    for t in TRAITS:
        out[f"{t}_pass"] = verdicts[t]["passed"]
    return out.reset_index(), info
