"""F3 'what the Combine measured'. Uses only Combine tables (combine_tracking, combine_traits, combine_results).

Selection rules (deterministic, no randomness; ties broken by ascending nfl_id):
  A  OL prospect: among OL with a registered O3 value (mirror-drill reversal time, the registered OL composite), a
     PASS_PRO(-/_)MIRROR_DRILL rep and two PASS_RUSH_DROP reps, the one whose O3_value is closest to the OL median.
     NOTE: the registered OL composite is the MIRROR drill (O3), not PASS_RUSH_DROP. Panel A shows the mirror
     rep with the lateral reversals highlighted (PASS_RUSH_DROP reps, trait O1, failed qualification and are not drawn).
  B  DL prospect: among DL with a D1 value and one rep on each side of PASS_RUSH_DRILL (right = start nearer (45, 23.75),
     left = nearer (45, 30.25)), the one whose D1_value is closest to the DL median. The whole-rep peak of the
     3-frame centred-mean speed is marked on each rep (the D1 definition).
  C  40-yard dash: among OL/DL with a 40 acceleration-shape value from two runs (O4/D5) and an official forty time,
     keep players whose two runs' own shapes agree within 0.30 s (drops one tracking outlier), then take pairs of the
     same combine position group with |forty difference| <= 0.01 s; choose the pair with the largest |shape difference|
     (ties: smaller forty gap, then ids). Curves are aligned at the first frame with smoothed speed >= 2 yd/s (the start of
     the shape measure); the shape segment runs to 0.9 x the run's own top speed.
Run: .venv\\Scripts\\python scripts\\figures\\f3_combine_measured.py
"""
import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

from _common import *  # noqa
from bdb2027 import traits as T

style()
tr = pl.read_parquet(PROC / "combine_traits.parquet").to_pandas()
cr = pl.read_parquet(PROC / "combine_results.parquet").to_pandas()[["nfl_id", "forty"]]
names = pl.read_parquet(PROC / "players.parquet").select("nfl_id", "display_name").to_pandas().set_index("nfl_id").display_name
tr = tr.merge(cr, on="nfl_id", how="left")

mirror = T.load_reps(T.DRILLS["mirror"])
drop = T.load_reps(T.DRILLS["drop"])   # only used to keep the same OL selection as before
rush = T.load_reps(T.DRILLS["rush"])
fort = T.load_reps(T.DRILLS["forty"])

# ---------------------------------------------------------------- selection
ol = tr[(tr.combine_position == "OL") & tr.O3_value.notna()]
ol = ol[ol.nfl_id.isin(mirror.nfl_id) & ol.nfl_id.isin(drop.groupby("nfl_id").size().loc[lambda s: s >= 2].index)]
ol = ol.assign(dev=(ol.O3_value - tr[(tr.combine_position == "OL")].O3_value.median()).abs()).sort_values(["dev", "nfl_id"])
ol_id = int(ol.iloc[0].nfl_id)

dl_c = tr[(tr.combine_position == "DL") & tr.D1_value.notna()]
ok = []
for pid in dl_c.nfl_id:
    rr = rush[rush.nfl_id == pid]
    sides = {T.start_side_rush(x, y) for x, y in zip(rr.x, rr.y)}
    if len(rr) >= 2 and sides == {1, -1}:
        ok.append(pid)
dl_c = dl_c[dl_c.nfl_id.isin(ok)]
dl_c = dl_c.assign(dev=(dl_c.D1_value - tr[(tr.combine_position == "DL")].D1_value.median()).abs()).sort_values(["dev", "nfl_id"])
dl_id = int(dl_c.iloc[0].nfl_id)

# 40: per-run shape from the tracking, same function as the registered trait
runs40 = {}
for pid, g in fort.groupby("nfl_id"):
    g = g.sort_values("t0")
    shapes = [T.accel_shape(s, 3)[0] for s in g.s]
    runs40[int(pid)] = (g, shapes)
