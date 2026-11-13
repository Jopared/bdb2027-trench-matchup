"""F4 forest plot of rep-level effects per SD (log-odds of a pressure), with the registered MDE band and the SESOI region.

Usage: .venv\\Scripts\\python scripts\\figures\\f4_forest.py [results_dir]   (default: data/processed/confirmatory_sim/201; real run: reports)
Reads (exact layout assumed):
  confirmatory_results.json : mode ('simulate' -> SIMULATED title and sim_ file prefix), h1_final.label,
                              units.M1.p_lt_sesoi (P(beta < 0.10)), units.M1.pe.k.{median, lo, hi} (pick-difference SDs per gap SD)
  forest_data.csv           : columns model, term, estimate, lo, hi, kind ; bayes rows (M1,gap) (M2,gap) (M1-A,gap) (M2-A,gap)
                              (M1-S1,c_R) (M1-S1,c_B); per-term rows (d_*) are used when present
  tables/R4.csv (tables dir resolved by _common): only used when forest_data.csv lacks the per-term rows; columns
                              Model, Term, 'Bayes median [95%]' ; rows (M1, d_weight|d_arm|d_forty|d_ten|d_shuttle|d_cone|d_ngs),
                              (M2, d_lpick)   [text 'est [lo, hi]' parsed]
Official measures enter the models as raw rusher-minus-blocker values (times: higher = slower), so for times a negative
coefficient means the faster player wins. There is no draft-slot axis: the slot conversion is unstable in the frozen run
(R3); the pick-difference-SD equivalent (k) is printed in the H1 row label instead.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from _common import *  # noqa

style()
d, j, sim, tdir = parse_results_args(__doc__)
forest = pd.read_csv(d / "forest_data.csv")
r4 = pd.read_csv(tdir / "R4.csv")
SESOI = 0.10


def fd(model, term):
    r = forest[(forest.model == model) & (forest.term == term) & (forest.kind == "bayes")].iloc[0]
    return float(r.estimate), float(r.lo), float(r.hi)


def r4v(model, term):
    hit = forest[(forest.model == model) & (forest.term == term) & (forest.kind == "bayes")]
    if len(hit):                      # per-term rows present in forest_data.csv: use them directly
        return float(hit.estimate.iloc[0]), float(hit.lo.iloc[0]), float(hit.hi.iloc[0])
    r = r4[(r4.Model == model) & (r4.Term == term)].iloc[0]
    return parse_est(r["Bayes median [95%]"])


pk = j["units"]["M1"]["pe"]["k"]
p_sesoi = float(j["units"]["M1"]["p_lt_sesoi"])
rows = [  # (group, label, (est, lo, hi), model, extra right-hand note)
    ("Draft slot", "Draft-pick difference (R - B, log pick)", r4v("M2", "d_lpick"), "M2", ""),
    ("Size", "Weight difference (R - B)", r4v("M1", "d_weight"), "M1", ""),
    ("Size", "Arm length difference (R - B)", r4v("M1", "d_arm"), "M1", ""),
    ("Stopwatch", "40-yard time difference (R - B)", r4v("M1", "d_forty"), "M1", ""),
    ("Stopwatch", "10-yard split time difference (R - B)", r4v("M1", "d_ten"), "M1", ""),
    ("Stopwatch", "Short-shuttle time difference (R - B)", r4v("M1", "d_shuttle"), "M1", ""),
    ("Stopwatch", "3-cone time difference (R - B)", r4v("M1", "d_cone"), "M1", ""),
    ("Stopwatch", "NGS athleticism score difference (R - B)", r4v("M1", "d_ngs"), "M1", ""),
    ("Tracking", "Tracking gap (primary, H1)", fd("M1", "gap"), "M1",
     f"\nP(beta < 0.10) = {p_sesoi:.3f}\nk = {pk['median']:+.2f} [{pk['lo']:+.2f}, {pk['hi']:+.2f}] pick SDs"),
    ("Tracking", "Tracking gap, pick controlled (H2)", fd("M2", "gap"), "M2", ""),
    ("Tracking", "Composite A gap, no pick (S0)", fd("M1-A", "gap"), "M1-A", ""),
    ("Tracking", "Composite A gap, pick controlled (S0)", fd("M2-A", "gap"), "M2-A", ""),
    ("S1", "Rusher composite c_R", fd("M1-S1", "c_R"), "M1-S1", ""),
    ("S1", "Blocker composite c_B", fd("M1-S1", "c_B"), "M1-S1", ""),
]
df = pd.DataFrame([(g, l, *v, m, n) for g, l, v, m, n in rows],
                  columns=["group", "term", "estimate", "lo", "hi", "model", "note"])
gcol = {"Draft slot": INK2, "Size": MUTED, "Stopwatch": MUTED, "Tracking": BLUE, "S1": ORANGE}

fig, ax = plt.subplots(figsize=(11.5, 7.6))
ypos, y, prev = [], 0.0, None
for g in df.group:
    if prev is not None and g != prev:
        y += 0.9 if g != "S1" else 1.5
    ypos.append(y); y += 1; prev = g
df["y"] = ypos
lo_x = min(df.lo.min(), -MDE) - 0.05; hi_x = max(df.hi.max(), MDE, SESOI) + 0.07
_g = df[df.group == "Tracking"].y
ax.fill_betweenx([_g.min() - 0.5, _g.max() + 0.5], -MDE, MDE, color=ORANGE, alpha=0.12, lw=0)   # the MDE applies to the gap rows only
ax.axvspan(SESOI, hi_x, color=AQUA, alpha=0.13, lw=0)
ax.axvline(0, color=INK2, lw=1)
for _, r in df.iterrows():
    c = gcol[r.group]
    ax.plot([r.lo, r.hi], [r.y, r.y], color=c, lw=2.2, solid_capstyle="round")
    ax.scatter(r.estimate, r.y, s=55, color=c, zorder=3, edgecolor=SURFACE, linewidth=1)
    ax.text(1.02, r.y, f"{r.estimate:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]{r.note}", transform=ax.get_yaxis_transform(),
            va="center", fontsize=8.5, color=INK2)
ax.set_yticks(df.y); ax.set_yticklabels(df.term)
ax.set_ylim(df.y.max() + 0.8, -1.0)
ax.grid(axis="y", visible=False)
ax.set_xlim(lo_x, hi_x)
ys1 = df[df.group == "S1"].y.min()
ax.axhline(ys1 - 0.85, color=AXIS, lw=0.9)
ax.text(lo_x, ys1 - 0.95, "Which side carries it (S1)", fontsize=8.5, fontweight="bold", color=INK2, va="bottom")
ysT = df[df.group == "Tracking"].y.min()
ax.text(-MDE, _g.min() - 0.62, f"MDE -{MDE}", color="#a63a12", fontsize=8, va="center", ha="right")
ax.text(MDE, _g.min() - 0.62, f"MDE +{MDE}", color="#a63a12", fontsize=8, va="center", ha="left")
ax.text(hi_x, 1.5, "beta >= 0.10:" + chr(10) + "hypothesised" + chr(10) + "region ", color="#0f6b4b", fontsize=8, va="center", ha="right")
ax.set_xlabel("log-odds of a pressure per SD of the term (posterior median and 95% interval)")
ax.legend([Patch(facecolor=ORANGE, alpha=0.18), Patch(facecolor=AQUA, alpha=0.3)],
          [f"registered minimum detectable effect of the gap, +/-{MDE} (gap rows only)", f"smallest effect of interest, beta >= {SESOI}"],
          loc="upper center", bbox_to_anchor=(0.5, -0.09), fontsize=8.5, ncol=2)
label = j.get("h1_final", {}).get("label", "")
fig.suptitle(f"{sim_tag(sim)}F4. The tracked gap against the club's other Combine measures and draft slot",
             x=0.01, ha="left", y=0.985, fontsize=11, fontweight="bold", color=(RED if sim else INK))
fig.text(0.01, 0.915, f"Registered verdict on H1: {label}." + chr(10) +
         "Effects are per SD, in pressure log-odds (positive = rusher wins more). Pick, H2 and S0 (pick) rows come from pick-controlled models, the rest from M1." + chr(10) +
         "Official measures enter as raw rusher-minus-blocker values: for times a negative coefficient means the faster player wins." + chr(10) +
         "Composites: higher = more athletic; a positive blocker-composite coefficient means quicker-reversing blockers allowed more pressure." + chr(10) +
         "S0 = pre-registered sensitivity composite A (registered composite plus the 40 acceleration shape).",
         fontsize=8.3, color=INK2, ha="left", va="top")
fig.subplots_adjust(left=0.27, right=0.72, top=0.79, bottom=0.14)
save(fig, fig_name("F4", sim), df.drop(columns=["y"]))
