"""F2 'the engine is real': (A) coherence of the detected engaged pair with the credited pressure, engaged vs non-engaged;
(B) the draft-pick effect on engaged vs non-engaged pairs, from the frozen confirmatory run.

Panel A (recomputed, matches reports/feasibility_c3.md G1): among pairs whose BLOCKER was credited with a pressure allowed,
the share in which the paired RUSHER also has a non-null time_to_pressure; within engaged_primary pairs vs the others.
Inputs: data/processed/engaged_pairs.parquet joined to data/processed/engaged_outcomes_SEALED.parquet (the outcome columns
pressure_allowed and rusher_time_to_pressure, built from player_play; keys game_id, play_id, blocker, rusher).
CI: 1,000 play-cluster bootstrap resamples, seed 2027 (as in the feasibility note).
Panel B: reports/confirmatory_results.json -> pc2.summary (M2 d_lpick on set P) and placebo.beta_lpd_PL (M2-PL on the placebo
set), posterior median and 95% interval, log-odds per SD of the log-pick difference.
Run: .venv\\Scripts\\python scripts\\figures\\f2_engine_is_real.py [path to confirmatory_results.json]
"""
import json
import sys

import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt

from _common import *  # noqa

style()
args = [a for a in sys.argv[1:] if not a.startswith("-")]
jp = args[0] if args else str(ROOT / "reports" / "confirmatory_results.json")
j = json.load(open(jp, encoding="utf-8"))

K = ["game_id", "play_id", "blocker_nfl_id", "rusher_nfl_id"]
p = pl.read_parquet(PROC / "engaged_pairs.parquet").select(K + ["engaged_primary"])
o = pl.read_parquet(PROC / "engaged_outcomes_SEALED.parquet").select(K + ["pressure_allowed", "rusher_time_to_pressure"])
d = p.join(o, on=K, how="left").filter(pl.col("pressure_allowed") == True)  # noqa: E712
d = d.with_columns(pl.col("rusher_time_to_pressure").is_not_null().alias("coh")).to_pandas()
d["play"] = d.game_id.astype(str) + "_" + d.play_id.astype(str)

rng = np.random.default_rng(2027)
plays = d.play.unique()
idx = {pl_: np.where(d.play.values == pl_)[0] for pl_ in plays}
rows = []
res = {}
for flag, lab in ((True, "Engaged pairs"), (False, "Non-engaged pairs")):
    sub = d[d.engaged_primary == flag]
    res[flag] = (int(sub.coh.sum()), len(sub), sub.coh.mean())
coh = d.coh.values.astype(float); eng = d.engaged_primary.values
boot = {True: [], False: []}
for _ in range(1000):
    pick = rng.choice(len(plays), len(plays), replace=True)
    ii = np.concatenate([idx[plays[k]] for k in pick])
    for flag in (True, False):
        m = eng[ii] == flag
        boot[flag].append(coh[ii][m].mean())
ci = {f: np.percentile(v, [2.5, 97.5]) for f, v in boot.items()}
for flag, lab in ((True, "Engaged pairs"), (False, "Non-engaged pairs")):
    k, n, sh = res[flag]
    rows.append(dict(panel="A_coherence", group=lab, k=k, n=n, share=sh, lo=ci[flag][0], hi=ci[flag][1]))
    print(f"{lab}: {k}/{n} = {sh * 100:.1f}%  95% cluster CI [{ci[flag][0] * 100:.1f}, {ci[flag][1] * 100:.1f}]")

pc2 = j["pc2"]["summary"]; pl_ = j["placebo"]["beta_lpd_PL"]
for lab, v in (("Engaged reps (model M2, set P)", pc2), ("Non-engaged pairs (placebo, model M2-PL)", pl_)):
    rows.append(dict(panel="B_pick_effect", group=lab, estimate=v["median"], lo=v["lo"], hi=v["hi"]))
out = pd.DataFrame(rows)

fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 4.9), gridspec_kw=dict(width_ratios=[1, 1.35], wspace=0.55))
A = out[out.panel == "A_coherence"]
cols = [BLUE, MUTED]
for i, (_, r) in enumerate(A.iterrows()):
    ax.bar(i, r.share * 100, width=0.55, color=cols[i])
    ax.plot([i, i], [r.lo * 100, r.hi * 100], color=INK, lw=1.4)
    ax.text(i, r.hi * 100 + 2, f"{r.share * 100:.1f}%\n({int(r.k)} of {int(r.n)})", ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Engaged pairs\n(within 1.5 yd for 4+ frames)", "Non-engaged pairs"])
ax.set_ylim(0, 100); ax.set_ylabel("% of blocker-pressure plays where the paired\nrusher is credited with a pressure too")
ax.grid(axis="x", visible=False)
ax.set_title("A. The detected pair is the credited pair")
B = out[out.panel == "B_pick_effect"]
ys = [0.0, 1.0]
for y, (_, r), c in zip(ys, B.iterrows(), (BLUE, MUTED)):
    bx.plot([r.lo, r.hi], [y, y], color=c, lw=2.6, solid_capstyle="round")
    bx.scatter(r.estimate, y, s=70, color=c, zorder=3, edgecolor=SURFACE, linewidth=1)
    bx.text(r.estimate, y - 0.12, f"{r.estimate:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]", va="bottom", ha="center", fontsize=8.5, color=INK2)
bx.axvline(0, color=INK2, lw=1)
bx.set_yticks(ys); bx.set_yticklabels(["Engaged reps", "Non-engaged pairs\n(placebo)"])
bx.set_ylim(1.6, -0.6); bx.grid(axis="y", visible=False)
bx.set_xlim(-0.36, 0.2)
bx.set_xlabel("effect of the rusher-minus-blocker draft-pick gap on pressure\n(log-odds per SD of the log-pick difference; negative = better-drafted rusher wins more)")
bx.set_title("B. The draft-pick effect is clearest on engaged reps")
ratio = B.estimate.iloc[1] / B.estimate.iloc[0]
bx.text(0.0, -0.27, f"On non-engaged pairs the effect is about {ratio:.1f} times as large\nand not distinguishable from zero; the two intervals overlap.\nA better-drafted rusher wins more engaged reps.", transform=bx.transAxes, fontsize=8.5, color=INK2, va="top")
fig.suptitle("F2. The positive control: detected pairs are the credited pairs, and draft slot predicts who wins an engaged rep",
             x=0.01, ha="left", y=0.99, fontsize=10.5, fontweight="bold")
fig.subplots_adjust(top=0.82, left=0.1, right=0.97, bottom=0.26)
panel_tag(ax, ""); panel_tag(bx, "")
save(fig, "F2_engine_is_real", out)