c = tr.copy()
c["shp"] = c.O4_value.fillna(c.D5_value)
c["nsl"] = c.O4_n_slots.fillna(c.D5_n_slots)
c = c.dropna(subset=["shp", "forty"])
c = c[(c.nsl == 2) & c.nfl_id.isin(runs40)]
c = c[[all(np.isfinite(runs40[i][1])) and len(runs40[i][1]) == 2 and abs(runs40[i][1][0] - runs40[i][1][1]) <= 0.30 for i in c.nfl_id]]
cand = []
rows = list(c.itertuples())
for i, a in enumerate(rows):
    for b in rows[i + 1:]:
        if a.combine_position == b.combine_position and abs(a.forty - b.forty) <= 0.0101:
            lo, hi = sorted([a, b], key=lambda z: z.nfl_id)
            cand.append((-abs(a.shp - b.shp), abs(a.forty - b.forty), lo.nfl_id, hi.nfl_id))
cand.sort()
_, _, p1, p2 = cand[0]
tr["shp"] = tr.O4_value.fillna(tr.D5_value)
fast, slow = sorted([p1, p2], key=lambda i: float(tr.loc[tr.nfl_id == i, "shp"].iloc[0]))
print("OL", ol_id, names.get(ol_id), "O3", float(tr.loc[tr.nfl_id == ol_id, "O3_value"].iloc[0]))
print("DL", dl_id, names.get(dl_id), "D1", float(tr.loc[tr.nfl_id == dl_id, "D1_value"].iloc[0]))
print("40 pair", fast, slow, "candidates", len(cand))


# ---------------------------------------------------------------- helpers
def reversal_segments(y, k=3, thr=1.0):
    """Same definition as traits.reversal_times, returning frame indices (last old-direction frame, first new-direction frame)."""
    vy = T.cdiff(T.cmean(y, k))
    q = np.where(np.isfinite(vy) & (np.abs(vy) >= thr))[0]
    if len(q) < 2:
        return []
    sg = np.sign(vy[q])
    runs, st = [], 0
    for j in range(1, len(q) + 1):
        if j == len(q) or sg[j] != sg[j - 1]:
            runs.append((q[st], q[j - 1]))
            st = j
    return [(a[1], b[0]) for a, b in zip(runs[:-1], runs[1:])]


def speed_path(ax, x, y, s, norm, lw=2.6, zorder=2):
    pts = np.column_stack([x, y]).reshape(-1, 1, 2)
    seg = np.concatenate([pts[:-1], pts[1:]], axis=1)
    lc = LineCollection(seg, cmap=SEQ_CMAP, norm=norm, linewidths=lw, zorder=zorder, capstyle="round")
    lc.set_array(0.5 * (s[:-1] + s[1:]))
    ax.add_collection(lc)
    return lc


def rep_rows(df, who, drill, rep_label, extra=None):
    out = pd.DataFrame({"nfl_id": who, "drill": drill, "rep": rep_label, "frame": np.arange(len(df["x"])),
                        "t_s": np.arange(len(df["x"])) * 0.1, "x": df["x"], "y": df["y"], "speed_ydps": df["s"]})
    if extra:
        for k, v in extra.items():
            out[k] = v
    return out


tables = []
norm = Normalize(0, 9)
fig = plt.figure(figsize=(12.5, 9.2))
gs = fig.add_gridspec(2, 3, height_ratios=[1.1, 1], hspace=0.38, wspace=0.28)

# ---- A: mirror drill with reversals
axm = fig.add_subplot(gs[0, 0:2])
mr = mirror[mirror.nfl_id == ol_id].iloc[0]
segs = reversal_segments(mr.y)
tt = np.arange(len(mr.y)) * 0.1
speed_path(axm, tt, mr.y, mr.s, norm)
inseg = np.zeros(len(mr.y), bool)
for a, b in segs:
    axm.plot(tt[a:b + 1], mr.y[a:b + 1], color=ORANGE, lw=6, alpha=0.9, zorder=3, solid_capstyle="round")
    inseg[a:b + 1] = True
