# Exploratory results X1-X5

All analyses below are **exploratory** (preregistration section 13.4). Specifications and reading rules are in `reports/specification_log.md` (entries X1-X5, each with a "Result" block and an "Execution note"). Scripts: `scripts/exploratory/x1_*.py` ... `x5_*.py` (shared helper `_common.py`). Tables: `reports/exploratory/tables/`. Figure: `figures/exploratory/x1_blocker_season_OE.png`. Run order: X2, X5, X1, X3, X4. Every engaged-rep script first reproduces the E0.1 check (M1 gap −0.154, κ-CI [−0.308, 0.000]; S1 c_B +0.143, c_R −0.064): passed in X2, X3, X4. Coefficients are logit units per SD unless stated; CIs are nominal 95% (t(G−1), clustered) unless stated.

---

## X2. Calibrated permutation test of the side terms (blind; 323 s)

Freedman-Lane, 2,000 draws, `default_rng(2027)`, studentized, M1-S1 on P; only the tested side permuted.

| Term (side permuted) | β_obs | t_obs | p two-sided (studentized) | p one-sided | p two-sided (coefficient) | null t* SD |
|---|---|---|---|---|---|---|
| c_B (blocker) | +0.143 | 2.319 | **0.0645** | 0.0375 | 0.1000 | 1.236 |
| c_R (rusher) | −0.064 | −0.780 | 0.4693 | 0.2959 | 0.4278 | 1.116 |

**Mechanical reading:** p = 0.0645 ≥ 0.05, so "the blocker-side term is not distinguishable from permutation noise".

## X5. Rusher trait on all pass-rush snaps (blind; 1.6 s)

19,672 blitz rusher snaps, 98 DL, 1,939 pressures (9.9%), 556 quick pressures. Rusher-clustered logit.

| Fit | Pressure β [95% CI] | Quick pressure β [95% CI] | Rushers / snaps |
|---|---|---|---|
| (a) c_R (D1) | +0.021 [−0.112, 0.155] | −0.050 [−0.293, 0.193] | 98 / 19,672 |
| (b) (a) + log pick + undrafted | +0.006 [−0.107, 0.120] | −0.064 [−0.260, 0.133] | 98 / 19,672 |
| (c) composite_sensA (D1 + D5) | −0.003 [−0.135, 0.129] | −0.078 [−0.325, 0.169] | 98 / 19,672 |
| (d) D5_z alone | +0.023 [−0.089, 0.134] | −0.005 [−0.200, 0.190] | 77 / 15,366 |

**Mechanical reading:** (a) and (b) include 0 but their upper bounds (0.155, 0.120) are not < 0.10, so the "no prediction" rule is not triggered; (c) and (d) do not exclude 0 negative; (a) is not positive excluding 0. **No reading rule fires.** (Rusher snaps lacking a play-level dropback duration, 9,080 of 28,752, were dropped; see the log note.)

## X1. Blocker trait on all pass-pro snaps (4.1 s)

46,193 snaps, 77 OL, pressure rate 8.34%, 7,094 snaps with an engaged cohort pair. Blocker-clustered logit, t(76).

| Fit | Term | β [95% CI] | p |
|---|---|---|---|
| (a) ctx + measures + c_B | c_B | +0.037 [−0.027, 0.100] | 0.25 |
| (b) (a) + log pick + undrafted | c_B | +0.031 [−0.034, 0.096] | 0.34 |
| (c) (a), eng_play = 0 (39,099 snaps) | c_B | +0.019 [−0.045, 0.082] | 0.56 |
| (d) (a) + eng_play + c_B × eng_play | c_B × eng_play | +0.051 [−0.031, 0.134] | 0.22 |
| | c_B on engaged plays | +0.078 [−0.020, 0.176] | 0.12 |
| (e) (a) + exp1 + c_B × exp1 | c_B × exp1 | +0.006 [−0.103, 0.115] | 0.91 |
| | c_B, rookie | +0.030 [−0.056, 0.116] | 0.49 |
| (f) 5-frame composite | c_B(k5) | −0.023 [−0.086, 0.040] | 0.47 |
| (g) not in spec: (a) + c_B × pos_T | c_B × pos_T | −0.032 [−0.135, 0.071] | 0.54 |

