# Pre-registration: confirmatory analysis

**Entry:** "The athletic gap: do Combine-tracked movement traits decide NFL trench reps?"
**Status:** FINAL DRAFT, awaiting freeze. The only fields still open are the freeze-manifest hashes in section 13.1 (the script hash and the sealed-file hash), which the coordinator fills at freeze. Nothing in this document was chosen with knowledge of any outcome in `engaged_outcomes_SEALED.parquet`.
**Design source:** `reports/candidates_v2.md` sections 3-4. Every change from that design is listed with its reason in Appendix A.

This document is binding. After it is frozen (hashed and committed), only `scripts/confirmatory_analysis.py`, run once in `--mode confirmatory`, produces confirmatory results. Anything not specified here is exploratory and must be labelled that way in the writeup.

---

## 0. What was known about outcomes when this was written (disclosure)

The sealed file has never been opened. These are the only outcome-derived facts that anyone on the project had seen:

| Source | Fact | Touches a Combine tracking trait? |
|---|---|---|
| `dataset_build.md` §7 | 787 of 8,271 primary engaged reps have `pressure_allowed` (base rate 0.0952); no null outcomes among engaged reps | No |
| `feasibility_c3.md` G1 | Coherence: P(rusher pressure \| blocker pressure) = 79.7% on engaged pairs vs 19.3% on non-engaged pairs | No |
| `feasibility_c3.md` G2 | GLM on all 8,271 engaged reps: z(rusher pick − blocker pick) −0.204 (SE 0.049), z(weight diff) −0.214, dropback_duration +0.577/s. Pick effect on non-engaged pairs −0.075; rusher-pressure outcome pick −0.220. Weight effect falls to −0.066 with position dummies | No (draft pick, weight, dropback) |
| `feasibility_c1.md` G5 | In-game set depth/quickness vs adjusted pressure probability: r up to +0.34 (wrong sign) | No (in-game kinematics only; the report states that no drill metric was correlated with any pressure outcome) |
| `feasibility_c2.md` G5 | In-game bend vs shrunk pressure rate: partial r 0.41 (EDGE only 0.22) | No (it states that no drill metric was correlated with pressure) |

**No analysis has related any candidate trait (O1-O5, D1-D6), any composite, or the athletic gap to any NFL outcome.** The trait gates, the composites and this design were all fixed without that information.

---

## 1. Question, hypotheses and the three design decisions

### 1.1 Question

On NFL pass-protection reps where a cohort blocker (OL) is engaged with a cohort rusher (DL), does the difference between their Combine-tracked movement traits (the **athletic gap**) predict whether the rep ends in a pressure? The primary question asks this beyond what a club measures at the Combine: both players' size, official stopwatch times and NGS athleticism score (H1). The key secondary asks it beyond draft slot as well (H2).

### 1.2 Hypotheses and expected directions

Sign conventions:
- gap = rusher composite − blocker composite, with composites oriented so that higher = more athletic;
- the outcome is the blocker's `pressure_allowed`;
- pick difference = rusher log pick − blocker log pick, and a lower pick is a better prospect.

| ID | Status | Statement | Model | Expected sign |
|---|---|---|---|---|
| **H1** | **Primary, confirmatory** | The athletic gap (registered composites) predicts blocker pressure allowed, given context, both players' size, official stopwatch measures and NGS athleticism | M1 | β_gap > 0 |
| H2 | Key secondary | Same, additionally given both players' draft slot | M2 | β_gap > 0 |
| S0 | Secondary, co-reported with H1 | H1 and H2 using sensitivity composite A (adds the 40-yard acceleration shape O4/D5) | M1-A, M2-A | > 0 |
| S1 | Secondary | Side decomposition: rusher composite and blocker composite as separate terms | M1-S1 | β_R > 0, β_B < 0 |
| S2 | Secondary | Gap × rusher alignment: is the gap more decisive on the EDGE than inside? | M1-S2 | interaction > 0 |
| S3a | Secondary | Gap → `peak_pressure_probability_allowed` (continuous) | M1-S3a | > 0 |
| S3b | Secondary | Gap → rusher pressure on the same rep | M1-S3b | > 0 |
| S4 | Secondary (validation) | Out-of-sample log loss of information sets (two-way grouped CV) | GLM | none stated (descriptive) |
| S5 | Secondary, about 100 words | "Giving ground": how much of the blocker-depth/pressure association disappears once the rusher is conditioned on | S5a/S5b | β_depth > 0; share > 0 |
| M0 | Secondary (information ladder) | Gap given context and size only | M0 | > 0 |

### 1.3 Decision 1: the fragile trait verdicts

**Rule:**
- The **primary composites are the mechanically gated ones**: OL = {O3 mirror reversal time}, DL = {D1 rush-drill peak speed}.
- **Composite A** (OL {O3, O4}, DL {D1, D5}) is pre-registered as **secondary hypothesis S0**. It is fitted with the identical models (M1 and M2) and reported in the **same table and forest plot, adjacent to H1, regardless of outcome**.
- Composite B (A plus O1) and two O3-fragility checks (DL-only, 5-frame smoothing) are sensitivity analyses (section 9).

**Anti-cherry-picking clauses:**
1. The H1 verdict (section 6) is computed only from the registered composite. No S0, B or sensitivity result can change it, upgrade it or replace it in the headline.
2. If the S0 verdict category differs from H1's, the writeup's summary sentence must state both, e.g. "registered composite: inconclusive; with the acceleration shape (pre-registered secondary): supported". The script emits that sentence (section 14, R11).
3. The writeup may not describe composite A as "the better composite" on the basis of outcome results.

**Reasons:**
- The gates were fixed before any trait was computed. Amending them now, after seeing which traits narrowly miss (O1's CI bound by 0.007; O4/D5's coverage by one blocker and two rushers), would itself be a researcher degree of freedom, even though no outcome has been seen.
- The coverage gate protects representativeness and power. It does not protect validity.
- O4/D5 are the most stopwatch-orthogonal traits in the pool (max |r| 0.28-0.29), and they come from true repeats (r 0.71 / 0.53). Silently excluding the one sensor-only trait would look arbitrary to a judge, and so would silently including it.
- Composite A is not a near-duplicate of the registered composite: r = 0.81 (OL) and 0.74 (DL). It also covers more players (75 vs 69 engaged blockers) because of the ≥ 1-component rule.
- A co-equal, pre-declared secondary is therefore the honest status.

O1 stays out of A. It fails the reliability gate (the CI lower bound), not the coverage gate, and reliability is the validity gate. It appears only in composite B.

### 1.4 Decision 2: the draft-pick control

**Rule:**
- **The primary model M1 does not control for draft pick.** It controls for context, size (weight, arm length), the official stopwatch measures (forty, ten-yard split, short shuttle, three-cone) and the NGS athleticism score, for both players.
- **M2 adds draft pick and is the key secondary H2.** It is reported in the same forest plot, directly beneath M1.
- The M2 pick-difference coefficient is the model-level positive control (PC2). It also supplies the unit for draft-pick equivalents for both M1 and M2.
- M0 (context + size only) completes an "information ladder" M0 → M1 → M2.

**Reasons (all available before outcomes):**
1. **Decision time.** A club uses Combine data before the draft. A prospect's draft slot does not exist when the decision is made; it is the result of that decision. The question "what does tracking add to what we measure now" therefore conditions on what is measured at the Combine (size, stopwatch, NGS score), not on the league's eventual verdict.
2. **Over-control.** Draft slot is partly caused by Combine athleticism, so it is a descendant of the exposure. Conditioning on it removes the part of the trait's value that the market had already priced in. It also opens a collider path (athleticism → pick ← film/production → NFL performance) that biases the gap coefficient toward zero or below. H2 answers a different, still useful question: did the draft already price this in?
3. **Precision is not the motive.** In the registered analysis set, pick explains little of the gap's variation once the measures are known. Approximate rep-level R² of the gap (outcome-free): size only 0.197; + stopwatch and NGS 0.375; + pick 0.417. Rep-level correlation of composite with own pick: rusher −0.13, blocker +0.08. M1 and M2 differ in what they adjust for, not in power.
4. **The pick yardstick is still needed and is kept.** It comes from M2, where gap and pick are estimated jointly.

A skeptic may object that dropping pick makes a positive result easier to obtain. H2 is reported with equal prominence, and the verdict for H2 is computed by the same rule as for H1. If H1 is supported and H2 is not, the writeup must say that the signal is largely what the draft already priced in.

### 1.5 Decision 3: the primary estimand and decision criterion

- **Estimand:** β_gap in M1, the log-odds of blocker pressure per 1 SD of the athletic gap. It comes from a Bayesian logistic model with crossed random intercepts for blocker and rusher (PyMC), with the priors in section 5.4.
- **Decision criterion:** H1 is **supported** if and only if the 2.5% quantile of the posterior of β_gap is > 0. That is, the 95% equal-tailed posterior interval excludes 0 in the expected direction.
- **Verdict categories and reported units:** section 6.
- **The frequentist mirror** (GLM, two-way cluster-robust SEs) and the Freedman-Lane permutation test are qualifiers. They change the wording, never the verdict.
- **Why the Bayesian interval and not the cluster Wald test decides.** The power simulation (section 12) shows that the two-way cluster Wald test is anti-conservative with 69 blockers and 97 rushers: type-I error 0.118 at nominal 0.05, and a t reference barely helps (0.114). The crossed-random-intercept model represents the clustering directly. Its calibration is checked before freeze on 100 null simulations, under a pre-specified fallback rule (section 6.3, test T1).

---

## 2. Data and analysis sets

### 2.1 Input files (all under `data/processed/`, via `bdb2027.paths.parquet`)

| File | Content | Opened before freeze? |
|---|---|---|
| `engaged_pairs.parquet` | One row per (game_id, play_id, blocker_nfl_id, rusher_nfl_id) co-occurrence; engagement flags, context; 29,269 rows | Yes (outcome-free) |
| `player_baselines.parquet` | 510 players: pick, log pick, undrafted, size, stopwatch, NGS athleticism, missing flags | Yes |
| `combine_traits.parquet` | 239 OL/DL players: per-trait z, registered `composite`, `composite_sensA`, `composite_sensB` | Yes |
| `engaged_outcomes_SEALED.parquet` | Same four keys; outcome columns `pressure_allowed`, `peak_pressure_probability_allowed`, `sack_allowed`, `time_to_pressure_allowed`, `rusher_time_to_pressure`, `rusher_quick_pressure`, `rusher_sack` | **No.** Opened only by the frozen script in confirmatory mode |

The join to outcomes is a 1:1 inner join on the four keys. The script asserts that no rows are lost or duplicated.

### 2.2 Eligible pairs (E0)

Rows of `engaged_pairs` with all of:
- `blocker_lined_up_position` ∈ {T, G, C};
- `blocker_combine_position` == "OL";
- `rusher_combine_position` == "DL";
- `rusher_lined_up_position` ∈ {EDGE, INTERIOR_LINE}.

