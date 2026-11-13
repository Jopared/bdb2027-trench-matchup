"""F1 'finding the rep': one real engaged blocker-rusher rep.

Selection rule (deterministic, no randomness):
  eligible = engaged_pairs rows with engaged_primary == True (1.5 yd for >= 4 frames),
             double_team == False (no other engaged blocker on the same rusher) and the blocker has no other
             engaged rusher on the play (single rusher).
  chosen   = the eligible pair whose n_close_150 (frames within 1.5 yd in the window) is closest to the median
             of the eligible set; ties broken by ascending (game_id, play_id, blocker_nfl_id, rusher_nfl_id).
Open columns of engaged_pairs and tracking x/y/event are used; the rep outcome (pressure_allowed, sack_allowed) is read from the unsealed engaged_outcomes_SEALED.parquet for the title only. The tracking table holds only the draft-cohort players, so the QB is not available (checked via
player_play.lined_up_position, projected columns only) and is not drawn. Orientation: downfield = the direction from the
blocker toward the rusher at the snap (rushers start on or past the line of scrimmage).
Run: .venv\\Scripts\\python scripts\\figures\\f1_engaged_rep.py
"""
import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from _common import *  # noqa

style()
pairs = pl.read_parquet(PROC / "engaged_pairs.parquet")
eng = pairs.filter(pl.col("engaged_primary") & ~pl.col("double_team"))
per_blk = (pairs.filter(pl.col("engaged_primary")).group_by("game_id", "play_id", "blocker_nfl_id")
           .agg(pl.len().alias("n_rush_eng")))
eng = eng.join(per_blk, on=["game_id", "play_id", "blocker_nfl_id"]).filter(pl.col("n_rush_eng") == 1)
med = float(eng["n_close_150"].median())
eng = eng.with_columns((pl.col("n_close_150") - med).abs().alias("_dev")).sort(
    ["_dev", "game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id"])
sel = eng.row(0, named=True)
print("eligible reps:", eng.height, "median n_close_150:", med, "chosen:", {k: sel[k] for k in
      ["game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id", "n_close_150", "n_common_frames", "season", "week"]})

g, p, b, r, season = sel["game_id"], sel["play_id"], sel["blocker_nfl_id"], sel["rusher_nfl_id"], sel["season"]
pp = (pl.scan_parquet(PROC / "player_play.parquet").filter((pl.col("game_id") == g) & (pl.col("play_id") == p))
      .select("nfl_id", "lined_up_position").collect())
qb_ids = pp.filter(pl.col("lined_up_position") == "QB")["nfl_id"].to_list()
ids = [b, r] + qb_ids   # qb_ids is empty in this dataset (cohort players only)
fr = (pl.scan_parquet(PROC / f"game_tracking_{season}.parquet")
      .filter((pl.col("game_id") == g) & (pl.col("play_id") == p) & pl.col("nfl_id").is_in(ids))
      .select("nfl_id", "time", "x", "y", "event").sort("time").collect().to_pandas())
ev = fr.dropna(subset=["event"])
t_snap = ev.loc[ev.event == "ball_snap", "time"].min()
t_pf = ev.loc[ev.event == "pass_forward", "time"].min()
t_sk = ev.loc[ev.event == "qb_sack", "time"].min()
cands = {"snap + 3.0 s": t_snap + pd.Timedelta(seconds=3.0), "pass_forward": t_pf, "qb_sack": t_sk}
cands = {k: v for k, v in cands.items() if pd.notna(v)}
end_reason = min(cands, key=cands.get)
t_start, t_end = t_snap + pd.Timedelta(seconds=0.2), cands[end_reason]

fr["t"] = (fr.time - t_snap).dt.total_seconds().round(1)
B = fr[fr.nfl_id == b].set_index("t")[["x", "y"]]
R = fr[fr.nfl_id == r].set_index("t")[["x", "y"]]
Q = fr[fr.nfl_id == qb_ids[0]].set_index("t")[["x", "y"]] if qb_ids else None
both = B.join(R, lsuffix="_b", rsuffix="_r", how="inner")
both["d"] = np.hypot(both.x_b - both.x_r, both.y_b - both.y_r)
ts, te = 0.2, round((t_end - t_snap).total_seconds(), 1)
both["in_window"] = (both.index >= ts - 1e-9) & (both.index <= te + 1e-9)
both["close"] = both.in_window & (both.d <= 1.5)
print("end reason", end_reason, "window", ts, te, "close frames", int(both.close.sum()))

