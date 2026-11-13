"""EXTRA (not in the writeup set; replaced by f5_anatomy.py) matchup surface: predicted pressure probability over blocker composite x rusher composite for an average rep,
faceted INTERIOR vs EDGE.

Usage: .venv\\Scripts\\python scripts\\figures\\f5_surface.py [results_dir]   (default: data/processed/confirmatory_sim/201; real run: reports)
Reads:
  confirmatory_results.json : mode ('simulate' -> SIMULATED title / sim_ prefix), surface.draws (optional footnote)
  surface_S2s.csv           : columns edge (0 = interior line, 1 = edge), c_R_z, c_B_z (composite-z units, -2..2 by 0.25),
                              median, lo90, hi90 (posterior summary of the predicted pressure probability)
Sequential single-hue ramp (probability is a magnitude); same colour scale in both facets.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from _common import *  # noqa

style()
d, j, sim, tdir = parse_results_args(__doc__)
s = pd.read_csv(d / "surface_S2s.csv")
vmin, vmax = float(s["median"].min()), float(s["median"].max())
fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), sharey=True)
for ax, (edge, lab) in zip(axes, ((0, "Interior rushers (DT / NT)"), (1, "Edge rushers (DE / OLB)"))):
    g = s[s.edge == edge]
    piv = g.pivot(index="c_R_z", columns="c_B_z", values="median").sort_index().sort_index(axis=1)
    xs, ys = piv.columns.values, piv.index.values
    im = ax.imshow(piv.values, origin="lower", cmap=SEQ_CMAP, vmin=vmin, vmax=vmax, aspect="equal",
                   extent=[xs[0] - 0.125, xs[-1] + 0.125, ys[0] - 0.125, ys[-1] + 0.125])
    cs = ax.contour(xs, ys, piv.values, levels=np.linspace(vmin, vmax, 7)[1:-1], colors=SURFACE, linewidths=0.8, alpha=0.9)
    ax.clabel(cs, fmt=lambda v: f"{v * 100:.0f}%", fontsize=7.5, inline=True)
    ax.grid(False)
    ax.set_title(lab)
    ax.set_xlabel("blocker composite (z; right = more athletic blocker)")
    ax.plot([0], [0], marker="+", color=INK, ms=9, mew=1.4)
    for cr, cb_, dx, dy in ((2, -2, 0.1, -0.35), (-2, 2, -0.1, 0.1), (-2, -2, 0.1, 0.1), (2, 2, -0.1, -0.35)):
        r = g[(g.c_R_z == cr) & (g.c_B_z == cb_)].iloc[0]
        ax.annotate(f"{r['median'] * 100:.1f}%\n[{r.lo90 * 100:.1f}, {r.hi90 * 100:.1f}]", (cb_ - 0.45 * np.sign(cb_), cr - 0.25 * np.sign(cr)),
                    xytext=(0, 0), textcoords="offset points", fontsize=7.5, ha="center", va="center",
                    color=INK if r["median"] < (vmin + vmax) / 2 + 0.01 else "#ffffff",
                    bbox=dict(boxstyle="round,pad=0.15", fc="none", ec="none"))
axes[0].set_ylabel("rusher composite (z; up = more athletic rusher)")
cax = fig.add_axes([0.91, 0.2, 0.014, 0.55])
cb = fig.colorbar(im, cax=cax)
cb.set_label("predicted P(pressure) on an average rep"); cb.outline.set_visible(False)
cb.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
fig.suptitle(f"{sim_tag(sim)}F5. Predicted pressure probability by matchup: rusher composite x blocker composite",
             x=0.01, ha="left", y=0.99, fontsize=11, fontweight="bold", color=(RED if sim else INK))
fig.text(0.01, 0.925, "Model M1-S2s, average rep (context at its mean, random effects at 0). Corner cells show the posterior median [90% interval]. "
         "+ marks an average-vs-average matchup.", fontsize=8.5, color=INK2)
fig.subplots_adjust(top=0.85, left=0.07, right=0.89, bottom=0.12)
save(fig, "extra_F5_surface" if not sim else "sim_extra_F5_surface", s)