axm.autoscale_view()
axm.set_xlabel("seconds into the rep"); axm.set_ylabel("lateral position y (yd)")
axm.set_title("Mirror drill: lateral reversals (orange)")
rv = [(b - a) * 0.1 for a, b in segs]
axm.text(0.02, 0.02, f"{len(rv)} reversals, median {np.median(rv):.2f} s (lower = faster; the composite uses the median)" + chr(10) + "blue line colour = speed (yd/s, colour bar at right); orange = reversal segments",
         transform=axm.transAxes, va="bottom", fontsize=8, color=INK2)
tables.append(rep_rows(mr, ol_id, "PASS_PRO_MIRROR_DRILL", "mirror", {"in_reversal_segment": inseg}))
panel_tag(axm, "A")

# ---- B: DL rush drill
axr = fig.add_subplot(gs[0, 2])
rr = rush[rush.nfl_id == dl_id].sort_values("t0")
peak_rows = []
for _, rp in rr.iterrows():
    side = T.start_side_rush(rp.x, rp.y)
    sm = T.cmean(rp.s, 3)
    i = int(np.nanargmax(sm))
    speed_path(axr, rp.x, rp.y, rp.s, norm)
    axr.scatter(rp.x[0], rp.y[0], s=22, color=INK, zorder=4)
    axr.scatter(rp.x[i], rp.y[i], s=120, facecolor="none", edgecolor=ORANGE, lw=2.2, zorder=5)
    lab = ("right start (rip/swim: right = swim)" if side == 1 else "left start")
    axr.annotate(f"peak {sm[i]:.1f} yd/s", (rp.x[i], rp.y[i]), xytext=(8, 8), textcoords="offset points", color=INK, fontsize=8)
    tables.append(rep_rows(rp, dl_id, "PASS_RUSH_DRILL", f"{'right' if side == 1 else 'left'} start",
                           {"smoothed_speed_k3": sm, "is_peak_frame": np.arange(len(sm)) == i}))
axr.autoscale_view(); axr.set_aspect("equal", adjustable="datalim")
axr.set_xlabel("x (yd)"); axr.set_ylabel("y (yd)")
axr.set_title("Pass-rush drill: peak speed")
axr.text(0.02, 0.02, "ring = whole-rep peak of the 3-frame\nsmoothed speed (D1, the DL composite)",
         transform=axr.transAxes, va="bottom", fontsize=8, color=INK2)
panel_tag(axr, "B")
cax = fig.add_axes([0.955, 0.57, 0.009, 0.3])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=SEQ_CMAP), cax=cax)
cb.set_label("speed (yd/s)"); cb.outline.set_visible(False)

# ---- C: two 40s
axc = fig.add_subplot(gs[1, 0:2])
cols = {fast: BLUE, slow: ORANGE}
for pid in (fast, slow):
    g, shp = runs40[pid]
    pos = tr.loc[tr.nfl_id == pid, "combine_position"].iloc[0]
    ft = float(cr.loc[cr.nfl_id == pid, "forty"].iloc[0])
    mshape = float(tr.loc[tr.nfl_id == pid, "shp"].iloc[0])
    for k, (_, rp) in enumerate(g.iterrows()):
        ss = T.cmean(rp.s, 3)
        top = np.nanmax(ss)
        i2 = next(i for i in range(len(ss)) if ss[i] >= 2.0)
        i9 = next(i for i in range(i2, len(ss)) if ss[i] >= 0.9 * top)
        t = (np.arange(len(ss)) - i2) * 0.1
        keep = (t >= -0.5) & (t <= 6.0)
        axc.plot(t[keep], rp.s[keep], color=cols[pid], lw=1.6 if k == 0 else 1.6, ls="-" if k == 0 else (0, (4, 2)),
                 alpha=0.95, label=None)
        axc.plot([0, t[i9]], [ss[i2], ss[i9]], color=cols[pid], lw=0, marker="o", ms=6, mec=SURFACE)
        axc.hlines(0.1 + (0.0 if pid == fast else 0.0), 0, 0, color=cols[pid])
        tables.append(pd.DataFrame({"nfl_id": pid, "drill": "FORTY_YARD_DASH", "run": k + 1, "t_from_2ydps_s": t,
                                    "speed_ydps": rp.s, "smoothed_speed_k3": ss, "official_forty": ft,
                                    "shape_run_s": shp[k], "shape_player_mean_s": mshape}))
    axc.plot([], [], color=cols[pid], lw=2,
             label=f"{names.get(pid, pid)} ({pos}): official 40 {ft:.2f} s, acceleration shape {mshape:.2f} s (2 -> 90% of top speed)")