# orient: x' increases from the blocker toward the rusher at the snap (downfield); origin = blocker position at the snap
x0, y0 = B.loc[0.0, "x"], B.loc[0.0, "y"]
ref_x = Q.loc[0.0, "x"] if Q is not None and 0.0 in Q.index else None
u = np.sign(x0 - ref_x) if ref_x is not None else np.sign(R.loc[0.0, "x"] - x0)  # QB never available here
flip = 1 if u > 0 else -1          # rotate 180 degrees when the offence moves toward decreasing x (keeps handedness)
tx = lambda d: u * (d.x - x0)
ty = lambda d: flip * (d.y - y0)
tmax = min(max(B.index.max(), R.index.max()), te + 1.0)
Bp, Rp = B[B.index <= tmax], R[R.index <= tmax]
Qp = Q[Q.index <= tmax] if Q is not None else None

oc = (pl.read_parquet(PROC / "engaged_outcomes_SEALED.parquet")
        .filter((pl.col("game_id") == g) & (pl.col("play_id") == p) & (pl.col("blocker_nfl_id") == b) & (pl.col("rusher_nfl_id") == r))
        .row(0, named=True))
outcome = "pressure allowed" if oc["pressure_allowed"] else "no pressure allowed"
if oc.get("sack_allowed"):
    outcome += " (sack)"
print("outcome:", outcome, {k: oc[k] for k in ("pressure_allowed", "sack_allowed", "rusher_time_to_pressure")})
names = pl.read_parquet(PROC / "players.parquet").select("nfl_id", "display_name").to_pandas().set_index("nfl_id").display_name
nb, nr = names.get(b, str(b)), names.get(r, str(r))

fig = plt.figure(figsize=(10, 8))
gs = fig.add_gridspec(2, 1, height_ratios=[1.5, 1], hspace=0.38)
ax = fig.add_subplot(gs[0])
for d, c, lab in ((Bp, BLUE, f"Blocker  {nb} ({sel['blocker_lined_up_position']})"),
                  (Rp, ORANGE, f"Rusher  {nr} ({sel['rusher_lined_up_position']})")):
    ax.plot(ty(d), tx(d), color=c, lw=1.2, alpha=0.5, zorder=2)
    inw = d[(d.index >= ts - 1e-9) & (d.index <= te + 1e-9)]
    ax.plot(ty(inw), tx(inw), color=c, lw=6, alpha=0.22, zorder=1, solid_capstyle="round")   # engagement window band
    ax.scatter(ty(d), tx(d), s=14, color=c, zorder=3, label=lab, edgecolor=SURFACE, linewidth=0.5)
cl = both[both.close]
ax.scatter(ty(Bp.loc[cl.index]), tx(Bp.loc[cl.index]), s=46, facecolor="none", edgecolor=INK, lw=0.9, zorder=4)
ax.scatter(ty(Rp.loc[cl.index]), tx(Rp.loc[cl.index]), s=46, facecolor="none", edgecolor=INK, lw=0.9, zorder=4)
if Qp is not None:
    ax.scatter(tx(Qp), ty(Qp), s=10, color=MUTED, zorder=2)
    ax.annotate("QB", (tx(Qp).iloc[0], ty(Qp).iloc[0]), xytext=(-4, 7), textcoords="offset points", color=INK2, ha="right")
for t_lab in (0.0, 1.0, 2.0, 3.0):
    if t_lab in Bp.index and t_lab <= tmax:
        ax.annotate(f"{t_lab:.0f} s", (ty(Bp.loc[[t_lab]]).iloc[0], tx(Bp.loc[[t_lab]]).iloc[0]), xytext=(-9, -3),
                    textcoords="offset points", color=INK2, fontsize=8, ha="center")
        ax.annotate(f"{t_lab:.0f} s", (ty(Rp.loc[[t_lab]]).iloc[0], tx(Rp.loc[[t_lab]]).iloc[0]), xytext=(9, 3),
                    textcoords="offset points", color=INK2, fontsize=8, ha="center")
