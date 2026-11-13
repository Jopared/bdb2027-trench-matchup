# Specification log (exploratory analyses after unsealing)

Per `preregistration.md` §13.4, every analysis after the frozen confirmatory run (2026-11-07, script SHA 8d842b70…) is **exploratory**. Each entry gives the date, who ran it, the exact specification, the reason, and the reading rule. Reading rules marked **"not blind"** were written after a preliminary look at the same or a closely related number (E0); they are stated anyway so the final reading is mechanical, but the writeup must not present them as pre-specified.

Common machinery for every engaged-rep entry (E0, X2-X4): import `scripts/confirmatory_analysis.py` read-only (never edit it), build the frame with `AnalysisBase(mode="exploratory", out_root=None).prepare(with_k5=...)`, left-join `engaged_outcomes_SEALED.parquet` on the four keys (validate 1:1), build designs with `make_design` on `Version.X` (P's constants), fit with `glm_mirror` (two-way cluster blocker + rusher − dyad, t(G−1) reference; κ = 1.20 version reported alongside). "M1-S1 GLM" = columns `C_COLS + Q_COLS + [c_R, c_B]` on set P. Reproduction check: M1 GLM gap must be −0.154, κ-CI [−0.308, 0.000]; S1 c_B +0.143, c_R −0.064.

---

## E0 — 2026-11-07 — interpreter scratch checks (already run)

Run by the statistical interpreter from scratch scripts outside the repo, to calibrate `reports/interpretation.md`. Nothing was written to the repo except this log and the interpretation. All are GLMs; CIs are nominal t-reference two-way cluster unless stated; none is a hypothesis test with a claim attached.

| ID | Specification | Result |
|---|---|---|
| E0.1 | Reproduce M1 and M1-S1 GLM | Matched R3/R5 exactly |
| E0.2 | M1-S1 / gap GLM under nested control sets: C; C+size; C+size+NGS; C+size+stopwatch (no NGS); M1 without cone; M1; M1+K | c_B: +0.083, +0.091, +0.110, +0.142, +0.119, +0.143, +0.126. c_R: +0.048, +0.038, −0.026, −0.013, −0.042, −0.064, −0.059. gap: −0.033, −0.054, −0.104, −0.125, −0.124, −0.154, −0.138 |
| E0.3 | Side-specific measure effects in M1-S1: β_R ≈ β_d + β_s, β_B ≈ β_s − β_d (approximate: d and s are separately standardised) | three-cone: rusher −0.225 [−0.452, 0.002], blocker +0.127 [−0.075, 0.328] (both in the *expected* direction for a time); NGS: rusher +0.233 [0.066, 0.400], blocker +0.058 [−0.255, 0.370]; blocker weight −0.171 [−0.381, 0.038] |
| E0.4 | SA13 inputs: player-level r between registered (3-frame) and 5-frame composites in P; M1-S1 with the k5 composites; both blocker versions in one model | Blockers r = 0.779 (n 69); rushers r = 1.000 (D1 unchanged). k5 c_B +0.061 [−0.078, 0.200]; jointly: k3 c_B +0.219 [0.051, 0.386], k5 c_B −0.108 [−0.300, 0.085] |
| E0.5 | O3 value distribution; c_B winsorised at ±2.5; rank-normal c_B; leave-one-blocker-out jackknife of c_B | 69 in-P blockers take 6 values: 0.40 s (14), 0.45 (11), 0.50 (35), 0.55 (3), 0.60 (5), 0.65 (1). Winsorised +0.152; rank-normal +0.167; jackknife range 0.106-0.200 |
| E0.6 | M1-S1 GLM on PL, and on PL split by whether the (game, play, blocker) also appears in P | PL all: c_B +0.103 [0.006, 0.201]. 2,882 of 17,795 PL rows share the blocker-play (identical outcome) with a P rep: c_B +0.268; the other 14,913: c_B +0.054 [−0.062, 0.171] |
| E0.7 | All pass-pro snaps (spec as X1(a) but cubic dropback polynomial, no penalty filter, one-way blocker clustering, normal CIs): 46,194 snaps, 77 OL with a registered composite | c_B (ctx + blocker measures) +0.036 [−0.027, 0.098]; + log pick +0.030 [−0.033, 0.094]; snaps without an engaged cohort pair (39,100) +0.018 [−0.045, 0.080]; snaps with one (7,094) +0.117 [−0.010, 0.244]; c_B × engaged-play +0.052 [−0.028, 0.133], p 0.20 |
| E0.8 | NFL season index (season − draft year) | P reps: rookie 2,804, 2nd 2,587, 3rd 1,823. Engaged reps: c_B rookie +0.046 [−0.087, 0.180], × (2nd+) +0.177 [−0.046, 0.400]. All snaps: × (2nd+) +0.004 [−0.103, 0.111]; by index 0/1/2: +0.035, −0.024, +0.073 |
| E0.9 | Assignment: correlations of c_B with opponent and rep features; M1-S1 + blocker-team FE / defense-team FE / rusher rating (model R posterior mean) / score diff, WP, Q4 / blocker weight², arm², weight×arm; interactions c_B×pos_T, ×edge, ×db1 | Rep-level r with c_R 0.06, rusher log pick 0.04, rusher rating 0.03, edge 0.09, pos_T 0.13, double team 0.07; blocker-level r with mean c_R faced 0.22, double-team share 0.23. c_B with controls: +0.115, +0.151, +0.129, +0.152, +0.167. c_B×pos_T −0.230 [−0.403, −0.056] (G/C +0.268, T ≈ +0.04); ×edge −0.046; ×db1 +0.059. All snaps: c_B×T −0.033 [−0.134, 0.069] |
| E0.10 | Collider ingredients: c_B × z(blocker log pick), c_B × z(log reps) in M1-S1; among the 105 OL with a composite, split at median log pick, r(composite, in P) and r(composite, log1p reps) | c_B×lpick +0.143 [0.042, 0.245] (larger for later picks); ×log reps −0.023. Early half (53): r −0.17 / −0.09; late half (52): r +0.14 / +0.13. All-snap blockers: r(composite, log snaps) 0.05, r(composite, log pick) −0.02 |
| E0.11 | Gaussian M1-S1 GLM, outcome blocker_back_disp_05s / _10s | c_B −0.0058 yd [−0.0205, 0.0090] (−0.02 outcome SD per SD); 1.0 s: −0.0132 [−0.0426, 0.0162] |
| E0.12 | M1-S1 GLM with composite A (on P-A, and on SA11 rows) | P-A: c_B +0.078 [−0.069, 0.225], c_R −0.134 [−0.240, −0.028]; SA11 rows: c_B +0.079, c_R −0.115 [−0.224, −0.005] |
| E0.13 | Analytic (no data): likelihood N(−0.153, 0.075) under priors N(0, s); type-M/S at calibrated SE 0.077; minimum Bayes factor −e·p·ln p | Posterior with N(0, 0.1): −0.098 [−0.216, 0.020]; N(0, 0.2): −0.134 [−0.272, 0.004]. Power / exaggeration if the true effect is 0.15: 0.49 / 1.4×; 0.10: 0.25 / 2.0×; 0.075: 0.16 / 2.6×. Min BF at p = 0.0375: 0.34 (posterior P ≤ 0.75 from 50:50) |

---

## Proposed programme X1-X5 (not yet run; to be run verbatim)

Rules for the executor: create new files only (suggested `scripts/exploratory/x{n}_*.py`, outputs to `reports/exploratory/x{n}.md` and `.csv`); never edit `scripts/confirmatory_analysis.py`, `src/`, `preregistration.md` or any `confirmatory*` output; seed 2027; append the observed numbers under each entry here with the run date; apply the reading rule mechanically and quote it. Each entry should take a few minutes at most.

### X1 — 2026-11-07 — Blocker trait at player level, on all pass-pro snaps (not blind: see E0.7, E0.8)

**Specification.**
- Rows: `player_play` with `pressure_allowed` non-null, `lined_up_position` ∈ {T, G, C}, `pass_result` non-empty, `play_nullified_by_penalty` == "N", joined to `games` with `season_type` ∈ {REG, POST}, non-null `dropback_duration` and `down`; `nfl_id` ∈ `combine_traits` with `combine_position` == "OL" and non-null `composite`.
- Flag `eng_play` = (game_id, play_id, nfl_id) appears in `engaged_pairs` as a blocker with `engaged_primary` true.
- Context: the Harrell 4-knot spline of dropback (knots at the 5/35/65/95th percentiles of these snaps, Gram-Schmidt orthonormalised), the 8 down × distance cells of §5.2, shotgun-or-empty (`offense_formation` ∈ {SHOTGUN, EMPTY}), season dummies, pos_T, pos_C.
- Blocker measures: z over distinct blockers in the set for weight, arm, forty, ten, shuttle, three-cone, NGS athleticism (missing → 0) plus forty/shuttle/cone missing flags. `c_B` = z of `composite` over distinct blockers. Pick block: `log_pick`, `undrafted`.
- Fits: logistic GLM, cluster-robust SE by blocker, t(G−1) reference.
  - (a) ctx + measures + c_B;
  - (b) (a) + pick;
  - (c) (a) on `eng_play` == 0;
  - (d) (a) + eng_play + c_B × eng_play;
  - (e) (a) + exp1 + c_B × exp1, exp1 = (season − draft_year ≥ 1);
  - (f) (a) with c_B replaced by the 5-frame composite (`build_k5_composites()`).
- Also aggregate to blocker-season: observed pressures, and expected pressures from fit (a) without c_B. Report r(c_B, (O − E)/√E) over blocker-seasons with ≥ 100 snaps, and a scatter (figure candidate).

**Reason.** S1's c_B is from 7,214 engaged reps. The same blockers have about 39,000 further pass-pro snaps. If quick mirror reversal really goes with allowing pressure, the effect should show across a blocker's whole season, with or without pick. Item (e) tests explanation (4) (rookie timing).

**Reading rules.**
- R1: If (a)'s 95% CI includes 0 and its upper bound is < 0.15, report "on all pass-pro snaps the blocker trait is bounded at ≤ upper per SD; the engaged-rep blocker effect does not carry over to a blocker's season". If (a) excludes 0 positive, the opposite-sign blocker effect is a general blocker property: report it as the strongest exploratory finding, still labelled exploratory.
- R2: If (d)'s interaction CI includes 0, the engaged and non-engaged estimates are not distinguishable. The pooled (a) is then the best blocker-level estimate, and "matchup-specific" must not be claimed.
- R3: Pick changes nothing in reading unless |(b) − (a)| > 0.03.
- R4: Rookie timing is supported only if (e)'s interaction is negative with a CI excluding 0.
- R5: (f) is reported next to (a) with no reading attached.

**Result (run 2026-11-07, `scripts/exploratory/x1_blocker_all_snaps.py`, runtime 4.1 s; tables `reports/exploratory/tables/x1_*.csv`, figure `figures/exploratory/x1_blocker_season_OE.png`).**
Frame: 46,193 pass-pro snaps (50,747 after the row filters, 46,193 for the 77 OL with a registered composite), pressure rate 8.34%, 7,094 snaps with an engaged cohort pair. Logit coefficients per SD, nominal 95% CI, t(76), SE clustered by blocker:

| Fit | Term | β [95% CI] | p |
|---|---|---|---|
| (a) ctx + measures + c_B | c_B | +0.0365 [−0.0266, 0.0996] | 0.25 |
| (b) (a) + log pick + undrafted | c_B | +0.0311 [−0.0336, 0.0958] | 0.34 |
| (c) (a) on eng_play = 0 (39,099 snaps) | c_B | +0.0188 [−0.0446, 0.0822] | 0.56 |
| (d) (a) + eng_play + c_B × eng_play | c_B (non-engaged) | +0.0268 [−0.0361, 0.0897] | 0.40 |
| | c_B × eng_play | +0.0514 [−0.0312, 0.1339] | 0.22 |
| | c_B on engaged plays | +0.0781 [−0.0199, 0.1761] | 0.12 |
| (e) (a) + exp1 + c_B × exp1 | c_B (rookie) | +0.0296 [−0.0564, 0.1157] | 0.49 |
| | c_B × exp1 | +0.0060 [−0.1029, 0.1149] | 0.91 |
| (f) 5-frame composite (same 46,193 snaps) | c_B(k5) | −0.0229 [−0.0857, 0.0399] | 0.47 |
| (g, not in spec; see note) (a) + c_B × pos_T | c_B × pos_T | −0.0318 [−0.1346, 0.0709] | 0.54 |

Blocker-season O/E (expected from fit (a) without c_B; 100 blocker-seasons with ≥ 100 snaps, 58 blockers): Pearson r(c_B, (O−E)/√E) = +0.128 (nominal Fisher 95% [−0.070, 0.316], p 0.21); Spearman +0.131 (p 0.19).

Mechanical readings: **R1** (a) CI includes 0 and upper 0.0996 < 0.15, so "on all pass-pro snaps the blocker trait is bounded at ≤ 0.10 per SD; the engaged-rep blocker effect does not carry over to a blocker's season". **R2** the (d) interaction CI [−0.031, 0.134] includes 0: engaged and non-engaged estimates are not distinguishable; "matchup-specific" must not be claimed. **R3** |(b) − (a)| = 0.0054 ≤ 0.03: pick changes nothing. **R4** (e) interaction is +0.006 (not negative): rookie timing is not supported. **R5** (f) −0.023 reported next to (a) +0.037, no reading.

**Execution note (X1).** (i) Row filters follow the entry; "pass_result non-empty" read as non-null and ≠ "". Counts differ by one snap from E0.7 (46,194 vs 46,193) because X1 applies the penalty filter. (ii) `log_pick` in (b) is z-scored over distinct blockers; `undrafted` is 0/1. (iii) Subsets (c) reuse the full-sample context columns (spline, measure z, c_B), dropping columns that become constant. (iv) (f) uses `build_k5_composites()` with z over distinct blockers in the (f) sample; all 77 blockers have a k5 value, so (f) and (a) have identical rows. (v) Added a supplementary fit (g), c_B × pos_T on all snaps, which is **not** in the X1 specification; X4(e)'s rule refers to "X1's all-snap c_B × pos_T", which X1 does not otherwise produce. (vi) The O/E correlation CI is a nominal Fisher interval that treats blocker-seasons as independent (58 blockers contribute 1-3 seasons each); the p-value is therefore approximate. (vii) Spline knots are the 5/35/65/95th percentiles of these 46,193 snaps, orthonormalised as in `Version`.

### X2 — 2026-11-07 — Calibrated test of the side decomposition (blind)

**Specification.**
- Freedman-Lane permutation exactly as V5 (§8), but for M1-S1 (GLM, `C_COLS + Q_COLS + [c_R, c_B]` on P).
- For side s, regress the player composite on the seven z_{m,s} plus that side's flags over the distinct players of s in P. Permute residuals within side × draft class (2,000 draws, `default_rng(2027)`). Rebuild composite* = fitted + permuted residual and re-standardise c_s* with P's c_s constants.
- Permute **only the tested side**, the other side held at observed.
- Record studentized t* for c_B (blocker side permuted) and separately for c_R (rusher side permuted). Two-sided p = (1 + #{|t*| ≥ |t_obs|}) / 2,001. Use `fast_logit_cluster` for speed.

**Reason.** S1's c_B interval sits at the boundary (Bayes [0.020, 0.301], GLM κ [−0.005, 0.290]). The registered permutation tests the gap, not the side term. This gives the one calibrated, generator-free p-value for the surprise itself.

**Reading rule.** p ≥ 0.05: "the blocker-side term is not distinguishable from permutation noise". p < 0.05: "the blocker-side association passes a calibrated permutation test, but it remains a secondary/exploratory result". With about 10 secondary intervals, it is never upgraded to a finding.

**Result (run 2026-11-07, `scripts/exploratory/x2_side_permutation.py`, runtime 323 s; tables `reports/exploratory/tables/x2_*.csv`).**
Reproduction check passed (M1 gap −0.154, κ-CI [−0.308, 0.000]; S1 c_B +0.143, c_R −0.064).

| Term (side permuted) | β_obs | nominal SE | t_obs | p two-sided, studentized | p one-sided (same direction) | p two-sided, coefficient | null t* SD |
|---|---|---|---|---|---|---|---|
| c_B (blocker side, 69 players) | +0.1428 | 0.0615 | 2.319 | **0.0645** | 0.0375 | 0.1000 | 1.236 |
| c_R (rusher side, 97 players) | −0.0639 | 0.0819 | −0.780 | 0.4693 | 0.2959 | 0.4278 | 1.116 |

Mechanical reading: c_B p = 0.0645 ≥ 0.05, so "the blocker-side term is not distinguishable from permutation noise". (c_R p = 0.469, same reading.) The permutation null of t* for c_B is wider than N(0, 1) (SD 1.24; 95% range [−2.36, 2.58]), so the nominal t reference is anti-conservative for this term.

**Execution note (X2).** (i) The log says "exactly as V5" with "one stream"; I used a fresh `default_rng(2027)` for each tested side (c_B run, then c_R run), so each side's permutation sequence is the one V5 would use for a single run. (ii) Beyond the V5 recipe, c_s* is re-standardised with P's c_s mean and SD (`Version.std`), as the entry states, rather than divided by the fixed 1.253. (iii) The engine check (numpy `fast_logit_cluster` vs statsmodels) agrees to 5e-5 / 3e-4 on the SEs of c_B / c_R; the one large coefficient difference (3.7) is on `pre0` (114 reps with zero pressures; quasi-separation) and does not touch c_B or c_R.

### X3 — 2026-11-07 — What the mirror-drill trait measures (partly not blind: E0.4, E0.5, E0.11)

**Specification.** All on P, M1-S1 GLM base.
- (a) Quantised O3: replace c_B with indicators `fast` = O3_value ≤ 0.45 s and `slow` = O3_value ≥ 0.55 s (reference 0.50 s).
- (b) c_B plus a z-scored `O3_n_slots` (the number of reversals in the rep).
- (c) k3 and k5 blocker composites jointly (as E0.4), reported with the variance-inflation factor.
- (d) Player level, among the 105 OL with an O3 value: Spearman r of O3_value with three-cone, short shuttle, NGS athleticism, weight, arm, `ngs_college_production_score`, draft year. Kruskal-Wallis of O3_value across draft years.
- (e) Gaussian M1-S1 GLMs for in-game `blocker_back_disp_05s` and `_10s` (E0.11, re-run in the formal script).

**Reason.** Explanation (3): the trait may measure something other than athletic quickness. O3 is a median of about 4 reversals from one rep, quantised in 0.05 s steps, and its effect sits in the part that changes with smoothing.

**Reading rules.**
- If the (a) contrast fast-vs-0.50 has the same sign as c_B, and the effect is not monotone across the three levels, call the c_B effect "carried by a one-frame difference in a single 10 Hz rep".
- If (c) puts the effect on the k3-specific part with the k5 part ≤ 0, call it "smoothing-specific, consistent with measurement noise".
- If (e) shows |effect| < 0.05 outcome SD with a CI inside ±0.10 SD, report "the trait shows no transfer to in-game set depth".
- None of these licenses a mechanism claim.

**Result (run 2026-11-07, `scripts/exploratory/x3_trait_meaning.py`, runtime 3.1 s; tables `reports/exploratory/tables/x3_*.csv`).** Reproduction check passed. All fits on P (7,214 reps, 69 blockers, 97 rushers), M1-S1 base, β per unit of the stated column; CI nominal t(68) two-way cluster, κ-CI alongside where useful.

| Fit | Term | β [95% CI] | κ-CI |
|---|---|---|---|
| ref: M1-S1 | c_B | +0.143 [0.020, 0.266] | [−0.005, 0.290] |
| (a) quantised O3 (reference 0.50 s: 35 blockers; fast ≤ 0.45: 25 blockers, 2,634 reps; slow ≥ 0.55: 9 blockers, 897 reps) | fast | +0.214 [−0.014, 0.442] | [−0.059, 0.488] |
| | slow | −0.215 [−0.596, 0.166] | [−0.672, 0.242] |
| (b) c_B + z(O3_n_slots) (rep-level r(c_B, n_slots) = −0.30; n_slots 4-7, median 4) | c_B | +0.130 [0.011, 0.250] | [−0.013, 0.273] |
| | z(n_slots) | −0.028 [−0.120, 0.065] | [−0.139, 0.083] |
| (c) k3 and k5 jointly | c_B (k3) | +0.219 [0.051, 0.386] | [0.018, 0.419] |
| | c_B (k5) | −0.108 [−0.300, 0.085] | [−0.339, 0.124] |
| ref: k5 alone | c_B (k5) | +0.061 [−0.078, 0.200] | [−0.105, 0.228] |
| (e) Gaussian, `blocker_back_disp_05s` (outcome SD 0.259 yd) | c_B | −0.0222 SD [−0.0792, 0.0347] = −0.0058 yd [−0.0205, 0.0090] | [−0.0905, 0.0461] SD |
| (e) Gaussian, `blocker_back_disp_10s` (outcome SD 0.666 yd) | c_B | −0.0199 SD [−0.0640, 0.0243] = −0.0132 yd [−0.0426, 0.0162] | [−0.0729, 0.0331] SD |

(c) VIF: k3 3.51, k5 3.68 in the full joint design; 2.96 for the pair alone (rep-level r(k3, k5) = 0.814).

(d) Player level, 105 OL with an O3 value (O3_value is the raw reversal time, lower = faster). Spearman r (n): three-cone +0.302 (52, p 0.030); short shuttle +0.243 (56, p 0.071); NGS athleticism −0.275 (105, p 0.0045); weight +0.132 (105, p 0.18); arm −0.062 (105, p 0.53); `ngs_college_production_score` −0.089 (105, p 0.37); draft year +0.095 (105, p 0.34). Kruskal-Wallis of O3_value across draft years 2023/2024/2025 (n 37/39/29): H = 0.992, p = 0.609 (all medians 0.500 s).

Mechanical readings:
- (a): the fast-vs-0.50 contrast (+0.214) has the same sign as c_B, but the effect **is** monotone across the three levels (fast +0.214 > 0.50 s = 0 > slow −0.215), so the rule's second condition fails: "carried by a one-frame difference in a single 10 Hz rep" is **not triggered**.
- (c): k3 part +0.219 > 0 and k5 part −0.108 ≤ 0, so "smoothing-specific, consistent with measurement noise" **is triggered**.
- (e): 0.5 s: |−0.022| < 0.05 SD with CI [−0.079, 0.035] inside ±0.10 SD (κ-CI [−0.091, 0.046] also inside); 1.0 s likewise (−0.020 [−0.064, 0.024]): "the trait shows no transfer to in-game set depth".
- (b) and (d) have no reading rule. None of these licenses a mechanism claim.

**Execution note (X3).** (i) "z-scored `O3_n_slots`" taken as z over the 69 distinct in-P blockers (mean 4.48, SD 0.66). (ii) (a) levels: 0.40 and 0.45 s are pooled as `fast` (25 blockers), 0.55-0.65 as `slow` (9 blockers), compared with 0.50 s (35); c_B is removed from the model and c_R retained. (iii) "monotone" is applied as fast > 0 > slow or the reverse, relative to the 0.50 s reference; this is my operationalisation, since the rule does not define it. (iv) (c) k5 column is `Version("k5").X["c_B"]` (standardised over the k5 primary set, which equals P: all 69 blockers have a k5 value); c_R is the registered one (D1 is identical under k5, r = 1.000). VIF is computed from the fitted design (all columns). (v) (d) p-values are Spearman asymptotic; the CI is an approximate Fisher interval (SE 1.06/√(n−3)). Three-cone and shuttle are available for 52 and 56 of the 105 OL. (vi) (e) reports nominal CIs for the rule; the κ-CI is shown for completeness.

### X4 — 2026-11-07 — Selection (collider) and assignment discriminators (not blind: E0.9, E0.10)

**Specification.**
- (a) M1-S1 GLM + z(blocker log pick) + c_B × z(blocker log pick).
- (b) M1-S1 + z(log blocker reps in P) + c_B × that.
- (c) Player-level selection model on the 105 OL with a registered composite: logistic in-P ~ composite × late-pick half + draft-class dummies, plus OLS log1p(reps in P) on the same. Report the composite slope within each half.
- (d) M1-S1 + defense-team FE; + blocker-team FE; + rusher rating from `player_ratings.csv` (posterior mean, side == rusher); + clip(score_diff_offense, ±21)/10, offense_win_prob, Q4 indicator. Each added separately, then all together.
- (e) M1-S1 + c_B × pos_T and c_B × edge (both in one model).
- (f) Rep-level and blocker-level correlations of c_B with rusher log pick, rusher rating, c_R, edge, double team, dropback.

**Reason.** These test explanations (1) collider and (2) assignment.

**Reading rules.**
- Collider (1) is called plausible only if both hold: the c_B effect is concentrated in later picks ((a) interaction > 0 with CI excluding 0), **and** composite predicts selection in that half ((c) composite slope CI excluding 0, or |r| ≥ 0.3). Otherwise: "the selection needed to produce Berkson bias is not present".
- Assignment (2) is called excluded through observables if every (d) estimate is within ±0.05 of +0.143 and every |r| in (f) is < 0.25.
- (e) is a subgroup split: report it, but never headline "guards only" unless X1's all-snap c_B × pos_T also excludes 0 in the same direction (E0.9 says it does not).

**Result (run 2026-11-07, `scripts/exploratory/x4_selection_assignment.py`, runtime 4.6 s; tables `reports/exploratory/tables/x4_*.csv`).** Reproduction check passed. GLMs on P (7,214 reps, 69 blockers, 97 rushers), M1-S1 base; nominal t(68) two-way cluster CI with κ-CI alongside.

| Fit | Term | β [95% CI] | κ-CI |
|---|---|---|---|
| (a) + z(blocker log pick) + c_B × it | c_B (at mean pick) | +0.283 [0.141, 0.426] | [0.112, 0.454] |
| | z(log pick) | +0.077 [−0.060, 0.215] | [−0.087, 0.242] |
| | **c_B × z(log pick)** | **+0.136 [0.041, 0.231]** | [0.022, 0.250] |
| (b) + z(log blocker reps) + c_B × it | c_B | +0.171 [−0.024, 0.366] | [−0.063, 0.405] |
| | c_B × z(log reps) | −0.046 [−0.265, 0.173] | [−0.309, 0.217] |
| (d1) + defense-team FE | c_B | +0.151 [0.014, 0.289] | [−0.014, 0.316] |
| (d2) + blocker-team FE | c_B | +0.115 [−0.009, 0.240] | [−0.034, 0.265] |
| (d3) + rusher rating | c_B | +0.129 [0.007, 0.251] | [−0.017, 0.275] |
| (d4) + score diff, win prob, Q4 | c_B | +0.152 [0.030, 0.274] | [0.006, 0.298] |
| (d5) all together | c_B | +0.096 [−0.042, 0.235] | [−0.070, 0.263] |
| (e) + c_B × pos_T + c_B × edge | c_B (guard/center, interior) | +0.252 [0.085, 0.419] | [0.051, 0.452] |
| | c_B × pos_T | −0.257 [−0.461, −0.052] | [−0.502, −0.011] |
| | c_B × edge | +0.057 [−0.177, 0.291] | [−0.224, 0.337] |
| (e) derived slopes | tackle interior / G-C edge / tackle edge | −0.005 / +0.309 / +0.052 | all κ-CIs include 0 except G-C edge [0.046, 0.571] |

(c) Player-level selection among the 105 OL with a registered composite (median log pick 5.04; early half 53 players, 51 in P; late half 52, 18 in P; class dummies 2024/2025):

| Half | Logit in-P ~ composite: slope [95% CI] | OLS log1p(reps) ~ composite: slope [HC3 95% CI] | r(composite, in-P) | r(composite, log1p reps) |
|---|---|---|---|---|
| early | −1.24 [−3.36, 0.88] | −0.130 [−0.581, 0.321] | −0.166 | −0.086 |
| late | +0.339 [−0.311, 0.989] | +0.218 [−0.154, 0.588] | +0.144 | +0.127 |

Pooled composite × late interaction: logit +1.55 (p 0.17); OLS +0.35 (p 0.23).

(f) Correlations of c_B (rep-level over 7,214 reps / blocker-level over 69 blockers, mean feature per blocker): rusher log pick +0.040 / +0.059; rusher rating +0.028 / −0.026; c_R +0.062 / +0.221; edge +0.090 / +0.086; double team +0.070 / +0.228; dropback duration −0.004 / −0.117. Max |r| = 0.228.

Mechanical readings:
- **Collider (1):** the (a) interaction is > 0 with CI excluding 0 (+0.136 [0.041, 0.231]), **but** in the late half the composite slope CIs include 0 (logit [−0.311, 0.989]; OLS [−0.154, 0.588]) and |r| = 0.14 / 0.13 < 0.3, so the second condition fails: "the selection needed to produce Berkson bias is not present". Collider is not called plausible.
- **Assignment (2):** every (d) estimate lies in [0.093, 0.193] (range 0.096-0.152; (d5) is 0.096, 0.003 inside the band) and max |r| in (f) = 0.228 < 0.25, so assignment is "excluded through observables".
- **(e):** c_B × pos_T = −0.257 [−0.461, −0.052]; X1's all-snap c_B × pos_T = −0.032 [−0.135, 0.071] includes 0, so "guards only" is **not** to be headlined.

**Execution note (X4).** (i) "z(blocker log pick)" and "z(log blocker reps)" are z-scored over the 69 distinct in-P blockers (not over reps), so the interaction coefficients (+0.136, −0.046) differ slightly from E0.10 (+0.143, −0.023). (ii) The rule for the selection model says "composite slope CI excluding 0, or |r| ≥ 0.3" without naming the model; I applied it to the late-half slope in either the logistic or the OLS model and to |r| for either outcome (the conclusion is the same under any single choice, none is satisfied). Slopes are from within-half fits with class dummies; logit CIs are Wald (nominal, no clustering since the unit is the player); the early-half logit gave a `ConvergenceWarning` (51 of 53 players in P, near-separation), so its wide CI is approximate. The half split is log pick > median (late) vs ≤ median (early). (iii) Rusher rating = `rating_mean` of side == rusher in `data/processed/confirmatory/player_ratings.csv` (the frozen model R output), standardised over P reps. (iv) Team FE are indicators for the team of the rusher (defense) or blocker (offense), reference the alphabetically first team in P. (v) Game state: `clip(score_diff_offense, ±21)/10`, `offense_win_prob` (raw), `quarter == 4`; no rows were dropped for nulls (n = 7,214 in every fit). (vi) (d5) combines both team FE, rusher rating and the three game-state columns. (vii) The "X1 all-snap c_B × pos_T" used by the (e) rule is X1's supplementary fit (g), which is not in the X1 spec (see X1 execution note). (viii) Blocker-level correlations use the unweighted blocker means of each rep-level feature.

### X5 — 2026-11-07 — Rusher trait at player level, on all pass-rush snaps (blind)

**Specification.**
- Rows: `player_play` with `blitzing` true, `lined_up_position` ∈ {EDGE, INTERIOR_LINE}, dropback plays (`pass_result` non-empty), not nullified, REG/POST; `nfl_id` with `combine_position` == "DL".
- Outcome: rusher pressure = `time_to_pressure` non-null. Secondary: `quick_pressure` true.
- Context as X1, with `edge` in place of pos_T/pos_C.
- Rusher measures: z over distinct rushers, as X1.
- Fits:
  - (a) + c_R (registered D1);
  - (b) (a) + log pick + undrafted;
  - (c) c_R from `composite_sensA` (D1 + D5);
  - (d) D5_z alone (rushers with D5).
- Logistic GLM, SE clustered by rusher, t(G−1).

**Reason.** This is the original hypothesis, made bigger and simpler: do rushers who are athletic by tracking generate more pressure across all their rush snaps, beyond stopwatch? E0.12 shows composite A's "Opposite" verdict sits on the rusher side, so S0 is not a replication of H1's blocker-side signal. This decides whether the rusher-side tracking traits carry anything.

**Reading rules.**
- If (a) and (b) both have CIs including 0 with upper bound < 0.10, report "rush-drill peak speed does not predict a rusher's pressure rate beyond stopwatch, size and NGS score (and pick)".
- If (c) or (d) excludes 0 negative, report it as the rusher-side counterpart of the S0 signal, exploratory.
- A positive (a) excluding 0 would be the one result in the hypothesised direction. It must be reported with the note that it was not the registered unit of analysis.

**Result (run 2026-11-07, `scripts/exploratory/x5_rusher_player_level.py`, runtime 1.6 s; tables `reports/exploratory/tables/x5_*.csv`).**
Frame: 19,672 rusher snaps, 98 DL rushers, 1,939 pressures (9.9%), 556 quick pressures (2.8%). Logit coefficient on the rusher trait (per SD), nominal 95% CI, t(G−1), SE clustered by rusher:

| Fit | Pressure: β [95% CI], p | Quick pressure: β [95% CI], p | Rushers / snaps |
|---|---|---|---|
| (a) c_R (D1) | +0.021 [−0.112, 0.155], 0.75 | −0.050 [−0.293, 0.193], 0.68 | 98 / 19,672 |
| (b) (a) + log pick + undrafted | +0.006 [−0.107, 0.120], 0.91 | −0.064 [−0.260, 0.133], 0.52 | 98 / 19,672 |
| (c) composite_sensA (D1 + D5) | −0.003 [−0.135, 0.129], 0.96 | −0.078 [−0.325, 0.169], 0.53 | 98 / 19,672 |
| (d) D5_z alone | +0.023 [−0.089, 0.134], 0.69 | −0.005 [−0.200, 0.190], 0.96 | 77 / 15,366 |

Mechanical reading: (a) and (b) both include 0 but their upper bounds (0.155, 0.120) are not < 0.10, so the first rule ("upper bound < 0.10 → no prediction beyond stopwatch") is **not triggered**; (c) and (d) do not exclude 0 negative, so the second rule is not triggered; (a) is not positive excluding 0, so the third is not triggered. No reading rule fires: the rusher trait estimates are centred near 0 (|β| ≤ 0.023) with intervals about ±0.13.

**Execution note (X5).** (i) `dropback_duration` is null on every rusher row of `player_play` (it is populated only on OL rows). "Context as X1" requires it, so I took the play-level value (constant within a play; verified range 0 among non-null rows, equal to `engaged_pairs.dropback_duration` where both exist) from any row of the same (game, play), and dropped rusher snaps on plays where no row carries it (9,080 of 28,752 DL blitz snaps). This is the smallest choice that keeps the X1 context; the dropped plays are those without OL pass-pro rows. (ii) "dropback plays (`pass_result` non-empty)" read as non-null and ≠ "". (iii) Log pick in (b) is z-scored over distinct rushers in the fit. (iv) `lined_up_position` is taken from `player_play`; `edge` = EDGE. (v) Every rusher in the frame has a registered composite and composite_sensA; D5_z exists for 77 of 98.
