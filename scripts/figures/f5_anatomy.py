"""F5 'Anatomy of the surprise': the blocker-side estimate under the frozen S1 and the exploratory follow-ups, one forest panel.

Usage: .venv\\Scripts\\python scripts\\figures\\f5_anatomy.py [results_dir]   (default: reports; real run only)
Reads (nothing hard-coded; every number comes from these files):
  <data dir>/forest_data.csv                 : (M1-S1, c_B) and (M1-S1, c_R) bayes rows (frozen)
  <tables dir>/R8.csv                        : row ID == SA13, column 'Bayes beta_gap [95%]' (frozen 5-frame sensitivity)
  <tables dir>/R5.csv                        : row ID == S1, Estimand == c_B, column 'GLM [95% CI]' (kappa-calibrated CI = first interval)
  reports/exploratory/tables/x2_permutation_summary.csv : term c_B -> beta_obs, p_two_studentized
  reports/exploratory/tables/x1_fits.csv    : fit (a), (c), (d) rows: est, lo, hi, n
  reports/exploratory/tables/x3_glm_fits.csv: fit (c) rows c_B (3-frame) and c_B5 (5-frame part); fit (e) blocker_back_disp_05s
Exploratory intervals: X1 = the table's blocker-clustered t(76) CIs; X2 and X3 rows = kappa-calibrated CIs (X3: lo_k, hi_k).
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from _common import *  # noqa

import sys
if len([a for a in sys.argv[1:] if not a.startswith("-")]) == 0:
    sys.argv.append(str(ROOT / "reports"))
style()
d, j, sim, tdir = parse_results_args(__doc__)
ET = ROOT / "reports" / "exploratory" / "tables"

forest = pd.read_csv(d / "forest_data.csv")
r5 = pd.read_csv(tdir / "R5.csv")
r8 = pd.read_csv(tdir / "R8.csv")
x1 = pd.read_csv(ET / "x1_fits.csv")
x2 = pd.read_csv(ET / "x2_permutation_summary.csv")
x3 = pd.read_csv(ET / "x3_glm_fits.csv")


def fd(model, term):
    r = forest[(forest.model == model) & (forest.term == term) & (forest.kind == "bayes")].iloc[0]
    return float(r.estimate), float(r.lo), float(r.hi)


def x1row(fit_prefix, term):
    r = x1[x1.fit.str.startswith(fit_prefix) & (x1.term == term)].iloc[0]
    return float(r.est), float(r.lo), float(r.hi), int(r.n)


cB, cR = fd("M1-S1", "c_B"), fd("M1-S1", "c_R")
sa13 = parse_est(r8[r8.ID == "SA13"].iloc[0]["Bayes beta_gap [95%]"])
glm_cB = parse_est(r5[(r5.ID == "S1") & (r5.Estimand == "c_B")].iloc[0]["GLM [95% CI]"])  # (est, kappa lo, kappa hi)
p2 = x2[x2.term == "c_B"].iloc[0]
a = x1row("(a)", "c_B"); c_ = x1row("(c)", "c_B"); dint = x1row("(d)", "cB_x_eng")
k3 = x3[x3.fit.str.startswith("(c) k3") & (x3.term == "c_B")].iloc[0]
k5 = x3[x3.fit.str.startswith("(c) k3") & (x3.term == "c_B5")].iloc[0]
dep = x3[x3.fit.str.contains("blocker_back_disp_05s")].iloc[0]

rows = [  # part, label, (est, lo, hi), note
    ("FROZEN", "Blocker composite c_B, engaged reps (S1)", cB, ""),
    ("FROZEN", "Rusher composite c_R, engaged reps (S1)", cR, ""),
    ("FROZEN", "Gap, 5-frame-smoothed composites (SA13, pre-registered sensitivity)", sa13, ""),
    ("EXPLORATORY", f"c_B GLM estimate (frozen) with exploratory calibrated p = {p2.p_two_studentized:.4f} (X2)",
     (float(p2.beta_obs), glm_cB[1], glm_cB[2]), "GLM, kappa CI"),  # frozen estimate, exploratory p
    ("EXPLORATORY", f"c_B on the same blockers' all pass-pro snaps (X1 a), n = {a[3]:,}", a[:3], ""),
    ("EXPLORATORY", f"c_B on their non-engaged snaps (X1 c), n = {c_[3]:,}", c_[:3], ""),
    ("EXPLORATORY", "Engaged x c_B interaction, all snaps (X1 d)", dint[:3], ""),
    ("EXPLORATORY", "c_B, 3-frame-specific part (X3 c)", (float(k3.est), float(k3.lo_k), float(k3.hi_k)), "kappa CI"),
    ("EXPLORATORY", "c_B, 5-frame part (X3 c)", (float(k5.est), float(k5.lo_k), float(k5.hi_k)), "kappa CI"),
]
df = pd.DataFrame([(p, l, *v, n) for p, l, v, n in rows], columns=["part", "term", "estimate", "lo", "hi", "note"])
colour = {0: ORANGE, 1: ORANGE, 2: BLUE, 3: ORANGE}   # row 3 (X2): frozen estimate, drawn in the frozen S1 colour
ypos, y = [], 0.0
for i, r in df.iterrows():
    if i == 3:
        y += 1.6
    ypos.append(y); y += 1
df["y"] = ypos

fig, ax = plt.subplots(figsize=(12, 6.6))
ax.axvline(0, color=INK2, lw=1)
for i, r in df.iterrows():
    c = colour.get(i, MUTED)
    ax.plot([r.lo, r.hi], [r.y, r.y], color=c, lw=2.3, solid_capstyle="round")
    ax.scatter(r.estimate, r.y, s=58, color=c, zorder=3, edgecolor=SURFACE, linewidth=1)
    ax.text(1.02, r.y, f"{r.estimate:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]" + (f"  ({r.note})" if r.note else ""),
            transform=ax.get_yaxis_transform(), va="center", fontsize=8.5, color=INK2)
ax.set_yticks(df.y); ax.set_yticklabels(df.term, fontsize=8.8)
ax.set_ylim(df.y.max() + 1.6, -1.1)
ax.grid(axis="y", visible=False)
xl = min(df.lo.min(), -0.1) - 0.05; xh = max(df.hi.max(), 0.1) + 0.05
ax.set_xlim(xl, xh)
yd = df.y[3] - 0.8
ax.axhline(yd, color=AXIS, lw=1)
ax.text(xl, -0.75, "FROZEN (pre-registered)", fontsize=9, fontweight="bold", color=INK2, va="center")
ax.text(xl, yd + 0.05, "EXPLORATORY (after unsealing; specification_log X1-X3)", fontsize=9, fontweight="bold", color=INK2, va="top")
ax.set_xlabel("log-odds of a pressure per SD of the term (frozen: posterior median and 95% interval; exploratory: estimate and 95% CI)")
fig.text(0.01, 0.112, f"Set depth, X3 (e): blocker composite vs in-game set depth at 0.5 s = {float(dep.est):+.3f} outcome SD "
        f"[{float(dep.lo):+.3f}, {float(dep.hi):+.3f}] (a different unit, so not drawn on this axis).",
        fontsize=8.5, color=INK2, va="top")
fig.text(0.01, 0.075, "Interval types: frozen rows Bayes 95%; GLM rows kappa-calibrated; X1 rows blocker-clustered t. X1 standardises c_B over distinct blockers, so its per-SD unit differs slightly from the rep-level one.",
         fontsize=8, color=INK2, va="top")
fig.text(0.01, 0.045, f"The blocker-side signal is concentrated in the 3-frame-specific part of the trait and is not distinguishable from zero across the same blockers' full seasons ({a[0]:+.3f} [{a[1]:+.3f}, {a[2]:+.3f}]).",
         fontsize=9.3, color=INK, va="top", fontweight="bold")
fig.suptitle("F5. Anatomy of the surprise: where the blocker-side effect shows up, and where it does not",
             x=0.01, ha="left", y=0.985, fontsize=11, fontweight="bold")
fig.subplots_adjust(left=0.36, right=0.74, top=0.92, bottom=0.24)
out = df.drop(columns=["y"]).copy()
out = pd.concat([out, pd.DataFrame([dict(part="EXPLORATORY", term="Set depth at 0.5 s vs c_B (X3 e), outcome SD", estimate=float(dep.est),
                                          lo=float(dep.lo), hi=float(dep.hi), note="not drawn; outcome-SD units")])], ignore_index=True)
save(fig, "F5_anatomy", out)