ax.axhline(0, color=AXIS, lw=0.8, ls=":")
ax.set_aspect("equal", adjustable="box")
ax.set_ylabel("yards downfield of the blocker's snap position")
ax.set_xlabel("yards across the field from the blocker's snap position")
handles, labels = ax.get_legend_handles_labels()
handles += [Line2D([], [], marker="o", mfc="none", mec=INK, ls="", ms=7)]
labels += ["frame within 1.5 yd inside the window"]
ax.legend(handles, labels, loc="upper right", fontsize=8)
panel_tag(ax, "A")
ax.set_title("Paths from the snap, one dot every 0.1 s")

bx = fig.add_subplot(gs[1])
dd = both[both.index <= tmax]
bx.axvspan(ts, te, color=MUTED, alpha=0.13, lw=0)
bx.plot(dd.index, dd.d, color=INK2, lw=1.4, zorder=2)
bx.scatter(dd.index[dd.close], dd.d[dd.close], s=28, color=INK, zorder=3,
           label=f"frames within 1.5 yd ({int(dd.close.sum())}; the rule needs 4)")
bx.scatter(dd.index[~dd.close], dd.d[~dd.close], s=14, color=MUTED, zorder=3)
bx.axhline(1.5, color=RED, lw=1.2)
bx.annotate("1.5 yd", (0.02, 1.5), xytext=(0, 4), textcoords="offset points", color=INK2, ha="left")
bx.axvline(0.0, color=AXIS, lw=1)
ytop = dd.d.max()
bx.annotate("snap", (0.0, ytop * 1.12), xytext=(3, -10), textcoords="offset points", color=INK2)
bx.axvline(ts, color=INK2, lw=0.9, ls="--"); bx.axvline(te, color=INK2, lw=0.9, ls="--")
bx.annotate("window starts\nsnap + 0.2 s", (ts, ytop), xytext=(4, -14), textcoords="offset points", color=INK2, va="top", fontsize=8)
bx.annotate(f"window ends: {end_reason}\n(earliest of snap + 3.0 s, pass_forward, qb_sack)", (te, ytop), xytext=(-4, -14),
            textcoords="offset points", color=INK2, ha="right", va="top", fontsize=8)
bx.set_xlabel("seconds from the snap"); bx.set_ylabel("blocker-rusher distance (yd)")
bx.set_ylim(0, ytop * 1.12); bx.set_xlim(-0.05, tmax)
bx.legend(loc="upper right", bbox_to_anchor=(1.0, 0.62), fontsize=8)
panel_tag(bx, "B")
bx.set_title("Engaged = within 1.5 yd for at least 4 frames inside the window")

fig.suptitle(f"F1. An engaged pass-protection rep: {nb} (OL) vs {nr} (rusher), {sel['blocker_team']} vs {sel['rusher_team']}, "
             f"{season} week {sel['week']}\nthey stayed within 1.5 yd for {int(sel['n_close_150'])} of {int(sel['n_common_frames'])} "
             f"frames in the window; outcome: {outcome}" + chr(10) + "(median-duration single-rusher, no-double-team engaged pair)",
             x=0.01, ha="left", y=0.995, fontsize=10.5, fontweight="bold")
fig.subplots_adjust(top=0.88, left=0.08, right=0.97, bottom=0.07)

out = both.reset_index().rename(columns={"t": "t_since_snap_s"})
out.insert(0, "game_id", g); out.insert(1, "play_id", p)
out["blocker_nfl_id"], out["rusher_nfl_id"] = b, r
tt = out.t_since_snap_s
out["bx_rel"], out["by_rel"] = tx(B).reindex(tt).values, ty(B).reindex(tt).values
out["rx_rel"], out["ry_rel"] = tx(R).reindex(tt).values, ty(R).reindex(tt).values
out["window_start_s"], out["window_end_s"], out["window_end_reason"] = ts, te, end_reason
out = out.rename(columns={"d": "pair_distance_yd"})
save(fig, "F1_engaged_rep", out.drop(columns=["x_b", "y_b", "x_r", "y_r"]))