Blocker-season O/E (100 blocker-seasons, ≥ 100 snaps, 58 blockers): Pearson r(c_B, (O−E)/√E) = +0.128 (nominal [−0.070, 0.316]); Spearman +0.131. Figure: `figures/exploratory/x1_blocker_season_OE.png`.

**Mechanical readings:** R1: (a) CI includes 0 and upper 0.100 < 0.15, so "on all pass-pro snaps the blocker trait is bounded at ≤ 0.10 per SD; the engaged-rep blocker effect does not carry over to a blocker's season". R2: the (d) interaction CI includes 0, so engaged and non-engaged estimates are not distinguishable and "matchup-specific" must not be claimed. R3: |(b) − (a)| = 0.005 ≤ 0.03, so pick changes nothing. R4: (e) interaction is +0.006, not negative, so rookie timing is not supported. R5: (f) reported next to (a), no reading.

## X3. What the mirror-drill trait measures (3.1 s)

All on P, M1-S1 base. Reference c_B: +0.143 [0.020, 0.266].

| Fit | Term | β [95% CI] |
|---|---|---|
| (a) quantised O3 (reference 0.50 s: 35 blockers) | fast (≤ 0.45 s; 25 blockers, 2,634 reps) | +0.214 [−0.014, 0.442] |
| | slow (≥ 0.55 s; 9 blockers, 897 reps) | −0.215 [−0.596, 0.166] |
| (b) c_B + z(O3_n_slots) | c_B | +0.130 [0.011, 0.250] |
| | z(n_slots) | −0.028 [−0.120, 0.065] |
| (c) k3 and k5 jointly (VIF 3.51 / 3.68) | c_B (k3) | +0.219 [0.051, 0.386] |
| | c_B (k5) | −0.108 [−0.300, 0.085] |
| (e) Gaussian, `blocker_back_disp_05s` | c_B | −0.022 outcome SD [−0.079, 0.035] (−0.0058 yd) |
| (e) Gaussian, `blocker_back_disp_10s` | c_B | −0.020 outcome SD [−0.064, 0.024] (−0.0132 yd) |

(d) Spearman r of O3_value (raw time, lower = faster) among 105 OL: three-cone +0.302 (n 52, p 0.030); short shuttle +0.243 (56, p 0.071); NGS athleticism −0.275 (105, p 0.0045); weight +0.132; arm −0.062; NGS college production −0.089; draft year +0.095 (all n 105, p ≥ 0.18). Kruskal-Wallis across draft years: H 0.992, p 0.609.

**Mechanical readings:** (a) the fast contrast has the same sign as c_B but the effect is monotone across the three levels, so "carried by a one-frame difference in a single 10 Hz rep" is **not triggered**. (c) k3 part +0.219 > 0 and k5 part −0.108 ≤ 0: "smoothing-specific, consistent with measurement noise" **is triggered**. (e) |−0.022| < 0.05 SD with CI inside ±0.10 SD (1.0 s: −0.020, also inside): "the trait shows no transfer to in-game set depth". (b), (d): no rule. None licenses a mechanism claim.

## X4. Selection (collider) and assignment discriminators (4.6 s)

| Fit | Term | β [95% CI] |
|---|---|---|
| (a) + z(blocker log pick) + c_B × it | c_B × z(log pick) | **+0.136 [0.041, 0.231]** |
| (b) + z(log blocker reps) + c_B × it | c_B × z(log reps) | −0.046 [−0.265, 0.173] |
| (d1) + defense-team FE | c_B | +0.151 [0.014, 0.289] |
| (d2) + blocker-team FE | c_B | +0.115 [−0.009, 0.240] |
| (d3) + rusher rating | c_B | +0.129 [0.007, 0.251] |
| (d4) + score diff, win prob, Q4 | c_B | +0.152 [0.030, 0.274] |
| (d5) all together | c_B | +0.096 [−0.042, 0.235] |
| (e) + c_B × pos_T + c_B × edge | c_B × pos_T | −0.257 [−0.461, −0.052] |
| | c_B × edge | +0.057 [−0.177, 0.291] |

(c) Selection among 105 OL (late half = log pick > median 5.04; 18 of 52 late players in P, 51 of 53 early):

| Half | Logit in-P slope [95% CI] | OLS log1p(reps) slope [HC3 CI] | r(inP) | r(log1p reps) |
|---|---|---|---|---|
| early | −1.24 [−3.36, 0.88] | −0.130 [−0.581, 0.321] | −0.166 | −0.086 |
| late | +0.339 [−0.311, 0.989] | +0.218 [−0.154, 0.588] | +0.144 | +0.127 |