Season types are REG and POST (PRE is already excluded by the build). E0 has 27,711 pairs, 8,087 of them engaged under the primary definition. This is the analysis set of `candidates_v2` §3.3 before composites are applied.

### 2.3 Named analysis sets (counts computed outcome-free on 2026-11-06)

| Set | Definition | Reps / pairs | Blockers | Rushers | Dyads | 2023 / 2024 / 2025 | REG |
|---|---|---|---|---|---|---|---|
| **P (primary)** | E0 ∩ `engaged_primary` ∩ both registered composites non-null | **7,214** | **69** | **97** | 1,201 | 431 / 1,821 / 4,962 | 6,867 |
| PL (placebo) | E0 ∩ not `engaged_primary` ∩ both registered composites | 17,795 | | | | | |
| ALL | P ∪ PL | 25,009 | | | | | |
| P-A (S0) | As P with `composite_sensA` | 7,720 | 75 | 97 | 1,281 | 431 / 1,882 / 5,407 | 7,297 |
| PL-A | As PL with `composite_sensA` | 18,849 | | | | | |
| P-B | As P with `composite_sensB` | 8,087 | 79 | 97 | 1,342 | | 7,664 |
| P-DL | E0 ∩ `engaged_primary` ∩ rusher registered composite non-null | 8,087 | 79 | 97 | 1,342 | | |
| P-thr | As P with `engaged_d125` / `engaged_d200` / `engaged_k3` / `engaged_k6` | 6,394 / 8,924 / 7,448 / 6,643 | | | | | |

Further facts about P:
- Blocker position: G 3,365, T 3,026, C 823.
- Rusher alignment: EDGE 3,156, INTERIOR_LINE 4,058.
- Rusher `nfl_position`: DT 2,550, DE 2,513, OLB 1,888, NT 263.
- Double-team flag: 953 reps.
- `pass_rushers_encountered`: 0 for 114 reps, 1 for 6,831, 2 for 269.
- Down: 1st 2,662, 2nd 2,410, 3rd 1,932, 4th 210.
- `dropback_duration`: mean 3.10 s, SD 1.20, range 0.58-14.25.
- `play_nullified_by_penalty`: "N" for all rows.
- SD of the gap (registered composite z units): 1.253. Rep-level correlation of the two composites: 0.06.

The script recomputes every count and writes it to R1. A mismatch with the counts above is a data-integrity failure and stops the run (check V0, section 8).

---

## 3. Traits and composites

The traits are taken unchanged from `reports/trait_qualification.md` and `combine_traits.parquet`. Pool, gates and the composite rule are those of `candidates_v2` §3.2 rules 1-6.

| Version | OL components | DL components | Status | Mosier reliability (OL / DL) |
|---|---|---|---|---|
| **Registered** (`composite`) | O3 mirror reversal time (odd/even r 0.70, max \|r\| vs stopwatch/size 0.32, coverage 87.3%) | D1 rush-drill peak speed (cross-side r 0.64, max \|r\| 0.715 vs forty, coverage 100%) | **Primary (H1, H2)** | 0.826 / 0.780 |
| A (`composite_sensA`) | O3, O4 (40 acceleration shape) | D1, D5 (40 acceleration shape) | Secondary S0 | not computed for A |
| B (`composite_sensB`) | O1, O3, O4 | D1, D5 | Sensitivity SA10 | |
| DL-only | none | D1 | Sensitivity SA12 (rule 6 contingency) | |
| k5 | O3 recomputed with 5-frame smoothing | D1 recomputed with 5-frame smoothing | Sensitivity SA13 | |

How the composites are built:
- **Composite value:** the equal-weighted mean of the oriented within-position × within-draft-year z-scores of the components (`traits.build_composites`). A player needs ≥ 1 component.
- **Gap:** gap_raw = composite(rusher) − composite(blocker). The model term `gap` is gap_raw divided by its SD over the reps of the version's primary set (1.253 for P). Coefficients are therefore per SD of the gap. R3 also reports them per 1 composite-z unit (β / SD).

Known fragilities and how each is handled:

| Fragility | Handling |
|---|---|
| O3 passes with 3-frame smoothing (r 0.70) but would fail with 5-frame (0.57) | SA12 DL-only (what rule 6 would prescribe if O3 failed); SA13 5-frame composites |
| D1 is near the redundancy line (\|r\| 0.715 vs forty; rep-level r −0.61 with rusher weight, −0.68 with rusher forty) | M1 controls each player's size and stopwatch measures with side-specific coefficients (section 5.2). β_gap is identified only from the part of the drill-speed difference that these measures do not linearly predict (about 62% of the gap's variance; R² 0.375, outcome-free) |
| O4/D5 miss coverage by one blocker / two rushers | S0 (decision 1) |
| O1 misses its CI bound by 0.007 | Composite B, SA10 |
| D4 is not estimable | No action; reported in T1 |

Composite reliabilities below 1 attenuate β_gap toward zero. The writeup may state this qualitatively. A disattenuated estimate is exploratory.

---

## 4. Outcomes

| Role | Variable | Definition | Rows used |
|---|---|---|---|
| **Primary** | `pressure_allowed` | Blocker charged with a pressure on the rep (binary, "rep lost") | P |
| S3a | `peak_pressure_probability_allowed` | Continuous, in [0, 1]; analysed on the probability scale and reported in percentage points | P, rows with non-null value (null count reported) |
| S3b | rusher pressure = `rusher_time_to_pressure` non-null | Per the host, with `blitzing` true a null `time_to_pressure` means no pressure | P |
| Placebo | `pressure_allowed` on non-engaged pairs | The blocker allowed a pressure on that play, to anyone | PL |
| Not analysed confirmatory | `sack_allowed`, `time_to_pressure_allowed`, `rusher_quick_pressure`, `rusher_sack` | Exploratory only | |

A blocker who appears in several engaged pairs on one play carries the same `pressure_allowed` in each. The primary keeps all pairs, because each is a distinct engaged rep. SA9 keeps one pair per (play, blocker).

---

## 5. Model specification

### 5.1 Transformation constants

All transformation constants are computed **once per composite version, on that version's primary set**: P for the registered composite, P-A for composite A, P-B for composite B, P-DL for DL-only. They include means, SDs, spline knots and imputation values. Every model using that version reuses them, including placebo, threshold variants, subsets and CV folds. They use no outcome data, so reusing them inside cross-validation does not leak anything. Players who appear only in a non-primary set (for example placebo pairs) are standardised with the same constants.

Player-level standardisation for measure m and side s ∈ {B (blocker), R (rusher)}:
- z_{m,s} = (x − μ_{m,s}) / σ_{m,s}, with μ and σ (ddof = 1) taken over the **distinct players** of side s in the primary set.
- A missing value is set to z = 0 (the side mean), and a missing flag is set.

Rep-level standardisation: a column marked std(·) is centred and scaled to SD 1 over the reps of the primary set.

### 5.2 Columns (exact)

**Context block C (21 columns, all models):**

| Column(s) | Definition |
|---|---|
| `db1, db2, db3` | Restricted cubic spline of `dropback_duration` (Harrell; 4 knots at the 5th, 35th, 65th and 95th rep-level percentiles of the primary set). Basis: db1 = x; for j = 1, 2: db(j+1) = [(x−t_j)₊³ − (x−t₃)₊³ (t₄−t_j)/(t₄−t₃) + (x−t₄)₊³ (t₃−t_j)/(t₄−t₃)] / (t₄−t₁)². Each column is then std(·). (Same basis as `scripts/power_simulation.py`; patsy `cr` is not used because its basis concentrated on one outlier rep.) **Orthonormalisation (added 2026-11-07, before freeze):** the three standardised columns are then replaced by their Gram-Schmidt orthogonalisation in the order db1, db2, db3, computed over the reps of the primary set (so db1 is unchanged, db2 is the part of db2 orthogonal to db1, db3 the part orthogonal to both), each result rescaled to SD 1 over the primary set. The 3 × 3 transform is a transformation constant (section 5.1): computed once on the primary set and applied to every set, subset, fold and prediction row. This is a basis change within the spline block: the fitted dropback curve, every other coefficient and all predictions are unchanged in the GLM, and unchanged in the Bayesian model up to the prior (Normal(0, 2.5) on each of the three coefficients, in whichever basis). Reason: with the raw standardised basis db2 and db3 correlate 0.995, and on 100 simulated null datasets 46 final fits failed the R-hat rule of section 5.5 on the spline coefficients alone, although gap, α and σ mixed well (ESS in the thousands, no divergences). |
| `dd_*` (8) | Down × distance cells: down3 = min(down, 3) ∈ {1, 2, 3+}; distance bucket ∈ {≤3, 4-7, ≥8} yards to go; reference cell (1st, ≥8); 8 indicators |
| `shotgun` | `shotgun` == True (SHOTGUN or EMPTY) |
| `play_action` | `play_action` == True |
| `s2023, s2024` | Season indicators (reference 2025) |
| `pos_T, pos_C` | Blocker lined up T / C (reference G) |
| `edge` | Rusher lined up EDGE (reference INTERIOR_LINE) |
| `double_team` | `double_team` == True (for the threshold variants SA1-4, recomputed under that definition: ≥ 1 other pair on the same (game, play, rusher) engaged under the variant) |
| `pre0, pre2` | `pass_rushers_encountered` == 0, ≥ 2 (reference 1) |

**Measures block Q (20 columns; M1, M2, all derived models):**
- For m ∈ {combine_weight, arm_length, forty, ten_yd_split, short_shuttle, three_cone, ngs_athleticism_score}:
  - `d_m` = std(z_{m,R} − z_{m,B}) (the matchup difference);
  - `s_m` = std(z_{m,R} + z_{m,B}) (the sum).
  - Together these give each player's measure its own coefficient (β_R = β_d + β_s, β_B = β_s − β_d), so an asymmetric effect of, say, rusher speed cannot load onto the gap.
- Missing flags, side-specific, 0/1:
  - `f_dash_B`, `f_dash_R` (forty missing; ten_yd_split missing is identical for every player in P and is merged);
  - `f_shuttle_B`, `f_shuttle_R`;
  - `f_cone_B`, `f_cone_R`.
  - Weight, arm length and NGS athleticism are never missing.
- Size sub-block Q_size = {d_weight, s_weight, d_arm, s_arm}.

**Pick block K (3 columns; M2, CV sets I1-I4):**
- `d_lpick` = std(log_pick_R − log_pick_B), where log_pick = ln(pick) and undrafted = ln 262;
- `f_undr_B`, `f_undr_R` (undrafted flags).
- Pick enters as a difference only, because it is the yardstick. A rusher-minus-blocker difference gives one interpretable coefficient. The confounding risk from asymmetric pick effects is small (|r| of composite with own pick ≤ 0.13). SA16 adds `s_lpick`.

