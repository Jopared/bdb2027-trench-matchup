"""F6 robustness, three panels: (A) permutation null of the studentized statistic with the observed value, (B) placebo
(non-engaged) vs engaged estimate, (C) sign robustness across the pre-listed sensitivity fits (table R8).

Usage: .venv\\Scripts\\python scripts\\figures\\f6_robustness.py [results_dir]   (default: data/processed/confirmatory_sim/201; real run: reports)
Reads:
  permutation_null.csv      : columns k, beta_star, t_star (one row per permutation); panel A draws t_star
  confirmatory_results.json : mode; perm.{t_obs, p_two, p_coef, nperm};
      units.M1.logodds.{median, lo, hi}  (engaged Bayes estimate, the primary row of panel C)
      glm_gap.M1.{est, ci_kappa}, placebo.bayes_gap_PL.{median, lo, hi}, placebo.glm_gap_PL.{est, ci_kappa}, placebo.ratio_gap
      cv.sets.*.ll, cv.reps   (not drawn; written to the CSV as held-out log loss minus I0, millinats per rep)
  tables/R8.csv (tables dir resolved by _common): columns ID, Description, 'GLM beta_gap [95% CI]', 'Bayes beta_gap [95%]',
      'Discordant?'. The Bayes column is used where present, otherwise the GLM kappa-calibrated interval (first interval).
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from _common import *  # noqa

style()
d, j, sim, tdir = parse_results_args(__doc__)
null = pd.read_csv(d / "permutation_null.csv")
pm = j["perm"]
r8 = pd.read_csv(tdir / "R8.csv")

fig = plt.figure(figsize=(13.5, 8.6))
gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.25], hspace=0.62, wspace=0.62)

# ---- A permutation null of the studentized statistic
ax = fig.add_subplot(gs[0, 0])
t = null.t_star.values
t_obs = float(pm["t_obs"])
n_ext = int((np.abs(t) >= abs(t_obs)).sum())
p_calc = (n_ext + 1) / (len(t) + 1)
print(f"panel A: {n_ext} of {len(t)} |t*| >= |t_obs|; recomputed p = {p_calc:.4f}; json p_two = {pm['p_two']:.4f}")
bins = np.linspace(min(t.min(), t_obs) - 0.2, max(t.max(), abs(t_obs)) + 0.2, 41)
n_, b_, patches = ax.hist(t, bins=bins, color=AXIS, edgecolor=SURFACE, linewidth=0.8)
for pa, lo_b, hi_b in zip(patches, b_[:-1], b_[1:]):          # shade bins in the two-sided tail |t*| >= |t_obs|
    if hi_b <= -abs(t_obs) or lo_b >= abs(t_obs):
        pa.set_facecolor(ORANGE)
ax.axvline(t_obs, color=BLUE, lw=2.2)
ax.axvline(-t_obs, color=BLUE, lw=1.2, ls="--")
ax.axvline(0, color=MUTED, lw=0.8, ls=":")
ax.text(t_obs - 0.08, ax.get_ylim()[1] * 0.97, "observed" + chr(10) + f"t = {t_obs:.2f}", color=BLUE, va="top", ha="right", fontsize=9)
ax.set_xlim(-6.2, 5.2)
ax.set_ylabel("permutations")
ax.set_xlabel("studentized gap statistic t* under permuted gaps" + chr(10) + f"orange: |t*| >= |observed|, {n_ext} of {len(t)} permutations" + chr(10) +
              f"two-sided studentized p = {pm['p_two']:.4f} (registered Q2)" + chr(10) + f"coefficient-based p = {pm['p_coef']:.4f}")
ax.set_title("A. Permutation null (studentized)")

# ---- B placebo
bx = fig.add_subplot(gs[1, 0])
bm = j["units"]["M1"]["logodds"]; pb = j["placebo"]["bayes_gap_PL"]
gm = j["glm_gap"]["M1"]; gp = j["placebo"]["glm_gap_PL"]
pts = [("Bayes", "Engaged reps", bm["median"], bm["lo"], bm["hi"], BLUE),
       ("Bayes", "Non-engaged (placebo)", pb["median"], pb["lo"], pb["hi"], MUTED),
       ("GLM", "Engaged reps", gm["est"], gm["ci_kappa"][0], gm["ci_kappa"][1], BLUE),
       ("GLM", "Non-engaged (placebo)", gp["est"], gp["ci_kappa"][0], gp["ci_kappa"][1], MUTED)]
ys = [3.2, 2.5, 1.0, 0.3]
for (m, lab, e, lo, hi, c), y in zip(pts, ys):
    bx.plot([lo, hi], [y, y], color=c, lw=2.4, solid_capstyle="round")
    bx.scatter(e, y, s=55, color=c, zorder=3, edgecolor=SURFACE, linewidth=1)
    bx.text(hi + 0.02, y, f"{e:+.2f} [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=8, color=INK2)
bx.axvline(0, color=INK2, lw=1)
bx.set_yticks(ys); bx.set_yticklabels([f"{p[0]}: " + ("engaged" if p[1].startswith("Engaged") else "placebo") for p in pts], fontsize=8.5)
bx.set_ylim(-0.4, 3.9); bx.grid(axis="y", visible=False)
bx.set_title("B. Placebo: gap on non-engaged pairs")
bx.set_xlabel("gap coefficient (log-odds per SD)" + chr(10) + f"placebo / engaged = {j['placebo']['ratio_gap']:.2f} (Bayes medians)")
bx.set_xlim(min(-0.45, min(p[3] for p in pts) - 0.05), max(p[4] for p in pts) + 0.5)
bx.invert_yaxis()

# ---- C sensitivity forest (R8 order; primary on top)
cx = fig.add_subplot(gs[:, 1])
short = {"SA1": "1.25 yd / 4 frames", "SA2": "2.0 yd / 4 frames", "SA3": "1.5 yd / 3 frames", "SA4": "1.5 yd / 6 frames",
         "SA5": "regular season only", "SA6": "no double teams", "SA7": "DE / DT / NT rushers only",
         "SA9": "1 pair per play-blocker", "SA15": "complete 40-time cases", "SA8": "dyad-equal weights (GLM)",
         "SA10": "composite B", "SA11": "composite A, same rows", "SA12": "DL-only (rusher composite)",
         "SA13": "5-frame smoothing", "SA14": "no dropback spline", "SA16": "+ pick asymmetry",
         "SA17": "+ dyad random intercept", "SA18_0.5": "prior N(0, 0.5)", "SA18_2.5": "prior N(0, 2.5)"}
rows = [("M1", "M1 primary (H1)", bm["median"], bm["lo"], bm["hi"], "primary")]
for _, r in r8.iterrows():
    bt = str(r["Bayes beta_gap [95%]"])
    est = parse_est(bt) if bt.strip()[0] in "-0123456789" else parse_est(r["GLM beta_gap [95% CI]"])
    kind = "discordant" if str(r["Discordant?"]).strip().lower() == "yes" else "ok"
    rows.append((r["ID"], f"{r['ID']}  {short.get(r['ID'], r['Description'])}", *est, kind))
df = pd.DataFrame(rows, columns=["id", "label", "estimate", "lo", "hi", "kind"])
sens = df[df.id != "M1"]
n_incl = int(((sens.lo <= 0) & (sens.hi >= 0)).sum()); n_all = len(sens)
n_disc = int((sens.kind == "discordant").sum())
print(f"panel C: {n_incl} of {n_all} sensitivity intervals include zero ({n_disc} flagged discordant)")
cmap = {"primary": BLUE, "ok": MUTED, "discordant": ORANGE}
df["y"] = np.arange(len(df)) + (df.index > 0) * 0.6
cx.axvline(0, color=INK2, lw=1)
for _, r in df.iterrows():
    c = cmap[r.kind]
    cx.plot([r.lo, r.hi], [r.y, r.y], color=c, lw=2.2, solid_capstyle="round")
    cx.scatter(r.estimate, r.y, s=48, color=c, zorder=3, edgecolor=SURFACE, linewidth=1)
    cx.text(1.02, r.y, f"{r.estimate:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]", transform=cx.get_yaxis_transform(), va="center", fontsize=8, color=INK2)
cx.set_yticks(df.y); cx.set_yticklabels(df.label, fontsize=8.3)
cx.invert_yaxis(); cx.grid(axis="y", visible=False)
cx.set_xlabel("gap coefficient (log-odds per SD); Bayes 95% interval (GLM kappa CI for SA8)")
cx.set_title(f"C. Sign robustness: {n_incl} of {n_all} pre-listed sensitivity intervals include zero")
cx.text(0.0, -0.075, "orange = the discordant sensitivities (SA12, SA13)" if n_disc else "", transform=cx.transAxes, fontsize=8, color="#a63a12", va="top")

cv = j["cv"]
ll = {k: v["ll"] for k, v in cv["sets"].items()}
cv_rows = [dict(panel="C_cv_not_drawn", info_set=k, ll=v, delta_vs_I0_millinats=(v - ll["I0"]) * 1000) for k, v in ll.items()]
fig.suptitle(f"{sim_tag(sim)}F6. Robustness of the athletic-gap effect: permutation, placebo and sensitivity checks",
             x=0.01, ha="left", y=0.99, fontsize=11, fontweight="bold", color=(RED if sim else INK))
fig.text(0.01, 0.015, "Out-of-sample: every richer information set did worse than context-only; a pick-sized effect is worth about 1 millinat per rep, so CV could not discriminate.",
         fontsize=8.8, color=INK2, ha="left", va="bottom")
fig.subplots_adjust(top=0.92, left=0.13, right=0.78, bottom=0.12)
panel_tag(ax, ""); panel_tag(bx, ""); panel_tag(cx, "")
csv = pd.concat([
    null.assign(panel="A_null", t_obs=t_obs),
    pd.DataFrame([dict(panel="B_placebo", model=p[0], group=p[1], estimate=p[2], lo=p[3], hi=p[4]) for p in pts]),
    df.drop(columns=["y"]).assign(panel="C_sensitivity"),
    pd.DataFrame(cv_rows)], ignore_index=True)
save(fig, fig_name("F6", sim), csv)