(f) Correlations of c_B, rep-level / blocker-level: rusher log pick 0.040 / 0.059; rusher rating 0.028 / −0.026; c_R 0.062 / 0.221; edge 0.090 / 0.086; double team 0.070 / 0.228; dropback −0.004 / −0.117. Max |r| 0.228.

**Mechanical readings:** Collider: (a) interaction > 0 with CI excluding 0, but the late-half composite slope CIs include 0 and |r| < 0.3, so "the selection needed to produce Berkson bias is not present". Assignment: all five (d) estimates lie within ±0.05 of +0.143 (range 0.096-0.152) and max |r| = 0.228 < 0.25: "excluded through observables". (e): X1's all-snap c_B × pos_T (−0.032 [−0.135, 0.071]) includes 0, so "guards only" is not to be headlined.

---

## What the programme settles

Each statement is about what the X results do to the explanation as written in `interpretation.md` section B; none is a test of the explanation as a whole.

**B1. Chance on a coarse single-rep trait: supported, not established.**
- X2: the blocker term's calibrated p is 0.0645 two-sided (0.0375 one-sided; coefficient-based 0.100), and the null t* SD is 1.24, so the nominal t reference was anti-conservative for this term. It is not distinguishable from permutation noise.
- X1: over the same blockers' 46,193 snaps the effect is +0.037 [−0.027, 0.100], and +0.019 [−0.045, 0.082] off the engaged plays. The engaged/non-engaged difference (+0.051 [−0.031, 0.134]) is not distinguishable from 0, so the data do not exclude a somewhat larger effect on engaged plays (+0.078 [−0.020, 0.176]), nor distinguish it from none.
- X3(c): the effect sits in the k3-specific part (+0.219) with the k5 part −0.108; X3(a) shows the quantised levels are monotone (fast +0.214, slow −0.215), so the one-frame-contrast reading is **not** supported.
- X5 (rusher side): the rusher traits are near 0 on all blitz snaps (|β| ≤ 0.023 for pressure, intervals about ±0.13), and X2 gives c_R p = 0.47; neither shows a rusher-side signal to carry the S0 "Opposite".

**B2. The trait measures something other than useful quickness: weakened as a football mechanism, left open as to what the k3-specific part is.**
- No transfer to in-game set depth (−0.022 SD [−0.079, 0.035]; 1.0 s −0.020 [−0.064, 0.024]); reversal count adds nothing (−0.028).
- O3_value tracks other athletic measures in the expected direction (three-cone +0.302, NGS athleticism −0.275) and is unrelated to weight, arm, production and draft year, so it is not simply a size or draft-class proxy.
- The k3-specific component carries the engaged-rep effect (X3(c)). The X results do not identify what that component is (sensor jitter, leader tempo, style).

**B3. Assignment confounding: weakened (excluded through observables, per the rule).**
- c_B stays in +0.096 to +0.152 under defense-team FE, blocker-team FE, rusher rating, game state, and all together; max |r| with opponent and rep features is 0.228.
- The tackle/guard pattern (c_B × pos_T −0.257 on engaged reps) is not present on all snaps (−0.032 [−0.135, 0.071]).
- Unobserved help schemes are not addressed by any X entry.

**B4. Collider selection: weakened.**
- One ingredient is present: the effect is larger for later picks (c_B × pick +0.136 [0.041, 0.231]).
- The other is not: the composite does not significantly predict selection into P or reps in the late-pick half (logit +0.339 [−0.311, 0.989]; r +0.144 / +0.127). Exposure (log reps) does not moderate c_B (−0.046 [−0.265, 0.173]); controlling for pick changes the all-snap estimate by 0.005.
- The late-half selection intervals are wide (18 of 52 late players in P), so the data do not exclude weak selection; the mechanical rule is not met.

**B5. Rookie timing: not supported (leaves it open, weakly).**
- On all snaps, the experience interaction is +0.006 [−0.103, 0.115] and the rookie-season c_B is +0.030 [−0.056, 0.116]; the pattern does not run in the direction the explanation needs (a negative interaction).
- The interval is about ±0.11, so a modest timing effect is not excluded.