axc.axvline(0, color=AXIS, lw=0.9)
axc.set_xlabel("seconds from the first frame at 2 yd/s (the shape measure starts here)")
axc.set_ylabel("speed (yd/s)")
axc.set_xlim(-0.5, 6.0)
axc.legend(loc="lower right", fontsize=8.5)
axc.set_title("Same official 40 time, different acceleration shape (solid = run 1, dashed = run 2)")
panel_tag(axc, "C")

# ---- D: what a 0.4 s vs a 0.5 s reversal looks like at 10 Hz (two real reversals from the mirror rep of panel A)
axv = fig.add_subplot(gs[1, 2])
ysm = T.cmean(mr.y, 3)
pick = {}
for a, b in segs:
    dur = round((b - a) * 0.1, 1)
    if dur in (0.4, 0.5) and dur not in pick:
        pick[dur] = (a, b)
dcol = {0.4: ORANGE, 0.5: BLUE}
for dur, (a, b) in sorted(pick.items()):
    fr_ = np.arange(a - 3, b + 4)
    t_ = (fr_ - a) * 0.1
    yy = ysm[fr_] - ysm[a]
    off = 0.0 if dur == 0.4 else -0.0
    axv.plot(t_, yy, color=dcol[dur], lw=1.4, alpha=0.8)
    axv.scatter(t_, yy, s=26, color=dcol[dur], zorder=3, edgecolor=SURFACE, linewidth=0.6, label=f"{dur:.1f} s reversal = {int(round(dur * 10))} frames")
    axv.axvspan(0, (b - a) * 0.1, color=dcol[dur], alpha=0.10, lw=0)
    tables.append(pd.DataFrame({"nfl_id": ol_id, "drill": "PASS_PRO_MIRROR_DRILL", "reversal_s": dur, "frame": fr_,
                                "t_from_last_old_direction_frame_s": t_, "y_smoothed_rel": yy}))
for k in range(-3, 8):
    axv.axvline(k * 0.1, color=GRID, lw=0.6, zorder=0)
axv.axhline(0, color=AXIS, lw=0.8)
axv.set_xlabel("seconds from the last frame moving the old way (ticks = 10 Hz frames)")
axv.set_ylabel("lateral position y, relative (yd)")
axv.set_title("D. A 4- vs a 5-frame reversal")
axv.legend(loc="upper left", fontsize=8)
axv.text(0.98, 0.03, "The registered OL trait is the median of" + chr(10) + "such counts, so one frame is 0.1 s.", transform=axv.transAxes,
         ha="right", va="bottom", fontsize=8, color=INK2)

ft1 = float(cr.loc[cr.nfl_id == fast, "forty"].iloc[0]); ft2 = float(cr.loc[cr.nfl_id == slow, "forty"].iloc[0])
fig.suptitle("F3. What the Combine measured: OL mirror-drill reversals (registered OL trait), DL rush-drill peak speed (registered DL trait), and the 40 shape",
             x=0.01, ha="left", y=0.995, fontsize=10.5, fontweight="bold")
fig.subplots_adjust(top=0.90, left=0.06, right=0.93, bottom=0.07)
out = pd.concat(tables, ignore_index=True)
save(fig, "F3_combine_measured", out)