**Gap:**
- `gap` = std(composite_R − composite_B).
- S1 uses `c_R` = std(composite_R) and `c_B` = std(composite_B) instead.
- CV sets also use `s_comp` = std(composite_R + composite_B).

**Column hygiene (deterministic):**
- After construction, on the rows of the set being fitted, drop columns that are constant, then columns that exactly duplicate an earlier column (order as listed above).
- Log every drop.
- Never drop `gap`, `c_R`, `c_B` or `d_lpick`; if one of these is constant, the run errors.

**Relation to the design in `scripts/power_simulation.py`.** Where `candidates_v2` left a choice open, its choices are adopted:
- down (1, 2, 3+) × yards to go (≤3, 4-7, ≥8) cells;
- the hand-built Harrell restricted cubic spline, 3 df, knots at the 5/35/65/95th percentiles, columns standardised;
- standardised baselines with missing values set to 0 plus missing flags;
- removal of exact-duplicate columns, which in P drops the ten-yard-split flag that duplicates the forty flag.

Remaining differences, each deliberate:

| # | Difference | Reason |
|---|---|---|
| 1 | M1 has no pick block | Decision 2 |
| 2 | Measures enter as difference + sum, not difference only | Appendix A #2 |
| 3 | z-scores are within side (μ and σ over that side's players), not pooled over both sides | With side-specific coefficients the fit is the same up to reparameterisation. Within-side z makes the "set to 0" imputation equal the player's own position mean rather than a pooled OL/DL mean |
| 4 | Missing and undrafted flags are side-specific 0/1, not rusher-minus-blocker differences | Same information without forcing equal-and-opposite flag effects |
| 5 | Three-cone is included (with a flag); the simulation omitted it | O3's largest stopwatch correlate is the three-cone (\|r\| 0.32). Leaving it out would let the blocker composite carry three-cone information, which is exactly what "beyond the stopwatch" must exclude |
| 6 | `pass_rushers_encountered` enters as indicators for 0 and ≥ 2, not as a linear standardised term | The values are 0 / 1 / 2 with 95% at 1, and 0 most likely marks a non-registered encounter rather than "one fewer rusher" |

These differences, and M1's omission of pick, are why the simulated MDE carries over to M1 only approximately (section 12).

### 5.3 Models

| Model | Fixed effects | Rows | Role |
|---|---|---|---|
| M0 | 1 + C + Q_size + gap | P | Information ladder |
| **M1** | **1 + C + Q + gap** (42 slopes) | **P** | **Primary, H1** |
| M2 | 1 + C + Q + K + gap (45 slopes) | P | Key secondary, H2; PC2 |
| M1-A, M2-A | As M1, M2 with composite A's gap and constants | P-A | S0 |
| M1-S1 | 1 + C + Q + c_R + c_B | P | S1 |
| M1-S2 | M1 + gap × edge | P | S2 |
| M1-S2s | 1 + C + Q + c_R + c_B + c_R × edge + c_B × edge | P | Matchup surface (figure F5 data only) |
| M1-S3a | M1, Gaussian likelihood, outcome peak pressure probability | P (non-null) | S3a |
| M1-S3b | M1, outcome rusher pressure | P | S3b |
| M1-PL, M2-PL | M1, M2 | PL | Placebo |
| R | 1 + C (no player-level covariates) | E0 ∩ engaged_primary (8,087 reps, 79 blockers, 97 rushers) | Opponent-adjusted ratings (descriptive) |

All logistic mixed models:

    y_r ~ Bernoulli(logit⁻¹(η_r)),   η_r = α + X_r β + u_{b(r)} + v_{q(r)}
    u_b = σ_B · z_b,  v_q = σ_R · z_q,  z ~ N(0, 1)    (non-centred crossed random intercepts)

M1-S3a uses y_std = (y − ȳ) / sd(y) over the non-null P rows, with Normal(η_r, σ_ε). Results are reported on the probability scale as β × sd(y) × 100 percentage points per SD of the gap.

### 5.4 Priors

| Parameter | Prior |
|---|---|
| α (logistic) | Normal(−2.25, 2) (−2.25 = logit of the known 0.095 base rate) |
| α (S3a, standardised outcome) | Normal(0, 1) |
| Spline columns db1-db3 | Normal(0, 2.5) |
| Every other slope (standardised continuous or 0/1 indicator), including gap, c_R, c_B, interactions | Normal(0, 1) |
| σ_B, σ_R | HalfNormal(1) |
| σ_ε (S3a) | HalfNormal(1) |

Prior sensitivity on β_gap: SA18 refits M1 with Normal(0, 0.5) and Normal(0, 2.5).

### 5.5 Sampler (nutpie NUTS through PyMC)

**Environment, verified 2026-11-06:**
- Python 3.12.10, PyMC 6.4.0, ArviZ 1.3.0, PyTensor 3.3.7, nutpie 0.16.11, numba 0.68.0. JAX is not installed.
- **There is no C++ compiler**, so PyTensor's C backend is unavailable and PyTensor falls back to slow Python-mode graphs. The PyMC default sampler is therefore not used. All sampling goes through **nutpie with its numba backend**.
- No posterior post-processing may evaluate PyTensor graphs (no `pm.sample_posterior_predictive`, no `pm.compute_log_likelihood`). AME, PE and the surface are computed in numpy from the posterior draws.
- Under PyMC 6.4, sampler options go in `nuts={...}`; `nuts_sampler_kwargs` is deprecated.
- All four packages are Apache-2.0 or MIT, so OSI-compatible. The script author adds pymc, arviz, nutpie and numba to `requirements.txt`, and the lock file must show these versions.

**Call (full setting)** for M0, M1, M2, M1-A, M2-A, S1, S2, S3a, S3b, M1-PL, M2-PL:

    pm.sample(nuts_sampler="nutpie", draws=2000, tune=2000, chains=4,
              cores=min(4, os.cpu_count()), random_seed=2027,
              nuts={"target_accept": 0.90, "low_rank_modified_mass_matrix": True},
              progressbar=False)

- nutpie's defaults are kept except for one option: mass-matrix adaptation uses nutpie's **low-rank modified mass matrix** (`low_rank_modified_mass_matrix=True`; added 2026-11-07, before freeze, after the pre-freeze tests showed slow mixing of the correlated spline coefficients under the default diagonal adaptation; on four simulated null datasets it cut max R-hat from 1.014-1.060 to 1.004-1.011 and raised bulk ESS from about 1,700 to 4,000-6,600, at about twice the sampling time). Maximum tree depth 10 and nutpie's own initialisation are unchanged (`init` does not apply). The option changes the sampler, not the posterior.
- All fits go through the direct nutpie interface, which is the equivalent of the call above:

      compiled = nutpie.compile_pymc_model(model, backend="numba")
      nutpie.sample(compiled, draws=…, tune=…, chains=4, cores=…, seed=…, target_accept=…,
                    low_rank_modified_mass_matrix=True)

  The model is compiled once, with the outcome as `pm.Data`, and outcomes are swapped with `compiled.with_data(...)`. The settings must be identical to the `pm.sample` call.
- The returned object is an xarray DataTree / ArviZ 1.x InferenceData, saved with `.to_netcdf()` (backend `h5netcdf`, which is in `requirements.txt`).

**Light setting** (sensitivities SA1-SA7 and SA9-SA18; S5a/S5b; S2s; R; pre-freeze simulation tests): draws=1000, tune=1000, otherwise identical.

**Convergence criteria**, all required for each fit, computed with ArviZ 1.3 (`az.rhat`, `az.ess` with method "bulk" and "tail") and the `diverging` field of `sample_stats`:
- max R-hat ≤ 1.01 over α, β, σ;
- bulk and tail ESS ≥ 400 for gap (or c_R, c_B, interaction, d_lpick where present);
- divergences ≤ 0.1% of post-warm-up draws.

**Escalation, once:** refit with draws=4000, tune=4000, `nuts={"target_accept": 0.97}`, random_seed=2028.
- If a full-setting fit still fails, the GLM mirror (with the κ-calibrated interval, section 5.6) becomes that model's decision basis. It is flagged in R2 and in the headline sentence.
- If a light-setting fit still fails, it is reported with a "not converged" flag.

**Reproducibility:** with fixed seed, versions and chain count, nutpie draws are expected to be reproducible. The run log records `os.cpu_count()` and the `cores` value actually used.

### 5.6 Frequentist mirror (GLM)

- **Fit:** the same fixed-effect matrix in a `statsmodels` GLM with `Binomial()` family (Gaussian for S3a), IRLS, maxiter 100.
- **Two-way cluster-robust covariance** (Cameron-Gelbach-Miller):
  - V = V_blocker + V_rusher − V_dyad, each computed with `cov_type="cluster"` and statsmodels' default small-sample correction;
  - if V is not positive semi-definite, clip negative eigenvalues to 0.
- **Inference, two versions, both always reported:**
  1. **Nominal:** t reference with G − 1 degrees of freedom, G = min(#blockers, #rushers) in the fitted rows. 95% CI = β ± t_{0.975, G−1} × SE, with p-values from the same reference.
  2. **κ-calibrated:** the same with SE replaced by κ × SE, **κ = 1.20**.
- **Where κ comes from.** In the power simulation's null runs, the empirical SD of the gap estimate divided by the mean two-way cluster SE was 0.0816 / 0.0683 = 1.195 (registered) and 0.0734 / 0.0616 = 1.192 (composite A). Across the dyad-weighted and REG-only variants it was 1.19-1.21. A z test with SEs inflated by κ ≈ 1.2 has about nominal size under the simulated generator. κ is fixed here and is not re-estimated after unsealing.
- **Which version is used where.** Q1 (section 6.3), the GLM fallback (section 5.5) and every GLM interval labelled "calibrated" in R3-R9 use the κ-calibrated version. The nominal version is shown alongside for transparency.
- **Why both a t reference and κ.** The t(G − 1) reference corrects for the number of clusters, but the simulation shows that it barely helps here: type-I error 0.114 vs 0.118 with the normal reference. The remaining problem is SE bias, not the degrees of freedom. κ depends on the simulation's assumptions (generator, RE SD 0.35), so the **calibrated frequentist check that does not depend on the generator is the Freedman-Lane permutation test (Q2)**. Neither GLM version decides H1.
- **Weighted fits** (SA8, SC4): `freq_weights` with the same covariance and the same two inference versions.

---

## 6. Estimands, units and decision criteria

### 6.1 Primary estimand

β_gap in M1, in log-odds per SD of the athletic gap. R3 reports:
- the posterior mean and median;
- the 95% equal-tailed interval;
- P(β_gap > 0);
- **P(β_gap < 0.10)**, the posterior probability that the effect is smaller than the smallest effect of interest (section 6.3).

### 6.2 Units the script reports for every gap estimate in M0, M1, M2, M1-A, M2-A

1. **Log-odds per SD** of the gap, and per 1 composite-z unit.
2. **Pressure-probability units:**
   - AME = mean over the rows of P of [logit⁻¹(η_r + β_gap) − logit⁻¹(η_r)], per posterior draw, using 1,000 evenly thinned draws. η_r includes the fitted random intercepts.
   - Reported in percentage points per rep, as extra pressures per 100 engaged reps, and as "reps per extra pressure" (1 / AME; reported only if the AME interval excludes 0).
   - For comparison with the power simulation, the base-rate version logit⁻¹(logit(0.0952) + β) − 0.0952 is also given.
3. **Draft-pick equivalents** (only if PC2 passes, section 8). They use M2's coefficient on `d_lpick` (β_lpd, per SD of the log-pick difference) and SD_lpd = the SD over P of (log_pick_R − log_pick_B). For each draw i:
   - k_i = β_gap,i / (−β_lpd,i): the gap SD is worth k pick-difference SDs;
   - δ_i = k_i × SD_lpd (log-pick units);
   - pick ratio_i = exp(δ_i);
   - slots64_i = 64 − 64 / exp(δ_i): "a 1-SD gap is worth the rusher being drafted at pick 64 / exp(δ) instead of 64 against the same blocker".
   - Median and 95% interval of each are reported.
   - For M2's own gap, draws come from the same posterior. For M1's gap, M1 draw i is paired with M2 draw i. This is a unit conversion across two independent posteriors, and it is stated as such.
   - For context, R3 also gives the SD of the raw pick difference in P (about 96 picks).

### 6.3 Verdict for H1 (computed mechanically by the script)

Smallest effect size of interest (SESOI) = **0.10 log-odds per SD**: half the C3 pick-difference effect per SD, or about +0.9 percentage points of pressure per rep at the 9.5% base rate. It was fixed from the positive control before outcomes. It is used only for P(β < SESOI) and for the wording of a null result, not for the verdict.

| Category | Condition on the M1 95% posterior interval [lo, hi] of β_gap | Reported as |
|---|---|---|
| **Supported** | lo > 0 | Estimate in all units of 6.2 |
| **Opposite** | hi < 0 | "Contrary to the hypothesis: a more athletic rusher relative to the blocker went with less pressure"; estimate in all units |
| **Inconclusive** | lo ≤ 0 ≤ hi | Bounded estimate: "beyond size, stopwatch and NGS athleticism, a 1-SD athletic gap is worth at most hi log-odds (≤ AME_97.5 percentage points per rep; ≤ slots64_97.5 draft slots at pick 64)", plus P(β < 0.10) and the MDE from section 12 |

**Qualifiers.** They change the wording, never the category. All are reported whatever the verdict.

| ID | Qualifier | Passes when |
|---|---|---|
| Q1 | GLM mirror agrees | The mirror's κ-calibrated 95% CI (section 5.6) excludes 0 in the same direction as the verdict (if Supported or Opposite) |
| Q2 | Freedman-Lane permutation | Two-sided studentized permutation p < 0.05 (V5) |
| Q3 | Rep-specific (placebo) | Placebo ratio β_gap(M1-PL) / β_gap(M1) ≤ 0.5, ratio of posterior medians (V6) |
| Q4 | No discordant sensitivity | Section 9 rule |
| Q5 | No engagement-selection problem | SC2 not flagged, or SC2 flagged and SC3a's gap has the same sign as M1's |

**Final label:**
- "Supported (robust)" if Supported and Q1-Q3 all pass.
- "Supported (qualified: <failing qualifiers>)" otherwise.
- Q4 and Q5 failures are named in the text under any category.
- "Opposite" and "Inconclusive" carry their qualifiers the same way.
- **Calibration contingency (resolved before freeze).** The Bayesian criterion is run on 100 null simulations before the freeze (test T1, section 13.3).
  - If **10 or more of the 100** null datasets give a 95% interval for β_gap that excludes 0, in either direction, the categories "Supported" and "Opposite" additionally require Q2 (permutation p < 0.05). A result with the interval excluding 0 but Q2 failing is then categorised "Inconclusive".
  - If 9 or fewer exclude 0, the criterion stands as registered.
  - The threshold separates nominal calibration from the GLM's observed miscalibration. If the true rate were 5%, P(≥ 10 of 100) = 0.03; at the cluster Wald test's simulated 11.8%, P(≥ 10) = 0.76.
  - The outcome of T1 and the contingency status (ACTIVE / INACTIVE) are written into section 13.1 (`CALIBRATION_CONTINGENCY`) before hashing, and copied into R2.

H2 and S0 receive the same category computation (with M2 and M1-A/M2-A) and are labelled secondary.

### 6.4 Multiplicity

- There is exactly **one confirmatory test (H1)**. No multiplicity correction applies to it.
- The secondaries are: H2, M0, S0 (two models), S1 (two terms), S2 (interaction, plus the derived EDGE and INTERIOR slopes), S3a, S3b, S5 (two coefficients and a share). That makes about 10 interval statements.
- They are reported with unadjusted 95% intervals and **no confirmatory claims**. The writeup uses "consistent with" and "suggests", never "confirms" or "shows", for secondaries.
- R5 carries the line: "If every secondary effect were null, about one in 20 intervals would exclude 0 by chance."
- S4 (CV), the validation checks and the sensitivities are not hypothesis tests.

---

## 7. Secondary analyses (specification details)

- **H2:** M2. Same units and same category computation as H1.
- **M0:** context + size only. It shows how much of the gap association the official measures absorb (M0 → M1) and how much pick absorbs on top (M1 → M2).
- **S0:**
  - M1-A and M2-A on P-A, with composite A's own constants.
  - SA11 refits M1-A on the rows of P (common sample), to separate the change of composite from the change of sample.
- **S1:**
  - Reports β_R (on c_R) and β_B (on c_B).
  - Expected β_R > 0 and β_B < 0.
  - Also reports β_R + β_B: on these separately standardised scales, it measures how far the two sides' effects depart from equal and opposite.
- **S2:**
  - β_int on gap × edge, plus the derived slopes β_gap (INTERIOR) and β_gap + β_int (EDGE), all with posterior intervals.
  - The football reading (tackle-or-guard, edge-or-interior) is allowed only as "consistent with", and only if β_int's interval excludes 0.
- **S2s surface (figure data only):** predicted pressure probability on the grid c_R, c_B ∈ {−2.00, −1.75, …, 2.00} (composite-z units, converted to the std scale using the P constants), for edge ∈ {0, 1}.
  - Marginal standardisation: average logit⁻¹ over the P reps of that alignment, with their own context and measures, and random effects set to 0.
  - Posterior median and 90% interval per cell, written to CSV.
- **S3a:** M1-S3a. Expected > 0. Reported in percentage points per SD of the gap.
- **S3b:** M1-S3b. Expected > 0. Its coherence with H1 (same sign) is described, not tested.
- **S5 ("giving ground")**, on P, using `blocker_back_disp_05s`. It has no nulls in P; if any appear, drop the row and count it.
  - S5a: logistic, 1 + C + std(blocker_back_disp_05s) + blocker random intercept only.
  - S5b: 1 + C + std(back_disp_05s) + c_R + the rusher-side measures (z_{m,R} for the seven measures plus f_dash_R, f_shuttle_R, f_cone_R) + blocker and rusher random intercepts.
  - Report β_depth in both, and share = 1 − median(β_depth,S5b) / median(β_depth,S5a) (a descriptive point estimate). Light sampler.
  - Expected β_depth,S5a > 0 (the C1 wrong-sign association) and share > 0.
- **Opponent-adjusted ratings (descriptive):** model R.
  - Blocker rating = −u_b (higher = better pass protection); rusher rating = v_q.
  - Posterior mean, SD and 5%/95% per player, written to CSV. Used later for T2 and case studies. Not a hypothesis.

---

## 8. Validation suite

| ID | Check | Specification | Expectation | Consequence |
|---|---|---|---|---|
| **V0** | Data integrity | Recompute the section 2.3 counts; 1:1 outcome join; no nulls in `pressure_allowed` on P | Exact match | **Decisive: stop** on mismatch |
| **V1 = PC1** | Exact reproduction of C3-G2 | All 8,271 `engaged_primary` rows of `engaged_pairs` (no position filters). Logit of `pressure_allowed` on const + z(rusher pick − blocker pick, raw picks, undrafted = 262) + z(rusher weight − blocker weight) + dropback_duration (seconds). z over these 8,271 rows. SE clustered by blocker | Events = 787; pick coef −0.204 ± 0.003; dropback 0.577 ± 0.003 | **Decisive: stop before any H1 model is fitted.** A failure means the outcome join or file is not the one the project validated. Diagnose, record a deviation, rerun |
| **V2 = PC2** | Model-level positive control | M2 coefficient on `d_lpick` | Negative, 95% interval entirely < 0; magnitude expected around 0.20 per SD (not required) | Pass: draft-pick equivalents reported. **Fail:** no draft-pick equivalents anywhere (probability units only); stated in R2 and in the headline. Not a stop |
| **V3** | Convergence | Section 5.5 | All criteria | Escalation, then GLM fallback |
| V4 = Q1 | GLM mirror | Section 5.6, for every Bayesian model listed in R4/R5 | Same sign as the Bayesian estimate | Qualifier |
| V5 = Q2 | Freedman-Lane permutation (2,000) | Below | Under H0, p uniform | Qualifier |
| V6 = Q3 | Placebo on non-engaged pairs | Below | β_gap(PL) ≤ ½ β_gap(P). Calibration: pick ratio on PL vs P ≈ 0.37 (C3: −0.075 / −0.204) | Qualifier (interpretable only if H1 is Supported or Opposite) |
| V7 = S4 | Two-way grouped CV of information sets | Below | Descriptive | None |
| V8 | Leave-one-class-out, leave-one-season-out | Below | Descriptive | None |
| V9 | Selection checks SC1-SC4 | Section 10 | | SC2 feeds Q5 |
| V10 | Prior sensitivity | SA18 | | Named if discordant |

**V5, Freedman-Lane permutation (GLM mirror of M1, on P):**
1. For each side s, fit a player-level OLS over the distinct players of s in P: composite_j ~ 1 + the seven z_{m,s} + that side's missing flags. This gives fitted values f_j and residuals e_j.
2. For k = 1…2,000, permute e within side × draft class, using one `numpy.random.default_rng(2027)` stream for all k. Set composite*_j = f_j + e_{π(j)}. Recompute gap* = (composite*_R − composite*_B) / 1.253 (the observed SD, so the units are fixed).
3. Refit the GLM M1 and record β* and the **studentized statistic** t* = β* / SE*_two-way, using the nominal cluster SE (κ cancels).
4. The test statistic is t. Two-sided p = (1 + #{|t*| ≥ |t_obs|}) / 2,001; the one-sided p (t* ≥ t_obs) and the coefficient-based p (|β*| ≥ |β_obs|) are also reported.

The studentized statistic is used because permutation tests on a studentized statistic stay closer to nominal size when exposure is very unequal across players (the top 10 blockers hold 35% of the reps in P). Its calibration is checked before freeze in test T1b.

Permuting the part of the composite that the club measures do not explain preserves the correlation of composite with the controls, and respects player-level clustering and class exposure.

**V6, placebo:**
- M1-PL and M2-PL on PL (17,795 pairs), Bayesian (full setting) and GLM, using P's constants.
- Ratios use posterior medians: ratio_gap = med β_gap(PL) / med β_gap(P); ratio_pick = med β_lpd(PL) / med β_lpd(P).
- A pressure on a play is shared by all of that blocker's pairs on the play. The random effects and the clustering absorb part of this dependence; the remaining dependence is noted.

**V7, two-way grouped CV (S4):**
- Information sets (GLM, fixed effects only, unpenalised):
  - I0 = C;
  - I1 = C + Q_size + K ("what the draft knows");
  - I2 = I1 + (Q minus Q_size) ("what clubs measure");
  - I3 = I1 + gap + s_comp;
  - I4 = I2 + gap + s_comp.
- Repetitions r = 0…19, each with `default_rng(2027 + r)`:
  - randomly assign the distinct blockers of P to 3 near-equal groups, and independently the rushers to 3 groups;
  - for each of the 9 cells (i, j), train on reps whose blocker ∉ group i **and** rusher ∉ group j, and predict the reps with blocker ∈ i and rusher ∈ j;
  - pool the predictions of all 9 cells, so every rep is predicted once per repetition.
- Columns constant in a training fold are dropped for that fold. p is clipped to [1e-6, 1 − 1e-6].
- Metrics: log loss and Brier score.
- Reported: the mean over repetitions for each set; ΔLL(I4 − I2) and ΔLL(I3 − I1) in millinats per rep, with their 2.5/97.5 percentiles over repetitions (described as split variability, not a CI); and the share of repetitions with Δ < 0. Δ < 0 means tracking improves prediction.

**V8:**
- **Leave-one-class-out**, for draft class c ∈ {2023, 2024, 2025}: test = reps in which blocker or rusher is from class c; train = reps in which neither is. Report LL(I2), LL(I4) and ΔLL.
- **Leave-one-season-out**, for season s: train on the other two seasons, test on s. Season indicators are excluded from all leave-one-season-out fits. Report ΔLL.
- **By-season coefficient:** GLM M1 fitted separately per season, with season indicators removed. 2023 (431 reps) is flagged as imprecise.

---

## 9. Sensitivity analyses

Each sensitivity is fitted with the GLM mirror and the Bayesian model (light setting); SA8 is GLM only. P's constants are used unless stated otherwise. The target is β_gap of M1 (M2 for SA16). Composite versions use their own constants.

| ID | Variation | Rows |
|---|---|---|
| SA1-SA4 | Engagement thresholds 1.25 yd / 4 frames, 2.0 yd / 4, 1.5 yd / 3, 1.5 yd / 6 (double-team flag recomputed under the variant) | P-thr |
| SA5 | REG only | 6,867 |
| SA6 | Exclude double teams | 6,261 |
| SA7 | Rushers whose `rusher_nfl_position` ∈ {DE, DT, NT} (excludes combine-DL players listed as OLB) | 5,326 |
| SA8 | Dyad-equal weighting, w = (N / D) / n_dyad (GLM only) | P |
| SA9 | One pair per (game, play, blocker): keep the pair with the smallest `min_dist` | P |
| SA10 | Composite B | P-B |
| SA11 | Composite A on P's rows (common sample) | P ∩ P-A |
| SA12 | DL-only: rusher composite (std) replaces gap; blocker side has no composite term | P-DL |
| SA13 | 5-frame smoothing: O3 and D1 recomputed with `traits.evaluate_trait(tid, reps, cr, k=5)`, z within position × draft year as in `build_composites`; composite = that z (registered components, no re-gating). Players lacking a k5 value drop | P with k5 composites |
| SA14 | Remove the dropback spline (the dropback duration is partly set by the rep's own outcome) | P |
| SA15 | Complete cases for the dash: both players have an official forty | P |
| SA16 | M2 + `s_lpick` (pick-asymmetry check) | P |
| SA17 | M1 + dyad random intercept (HalfNormal(1) SD) | P |
| SA18 | β_gap prior Normal(0, 0.5) and Normal(0, 2.5) | P |

**Discordance rule (feeds Q4):**
- If H1 is Supported or Opposite, a sensitivity is **discordant** when its Bayesian point estimate has the opposite sign to M1's, or its magnitude is < 50% of M1's.
- If H1 is Inconclusive, a sensitivity is discordant when its 95% interval excludes 0.
- Every discordant sensitivity is named in the writeup.
- No sensitivity changes the verdict, and none may be promoted to the headline.

Two items of the `candidates_v2` §3.6 list have changed:
- "Dropping the 40-derived traits" is satisfied by construction, because the registered composite has none; S0/SA11 is the comparison.
- "Dropping pick" is now the primary itself (M1); M2 is its counterpart.

---

## 10. Selection analyses (V9)

- **SC1, who is in the analysis set:**
  - Population: per side, all players in `combine_traits` with a non-null registered composite (OL 105, DL 118).
  - Compare the composite of in-P players with out-of-P players: mean difference with a player bootstrap 95% CI (2,000, `default_rng(2027)`) and a KS p-value.
  - Also describe the same comparison for log pick and NGS athleticism.
  - Separately describe the 10 engaged blockers without an O3 value (873 engaged reps) against the 69: mean log pick, NGS athleticism, share missing the forty.
- **SC2, does the gap predict being engaged:**
  - Rows: ALL (25,009 pairs).
  - GLM logistic of `engaged_primary` on 1 + (C without `double_team`, which is defined from other pairs' engagement) + Q + gap, with two-way cluster SE and t reference.
  - **Flagged** if the κ-calibrated 95% CI of the gap coefficient excludes 0.
- **SC3, all-pairs bound:**
  - On ALL, GLM of `pressure_allowed` on (a) 1 + C + Q + gap + engaged_primary, and (b) (a) + gap × engaged_primary.
  - Always reported. If SC2 is flagged, (a)'s gap coefficient is reported next to the primary as the selection-robust bound.
- **SC4, inverse-probability weights:**
  - Per side, logistic at player level over the SC1 population: in-P ~ log_pick + undrafted + ngs_athleticism_score + draft-class indicators.
  - Stabilised weight w_j = (share in P) / p̂_j, truncated at its within-side 1st and 99th percentiles.
  - Rep weight = w_blocker × w_rusher, normalised to mean 1.
  - Weighted GLM M1 (`freq_weights`, two-way cluster). Reported in R9.

---

## 11. Missing data

| Item | Situation (computed on P) | Rule |
|---|---|---|
| Rep covariates in C | 0 nulls in P (`dataset_build.md` §6) | Any row with a null in a C variable is dropped and counted. This affects only PL/ALL: 4 pairs have null `shotgun` |
| Primary outcome | 0 nulls among engaged reps | Drop and count. A null on P is a V0 failure |
| S3a outcome | Unknown | Drop nulls, count, report |
| Official measures | Blockers (69): forty / ten-yard split missing 12, short shuttle 32, three-cone 37. Rushers (97): 19, 59, 60. Weight, arm length, NGS athleticism: 0 | Impute at the side mean of P's players (z = 0) plus a side-specific missing flag; forty and ten-yard-split flags merged (identical); SA15 is the complete-case check |
| Draft pick | Undrafted: 3 of 69 blockers, 16 of 97 rushers | pick = 262 (log 262) plus undrafted flags (M2, K) |
| **Composite** | A player needs ≥ 1 component. Registered: 69 of 79 engaged blockers have O3 (10 have no mirror rep with ≥ 4 reversals; 873 engaged reps lost); 97 of 97 rushers have D1. Composite A: 75 of 79 blockers. Composite B: 79 of 79 | **Not imputed.** It is the hypothesis variable, and imputation would dilute and blur it. P = 7,214 reps, 69 blockers, 97 rushers. The 10 excluded blockers are described in SC1 and re-enter in SA12 (DL-only, 8,087 reps) |
| Back displacement (S5) | 0 nulls in P | Drop and count |

---

## 12. Power and minimum detectable effect

Source: `reports/power_simulation.md` and `scripts/power_simulation.py` (500 simulations per setting, seed 2027; the sealed file was not opened). Nothing in this section changes any rule above. The MDE only calibrates how a null is worded and what the design can be expected to find.

### 12.1 Simulation set-up

- **Generator:** logistic, logit P = a − 0.20 × z(log-pick difference) + 0.58 × z(dropback) + β_gap × gap + u_blocker + u_rusher, with crossed random intercepts of SD 0.35 (0.20 and 0.50 as sensitivity), and a solved so the mean rate is 0.0952. No other covariate has an effect.
- **Fit:** the frequentist mirror (logistic GLM, two-way cluster-robust SE, Wald z at two-sided 0.05) with the **`candidates_v2` covariate set**: rusher-minus-blocker differences including log pick. This is closest to M2 without sum terms.
- **Analysis sets:** exactly those of section 2.3. Registered: 7,214 reps, 69 blockers, 97 rushers, 1,201 dyads. Composite A: 7,720 reps, 75 blockers, 97 rushers, 1,281 dyads.
- **Carry-over to M1 is approximate.** M1 drops the pick block and adds sum terms and the three-cone (section 5.2). Pick explains about 4% of the gap's variance and is nearly uncorrelated with it (r ≈ −0.02), so the MDE is expected to transfer **approximately** to M1. It was not simulated for M1 or for the Bayesian model. The Bayesian criterion's own size is checked by T1 (section 13.3).

### 12.2 Power, registered composite (RE SD 0.35, reps equally weighted)

| Planted β_gap (log-odds/SD) | 0.00 (type-I) | 0.10 | 0.15 | 0.20 | 0.30 | 0.40 |
|---|---|---|---|---|---|---|
| Registered, Wald z as simulated | 0.118 | 0.352 | 0.562 | 0.776 | 0.974 | 0.998 |
| Registered, t(G − 1) reference | 0.114 | 0.346 | 0.552 | 0.774 | 0.970 | 0.996 |
| Registered, size-adjusted (calibrated critical value) | 0.050 | 0.260 | 0.428 | 0.674 | 0.942 | 0.992 |
| Composite A, Wald z as simulated | 0.104 | 0.378 | 0.640 | 0.840 | 0.992 | 1.000 |
| Composite A, size-adjusted | 0.050 | 0.244 | 0.458 | 0.716 | 0.964 | 1.000 |

The estimate of β_gap is nearly unbiased: |bias| ≤ 0.012 across all planted effects. Its empirical SD at the null is 0.082 for the registered composite and 0.073 for A. The mean two-way cluster SE is too small by about 15-20% (0.068 and 0.062), which is the source of the inflated type-I rate and of κ = 1.20 (section 5.6).

### 12.3 Minimum detectable effect at 80% power

| Composite | Variant | MDE, Wald z as simulated | MDE, size-adjusted | Size-adjusted MDE in pick-difference SDs (MDE / 0.20) | Size-adjusted MDE in pp per rep at base rate 9.52% |
|---|---|---|---|---|---|
| **Registered** | **standard, RE SD 0.35** | 0.212 (1.06 pick SDs, +1.99 pp) | **0.247** | **1.24** | **+2.35** |
| Registered | RE SD 0.20 / 0.50 | 0.168 / 0.275 | 0.176 / 0.333 | | |
| Registered | dyad-equal weights | 0.265 | 0.306 | | |
| Registered | REG only | 0.213 | 0.249 | | |
| **Composite A** | **standard, RE SD 0.35** | 0.190 (0.95 pick SDs, +1.77 pp) | **0.234** | **1.17** | **+2.22** |
| Composite A | dyad-equal weights / REG only | 0.245 / 0.191 | 0.264 / 0.236 | | |

**Continuous secondary S3a** (assumption-based: outcome mean 0.25, SD 0.20, RE SD 0.05 per side, none of these known): MDE about 0.024 probability units per SD of the gap (about 0.12 outcome SD) for both composites. The cluster Wald test's type-I rate is again inflated (0.13).

### 12.4 Which MDE is registered, and why

The registered MDEs used in the null wording (R3, R11) are the **size-adjusted** values: **0.247** (registered composite) and **0.234** (composite A).
- The as-simulated MDEs (0.212, 0.190) come from a test that rejects a true null 10-12% of the time. They overstate what any correctly sized test can detect.
- The size-adjusted MDE is what a test with true 5% size detects with 80% power under the generator. The Bayesian interval, if calibrated (T1), and the Freedman-Lane test are such tests. It is the honest planning number.
- It still depends on the assumed RE SD (0.176-0.333 across 0.20-0.50).

### 12.5 What this means for interpretation (fixed before outcomes)

- The design can detect an athletic-gap effect of about the size of the whole draft-pick effect: roughly 1.2 pick-difference SDs, or +2.3 pp of pressure per rep per SD.
- It has only about 26-35% power for the SESOI of 0.10 (half the pick effect).
- An "Inconclusive" verdict is therefore the most likely result unless the true effect is at least as large as draft slot's. It must be worded as a bound ("at most …"), never as "no effect".
- If the true effect equals the pick effect (0.20), the chance of "Supported" is about 0.67 (size-adjusted).

Machine-readable lines (parsed by the script for the headline sentence):

    MDE_REGISTERED_LOGODDS: 0.247
    MDE_SENSA_LOGODDS: 0.234

---

## 13. Freezing procedure and deviations policy

### 13.1 Freeze manifest (filled by the coordinator at freeze; parsed by the script)

    SCRIPT_SHA256: 8d842b70db03e2b0aa223f827bf0a496cb971ca3ea03f0a7c56563be8c046aca
    INPUT_SHA256 data/processed/engaged_pairs.parquet: bb29bff6712c71f59a7bf5290bdf7253c616f13353c8c230a92c8e4708d890a9
    INPUT_SHA256 data/processed/player_baselines.parquet: f5c476d4130644559d61d5363c5929f039c92cc2b5550b97c0097dafaf3831cb
    INPUT_SHA256 data/processed/combine_traits.parquet: a2becc421396521e55c4033bbce3a64270267c63bf27336ffddbe0c61b67c518
    INPUT_SHA256 data/processed/engaged_outcomes_SEALED.parquet: d682dff07ce30dcdb84912a0dbdbc64046ae7ea446eb2a78d86a085407d5b517
    INPUT_SHA256 data/processed/combine_tracking.parquet: 76e6942d2308d76d11ed5c6c025a7a51eecbbf55264ef118a1a10c2de22d2e5e
    INPUT_SHA256 data/processed/combine_results.parquet: ed3b80b61262b328c73c345c4b3896d533d3d5b9dd4cb613906f63d8b1545096
    INPUT_SHA256 src/bdb2027/traits.py: 2965e1883dc79db3b5e0da469c363667d1ce02041cff53c86b1255d9d3c9eb16
    INPUT_SHA256 src/bdb2027/paths.py: 59f103f72a33e0835d62addc1b5ef3d43aadbf1e8b25a965c5ed34d5e2d05f21
    PACKAGE_VERSIONS: python 3.12.10; pymc 6.4.0; arviz 1.3.0; pytensor 3.3.7; nutpie 0.16.11; numba 0.68.0; statsmodels 0.15.0; numpy 2.5.4; pandas 3.1.1; polars 2.1.0; scipy 1.18.1
    SAMPLER: nutpie (numba backend, low-rank modified mass matrix); no C++ compiler in the environment
    KAPPA_GLM_SE_INFLATION: 1.20
    CALIBRATION_CONTINGENCY: INACTIVE (6 of 100 null intervals excluded 0; 0 of 100 final fits failed the convergence criteria, 9 escalated)
    PERMUTATION_CALIBRATION: 2 of 50 null datasets with permutation p < 0.05
    FREEZE_COMMIT: [fill after commit, in the commit message / tag, not in this file]

The hashes of the data and source files above were computed on 2026-11-06 while this document was drafted (the two combine files, read by SA13 through `traits.py`, were added on 2026-11-07), and must still match at freeze. The package versions were read from `.venv` on the same date; the script aborts if the installed versions differ (guard 2b). The sealed file's hash is computed over its bytes by the coordinator; the file is not parsed. The two calibration lines are not hashes but pre-freeze test results. They are written in by the coordinator from `reports/confirmatory_script_tests.md` before the document is hashed, and no outcome is involved.

### 13.2 Sequence

1. This document is complete except for the section 13.1 fields marked [fill].
2. A separate agent (the script author) writes `scripts/confirmatory_analysis.py` from sections 2-11 and 14. It tests the script only in `--mode simulate`: T2-T6 first, then the calibration runs T1 and T1b on the feature-complete script. It writes `reports/confirmatory_script_tests.md`. If any model-fitting or test code changes after T1/T1b have run, T1/T1b are rerun.
3. The coordinator checks the test report and fills `CALIBRATION_CONTINGENCY`, `PERMUTATION_CALIBRATION`, `SCRIPT_SHA256` and the sealed-file hash in section 13.1.
4. The coordinator computes the SHA-256 of `reports/preregistration.md`, commits the document, the script and the test report together, and tags the commit `prereg-frozen`. The tag message holds the document hash.
5. The confirmatory run happens once: `python scripts/confirmatory_analysis.py --mode confirmatory`.
6. From this point every further specification is exploratory and is appended to `reports/specification_log.md` (date, specification, reason, result).

Changes before step 5 (for example, a bug found during simulation tests) are a **re-freeze**: a new hash, a new commit, and a dated changelog entry at the end of this document. They are allowed because no outcome has been seen.

### 13.3 Script specification

**Command line:**
- `--mode simulate --sim-beta-gap <float> --sim-seed <int> [--light] [--only <step>]`.
  - Builds everything, but replaces the outcomes with simulated ones. The generator is the power simulation's: logit P = a − 0.20 × `d_lpick` + 0.58 × std(dropback_duration) + β_gap × `gap` + u_b + v_q; u, v ~ N(0, 0.35²) crossed; a solved so that the mean rate is 0.0952; no other effects.
  - For S3a, a Gaussian generator with the same planted standardised effect; for S3b, the same generator as the primary with an independent draw.
  - `--only` is allowed in simulate mode only.
- `--mode confirmatory`. No other options except `--rerun-reason "<text>"` (section 13.4).

**Sealed-file isolation:** the sealed path is referenced only inside one function, `load_sealed_outcomes()`. That function raises unless the mode is confirmatory and all guards have passed. Test T5 verifies this.

**Guards in confirmatory mode, before anything else:**
1. The script's own SHA-256 equals `SCRIPT_SHA256` parsed from `reports/preregistration.md`.
2. Every `INPUT_SHA256` matches.
   - 2b. The installed versions of the packages in `PACKAGE_VERSIONS` match.
   - 2c. `CALIBRATION_CONTINGENCY` is filled with ACTIVE or INACTIVE (the run aborts on "[fill"), and the verdict code applies it.
3. `reports/confirmatory_results.md` does not already exist. If it does, the script refuses unless `--rerun-reason` is given; it then writes to `reports/confirmatory/run_NN/` and appends the reason to `reports/deviations.md`.
4. Record the git HEAD (`git rev-parse HEAD`, read-only), the hash of `preregistration.md`, package versions, CPU count and start time.

**Fixed step order in confirmatory mode.** The run never branches on runtime or on intermediate results, except for the pre-specified PC1 stop, the convergence escalation and the PC2 unit rule.
1. Guards.
2. Build sets, constants and columns. Write R1 and a design summary.
3. Load the sealed outcomes; V0.
4. PC1. If it fails, write R0-R2 with status STOP and exit with a non-zero code.
5. M1, Bayesian and GLM.
6. M2 (and PC2), then M0.
7. H1 verdict, written immediately to R3 and R11.
8. Secondaries.
9. V5-V8.
10. Sensitivities.
11. Selection.
12. Ratings and the S2s surface.
13. Final outputs.

Results are appended to the JSON after each step, so a crash loses nothing.

**Seeds:**
- every Bayesian fit (nutpie through PyMC): `random_seed=2027` (escalation 2028);
- permutation: `default_rng(2027)`;
- CV repetition r: `default_rng(2027 + r)`;
- bootstraps: `default_rng(2027)`;
- simulate mode: `default_rng(sim_seed)`.

**Outputs:**
- `reports/confirmatory_results.md`: the template of section 14 with every placeholder filled; nothing written by hand.
- `reports/confirmatory_results.json`: every number in the md, keyed by table and row.
- `reports/confirmatory/tables/R1.csv` … `R10.csv`.
- `data/processed/confirmatory/` (git-ignored):
  - `idata_<model>.nc` (ArviZ InferenceData for each Bayesian fit);
  - `permutation_null.csv` (2,000 rows of β* and t*);
  - `cv_predictions.parquet`;
  - `player_ratings.csv`;
  - `surface_S2s.csv`;
  - `forest_data.csv`;
  - `run_log.txt` (guards, hashes, versions, dropped columns, convergence diagnostics, timings).
- In simulate mode, the same files go to `data/processed/confirmatory_sim/<sim_seed>/`. Nothing is written to `reports/` in simulate mode.

**Implementation constraints:**
- Self-contained, apart from `bdb2027.paths` and `bdb2027.traits` (used for SA13), plus numpy, pandas/polars, scipy, statsmodels, pymc, arviz, nutpie, numba, h5netcdf and h5py.
- No step may need a C++ compiler. All Bayesian fits use nutpie (section 5.5), and posterior summaries (AME, PE, surface) are computed in numpy from the draws.
- Set the PyTensor flag `cxx=""` (for example `os.environ["PYTENSOR_FLAGS"] = "cxx="` before importing pymc) to silence the compiler warning. Behaviour does not change.
- Kaggle-compatible paths through `bdb2027.paths`.
- No interactive prompts.
- Every rule in sections 2-11 is implemented as written. Where the code and this document disagree, the document wins (section 13.4).

**Pre-freeze acceptance tests** (simulate mode only; results in `reports/confirmatory_script_tests.md`):

| Test | Content | Pass condition |
|---|---|---|
| **T1** | **Bayesian null calibration.** Who: the script author, on the feature-complete script, in simulate mode. When: after T2-T6 pass and before the coordinator computes `SCRIPT_SHA256`. What: **100 null datasets** (β_gap = 0; sim seeds 1-100; generator of section 13.3) on P's design; M1 fitted exactly as in confirmatory mode, except with the light sampler setting; GLM mirror on the same datasets | Record k = the number of datasets whose 95% interval for β_gap excludes 0, and the coverage. **k ≥ 10 → `CALIBRATION_CONTINGENCY: ACTIVE`** ("Supported" and "Opposite" then also require Q2, section 6.3); k ≤ 9 → INACTIVE. Also record the rejection rates of the GLM mirror (nominal and κ-calibrated) on the same datasets. Information only, no rule attached |
| **T1b** | **Permutation calibration.** The first 50 null datasets of T1 (seeds 1-50): studentized Freedman-Lane test with 199 permutations each (`default_rng(sim_seed)`) | Record the number with p < 0.05 in `PERMUTATION_CALIBRATION`. If it is ≥ 6 of 50 (P = 0.04 under nominal size), R2 and the writeup state that Q2 was anti-conservative in simulation. Q2's rule is unchanged |
| T2 | 5 datasets with β_gap = 0.25 (seeds 101-105) | Mean M1 estimate within 0.25 ± 0.08; intervals cover 0.25 in ≥ 4 of 5 |
| T3 | Same datasets: M2 `d_lpick` | Mean within −0.20 ± 0.08 |
| T4 | One full end-to-end simulate run | Every table is filled; no NaN except where a rule produces "not reported" (for example PE after a PC2 failure); runtime recorded |
| T5 | Sealed-file isolation | Instrument `load_sealed_outcomes` and the file-open calls; a simulate run never touches the sealed path. The sealed file itself is not moved, renamed or read |
| T6 | PC1 code path | On a synthetic table built to reproduce known coefficients, the PC1 function computes them correctly. It cannot be run on the real outcomes before freeze |

### 13.3b Readings fixed before the freeze (2026-11-07)

The script author listed the points where sections 2-14 leave a choice open. The readings below were adopted as part of this document (they are the specification; the code follows them). All were fixed on simulated outcomes only.

1. **When the H1 verdict is written.** Step 7 writes a provisional category (from the M1 interval alone) to the JSON. The final category, label, R3 and R11 are written at step 13, because the ACTIVE contingency needs Q2, which needs the permutation test of step 9. The category itself depends only on the M1 interval (and on Q2 if ACTIVE); nothing computed after step 7 changes it otherwise.
2. **Q1 and Q3 under Inconclusive.** Both are reported as "n/a" with their values shown (CI and ratio).
3. **Scope of the contingency.** The Q2 downgrade applies to H1 only. H2 and S0 use the plain interval rule (they have no permutation test).
4. **Pick-equivalent units.** For M0, M1 and M1-S* the pick equivalent uses the registered M2's `d_lpick` draws and P's SD of the log-pick difference; M2-A uses its own `d_lpick` draws and P-A's SD. Draw i of the gap model is paired with draw i of the pick model; if one chain set escalated, both are truncated to the shorter length.
5. **Rep-level std(·)** uses ddof = 1 after centring. The gap SD quoted in section 2.3 (1.2535) is the raw composite-difference SD.
6. **GLM fallback.** A fit counts as "full-setting not converged, GLM fallback" only when it is a full-setting model. In `--light` runs (simulate tests) it is flagged "not converged".
7. **Sampler interface.** All fits use `nutpie.compile_pymc_model` / `with_data` / `nutpie.sample` with the settings of section 5.5, not `pm.sample`.
8. **Discordance (Q4) comparisons** use posterior medians. SA8 (GLM only) is compared with M1's GLM estimate. SA16 is compared with M2's gap. SA12's `c_R` is compared with M1's gap (different scales; reported as such). SA18 has two priors, each its own row. For SA17 and SA18 the GLM column repeats M1's GLM.
9. **SA13 set** = E0 ∩ engaged ∩ both 5-frame composites non-null, with no requirement on the registered composites. The 5-frame builder reproduces the registered composite exactly at k = 3.
10. **SC4 weights** are truncated at percentiles taken over the in-P players of each side. The SC1 bootstrap resamples the in-P and out-of-P groups separately.
11. **R1** reports pre-drop counts (which match section 2.3); rows dropped for a null context value (4 in PL and ALL) are listed in a separate column.
12. **"slots64_97.5" and "AME_97.5"** (section 6.3) are the upper 97.5% quantiles of those draws.
13. **Output locations.** In a `--rerun-reason` run every output goes under `reports/confirmatory/run_NN/` (tables, md, json) and `data/processed/confirmatory/run_NN/`.
14. **Simulate generator.** Placebo and non-engaged rows carry no gap effect. Rows without a registered gap use gap = 0. S3a: Gaussian with random-effect SD 0.2, residual SD 0.9 and 0.3% nulls, rescaled to 0.25 + 0.20·z. S3b: an independent Bernoulli draw with the same linear predictor and random effects. Simulated pressures are not shared across a blocker's pairs within a play.
15. **Git HEAD** (guard 4) is recorded as "unavailable" if `git` cannot be run; the run does not abort.
16. **T4** is run with `--light`; a full-setting end-to-end run before the freeze is not required (the confirmatory run is the first full-setting run).

### 13.4 Deviations policy (after unsealing)

- **The frozen run's results are always reported.** If any later run differs, both are shown and the frozen one is named first.
- **Bug** = the code does not implement this document's text. Fix only the bug and record the diff, the reason and both results in `reports/deviations.md`. Rerun the whole pipeline with `--rerun-reason`. A bug fix may not change any specification.
- **Infeasibility** (for example a model that cannot be fitted): use the pre-specified fallback (section 5.5). Where none exists, record the deviation and label the replacement analysis exploratory.
- **New analyses**, including any done because of what the results show, are exploratory. They go in `reports/specification_log.md` and are labelled exploratory in the writeup.
- **The writeup states the H1 verdict category and label exactly as the frozen run emits them.** The skeptical-judge review checks every number in the text against `confirmatory_results.json`.

---

## 14. Results template

The script fills the `{…}` fields; it adds no other prose. Intervals are 95% unless stated otherwise. "Bayes" = posterior median [2.5%, 97.5%]; "GLM" = estimate [κ-calibrated 95% CI] {nominal t-reference 95% CI}.

### R0 Run manifest

| Item | Value |
|---|---|
| Script SHA-256 (computed / registered) | {sha_script} / {sha_registered} |
| preregistration.md SHA-256 | {sha_prereg} |
| Git HEAD | {git_head} |
| Input hashes match | {yes/no per file} |
| Versions | python {…}, pymc {…}, arviz {…}, pytensor {…}, statsmodels {…}, numpy {…}, pandas {…}, polars {…} |
| Start / end / CPUs | {…} |
| Status | {COMPLETE / STOP at PC1 / STOP at V0} |

### R1 Analysis sets

| Set | Reps | Pressures | Rate | Blockers | Rushers | Dyads | 2023 / 2024 / 2025 | REG | Rows dropped (reason) |
|---|---|---|---|---|---|---|---|---|---|
| P, PL, ALL, P-A, PL-A, P-B, P-DL, P-thr (4), SA5-SA7, SA9, SA13, SA15 | {…} | | | | | | | | |

Plus: dropped columns per model (column hygiene); gap SD; SD_lpd; SD of the raw pick difference.

### R2 Decisive checks

| Check | Expected | Observed | Status |
|---|---|---|---|
| V0 counts and join | Section 2.3 | {…} | {PASS/STOP} |
| PC1 events | 787 | {…} | |
| PC1 pick coefficient | −0.204 ± 0.003 | {…} (SE {…}) | {PASS/STOP} |
| PC1 dropback coefficient | 0.577 ± 0.003 | {…} | |
| PC2 M2 `d_lpick` | 95% interval < 0 | {med} [{lo}, {hi}] | {PASS/FAIL → no PE} |
| Convergence, per full-setting model | R-hat ≤ 1.01, ESS ≥ 400, divergences ≤ 0.1% | max R-hat {…}, min ESS bulk/tail {…}, divergences {…}, escalated {y/n} | {…} |
| Pre-freeze Bayesian calibration (copied from T1) | ≤ 9 of 100 null intervals exclude 0 | {k} of 100; coverage {…} | contingency {ACTIVE/INACTIVE} |
| Pre-freeze permutation calibration (copied from T1b) | ≤ 5 of 50 with p < 0.05 | {k} of 50 | {ok / anti-conservative in simulation} |

### R3 Primary result (H1, M1, registered composite, set P)

| Quantity | Value |
|---|---|
| β_gap, log-odds per SD of gap: Bayes | mean {…}, median {…} [{lo}, {hi}] |
| β_gap per composite-z unit | {…} [{…}] |
| P(β_gap > 0); P(β_gap < 0.10) | {…}; {…} |
| GLM mirror | {…}; κ-calibrated [{…}], p {…}; nominal [{…}], SE {…}, t df {…}, p {…} |
| AME, percentage points per rep (+1 SD gap) | {…} [{…}] |
| Extra pressures per 100 engaged reps | {…} [{…}] |
| Reps per extra pressure | {… or "not reported"} |
| Base-rate pp change (power-simulation convention) | {…} |
| Pick-difference SDs per gap SD (k) | {… or "not reported (PC2 failed)"} |
| Pick ratio exp(δ); slots at pick 64 | {…} [{…}]; {…} [{…}] |
| MDE (section 12), log-odds / pp / pick-difference SDs | {…} |
| **Verdict category** | **{Supported / Opposite / Inconclusive}** |
| Q1 GLM; Q2 permutation p; Q3 placebo ratio; Q4 discordant sensitivities; Q5 selection | {pass/fail, value} × 5 |
| **Final label** | **{…}** |

### R4 Information ladder and forest data

| Model | Term | Bayes median [95%] | GLM [95% CI] | Pick-equivalent k [95%] |
|---|---|---|---|---|
| M0, M1, M2 | gap | {…} | {…} | {…} |
| M1, M2 | every d_* and s_* term, f_* flags, d_lpick (M2), f_undr_* (M2) | {…} | {…} | |
| M1, M2 | σ_B, σ_R | {…} | | |
| M1-A, M2-A | gap | {…} | {…} | {…} |

### R5 Secondaries

| ID | Model | Estimand | Expected | Bayes median [95%] | P(expected direction) | GLM [95% CI] | n | Category (H2, S0 only) |
|---|---|---|---|---|---|---|---|---|
| H2 | M2 | gap | + | | | | | |
| M0 | M0 | gap | + | | | | | |
| S0 | M1-A / M2-A | gap | + | | | | | |
| S1 | M1-S1 | c_R; c_B; c_R + c_B | +; −; none | | | | | |
| S2 | M1-S2 | gap × edge; gap (interior); gap (edge) | +; ≥0; + | | | | | |
| S3a | M1-S3a | gap, pp of peak pressure probability | + | | | | | |
| S3b | M1-S3b | gap | + | | | | | |
| S5 | S5a / S5b | β_depth; β_depth; share | +; none; + | | | | | |

Footer line (fixed text): "Secondary results carry no confirmatory claim; with about 10 secondary intervals, about one in 20 would exclude 0 by chance if every effect were null."

### R6 Permutation and placebo

| Statistic | Value |
|---|---|
| Observed GLM β_gap (M1) | {…} |
| Null distribution: mean, SD, 2.5% / 97.5% | {…} |
| Permutation p, two-sided / one-sided | {…} / {…} |
| Placebo M1-PL β_gap: Bayes / GLM | {…} / {…} |
| ratio_gap (PL / P) | {…} → Q3 {pass/fail/not applicable} |
| Pick calibration: M2-PL β_lpd, ratio_pick | {…}, {…} (C3 reference ≈ 0.37) |

### R7 Out-of-sample

| Information set | Mean log loss | Mean Brier |
|---|---|---|
| I0-I4 | {…} | {…} |

| Contrast | Mean ΔLL (millinats per rep) | 2.5-97.5% over repetitions | Share of repetitions < 0 |
|---|---|---|---|
| I4 − I2 (tracking beyond club measures and pick) | {…} | {…} | {…} |
| I3 − I1 (tracking beyond pick and size) | {…} | {…} | {…} |
| I2 − I1 (stopwatch beyond pick and size, reference) | {…} | {…} | {…} |

Leave-one-class-out and leave-one-season-out tables: held-out unit, n test reps, LL(I2), LL(I4), ΔLL. By-season GLM β_gap with 95% CI and n.

### R8 Sensitivities

| ID | Description | Reps | Blockers / rushers | GLM β_gap [95% CI] | Bayes β_gap [95%] | Discordant? |
|---|---|---|---|---|---|---|
| SA1-SA18 | {…} | {…} | {…} | {…} | {…} | {yes/no} |

### R9 Selection

| Check | Result |
|---|---|
| SC1 composite, in-P vs out-of-P (OL, DL): mean difference [bootstrap CI], KS p | {…} |
| SC1 the 10 excluded blockers vs the 69: log pick, NGS, % missing forty | {…} |
| SC2 gap → engaged: GLM [95% CI] | {…} → {flagged/not} |
| SC3a all-pairs gap; SC3b gap, engaged, gap × engaged | {…} |
| SC4 IPW-weighted M1 gap | {…} |

### R10 Variance components and ratings

σ_B and σ_R for M1, M2 and R. In the md, the top 10 and bottom 10 blockers and rushers by model-R rating (nfl_id, reps, rating [90%]). The full table goes to CSV only.

### R11 Verdict sentence (exact templates; the script picks one and fills it)

- **Supported:** "On {n} engaged NFL pass-protection reps ({nB} blockers, {nR} rushers), each 1-SD increase in the Combine-tracked athletic gap (rusher minus blocker) raised the odds of a pressure by {β} log-odds [{lo}, {hi}], about {ame} percentage points per rep{, equivalent to {k} SDs of draft-pick difference}, beyond both players' size, stopwatch times and NGS athleticism score. Label: {label}."
- **Opposite:** "… the athletic gap went with *less* pressure: {β} [{lo}, {hi}] … Label: {label}."
- **Inconclusive:** "On {n} engaged reps, the athletic gap's effect beyond size, stopwatch and NGS athleticism was {β} [{lo}, {hi}] log-odds per SD. The data are compatible with no effect and rule out effects larger than {hi} (about {ame_hi} percentage points per rep{; {slots_hi} draft slots at pick 64}); the design's MDE was {mde}. P(effect < half the draft-pick effect) = {p_sesoi}."
- **Always appended:**
  - "With draft slot also controlled (pre-registered secondary): {H2 category}, {β2} [{lo2}, {hi2}]."
  - "With the 40-yard acceleration shape added to the composite (pre-registered secondary S0): {S0 category}, {βA} [{loA}, {hiA}]."
  - If any convergence fallback, PC2 failure or discordant sensitivity occurred: one sentence naming each.

---

## Appendix A. Changes from `candidates_v2.md` §3 and why

| # | candidates_v2 | This document | Why |
|---|---|---|---|
| 1 | Research question and primary model condition on draft slot | Primary M1 conditions on size, stopwatch and NGS athleticism; pick is in the key secondary M2 (H2); M0 added | Decision 2 (section 1.4): decision-time information set; pick is a descendant of the exposure (over-control and collider bias); pick barely changes precision |
| 2 | Player baselines entered only as rusher-minus-blocker differences | Measures enter as difference **and** sum (equivalent to side-specific coefficients); pick as difference only | The rusher composite D1 correlates −0.68 with rusher forty and −0.61 with rusher weight. If rusher and blocker measures have unequal effects (C3 showed unequal pick effects, −0.185 vs +0.109), a difference-only control leaves residual speed effects that load onto the gap. Pick stays a single difference because it is the yardstick and is nearly uncorrelated with the composites |
| 3 | log pick / "draft-pick equivalents = gap / pick coefficient" | Log-pick difference; equivalents expressed as pick-difference SDs, pick ratio and slots at pick 64; unit taken from M2 for both M1 and M2 | Log pick is the registered functional form (§3.3); the slot conversion keeps it football-readable |
| 4 | Positive control "pick reproduces about −0.20 in the final model; else stop" | Split: PC1 = exact reproduction of C3-G2 (decisive stop, before H1 is fitted); PC2 = M2 pick coefficient negative (governs only whether pick equivalents are reported) | With NGS, stopwatch, random effects and log pick, the M2 coefficient is not expected to equal −0.204, so "≈ −0.20 or stop" would be an ill-defined stop rule. The exact reproduction is a clean data-integrity test |
| 5 | Decision criterion: 95% interval excludes 0 | Kept, plus the three-category verdict, the SESOI (0.10) used only for wording, and qualifiers Q1-Q5 that change wording but not the verdict | Removes post-hoc freedom in describing a null or a fragile positive |
| 6 | Natural spline (3 df) for dropback; "down and yards-to-go bucket" | Harrell restricted cubic spline, 4 knots at 5/35/65/95%; down (1, 2, 3+) × distance (≤3, 4-7, ≥8) cells | Same as the power simulation. patsy `cr` misbehaves with one outlier rep (dropback up to 14.2 s) |
| 7 | Permutation: shuffle composites among players within position group | Freedman-Lane: permute composite residuals (after club measures) within side × draft class | Plain shuffling destroys the composite-control correlation and gives too narrow a null when the controls are correlated with the composite (r up to 0.68) |
| 8 | GLM mirror with two-way cluster SE | Same, with a t(G − 1) reference and a κ = 1.20 SE inflation (the κ version drives Q1); the permutation statistic is studentized; Bayesian null calibration on 100 simulations with a pre-specified contingency | The final power simulation shows that the cluster Wald test's type-I error is 0.118 (registered) and 0.104 (A), that the t reference barely helps (0.114), and that cluster SEs are 15-20% too small |
| 15 | Default PyMC sampler | nutpie (numba backend) through `pm.sample(nuts_sampler="nutpie", nuts={...})` | The environment has no C++ compiler, so PyTensor's C backend is unavailable |
| 16 | Official measures forty, ten-yard split, short shuttle (§3.3) | Three-cone added | O3's largest stopwatch correlate is the three-cone (\|r\| 0.32) |
| 9 | Sensitivities listed in §3.6 | Kept; "drop 40-derived traits" satisfied by construction; "drop pick" is now M1; "exclude non-DL rushers" becomes SA7 (exclude NFL-OLB-listed DL), because non-DL rushers are already excluded from the analysis set; added SA9 (one pair per play-blocker), SA11 (composite A on the common sample), SA12 (DL-only), SA13 (5-frame composites), SA14 (no dropback), SA15 (complete-case dash), SA16 (pick sum), SA17 (dyad random effect), SA18 (prior) | O3 smoothing fragility (SA12, SA13); mediator concern for dropback (SA14); imputation (SA15); repeated dyads and duplicated outcomes (SA9, SA17) |
| 10 | S0 did not exist | S0 = composite A, co-reported regardless of outcome | Decision 1 (section 1.3) |
| 11 | Out-of-sample validation across classes not specified | Added leave-one-class-out (V8) alongside leave-one-season-out | `PROMPT.md` §4 asks for validation across draft classes |
| 12 | Selection: "gap predicts being engaged; IPW on pick, NGS, class" | Specified exactly (SC1-SC4); `double_team` dropped from the engagement model | double_team is defined from other pairs' engagement, which is mechanically related to this pair's engagement |
| 13 | Analysis set "about 7,500-8,000 reps, 75-80 players per side" | 7,214 reps, 69 blockers, 97 rushers (the registered OL composite is missing for 10 blockers) | Computed, outcome-free |
| 14 | CV information sets (i)-(iv) | Kept as I1-I4 (I0 context-only added as a reference); tracking enters as gap + composite sum; 20 repetitions | Each side's composite gets its own coefficient for prediction, as the other measures do; repetitions reduce split noise |

## Changelog

- 2026-11-06: draft written (power and freeze manifest slots open).
- 2026-11-07 (freeze): manifest completed from the rerun tests on the amended script (T1 k = 6 of 100, no convergence failures; T1b 2 of 50); script and sealed-file hashes filled; h5py added to the dependencies.
- 2026-11-07 (pre-freeze, after the script author's tests T1-T6 on simulated outcomes; no outcome seen): the spline block is orthonormalised (section 5.2) and the sampler uses nutpie's low-rank modified mass matrix (section 5.5), because 46 of 100 null fits failed the R-hat rule on the three spline coefficients alone (db2/db3 correlation 0.995); the test results that follow this change supersede the first T1/T1b run (k = 6 of 100, 2 of 50), which was obtained with the diagonal sampler and the raw basis. Two more input hashes (combine files read by SA13) added to section 13.1. Readings of open points fixed in section 13.3b. h5netcdf added for the `.nc` outputs.
- 2026-11-06: section 12 filled from the final power simulation (500 simulations). MDEs registered as the size-adjusted values (0.247 registered, 0.234 A). GLM inference given a κ = 1.20 calibrated version that drives Q1. Permutation statistic studentized. Bayesian calibration rule fixed (T1: 100 null runs, ACTIVE at ≥ 10). Permutation calibration added (T1b). Sampler switched to nutpie (no C++ compiler). Package versions recorded. The power simulation's concrete design choices adopted, with the remaining differences listed in section 5.2.
