# Candidates v2: revised ranking and recommended design after feasibility

Inputs: `reports/feasibility_c1.md`, `feasibility_c2.md` and `feasibility_c3.md` (read in full), the crowding search, and `reports/candidates.md` (v1, unchanged).

Numbers marked **[q]** come from one light, outcome-free query I ran for this document: cross-rep reliability and stopwatch correlations of four speed traits. No NFL outcome was touched. These numbers are point estimates without CIs and must be re-verified by the trait-qualification job in section 3.2. The host post (Kaggle discussion 751165) describing the two PASS_RUSH_DROP reps was relayed second-hand; I have not read it myself.

---

## 0. What the feasibility results changed, and what v1 got wrong

**C1 is dead as a Combine-trait story.**
- The two PASS_RUSH_DROP reps are mirrored drops from different stances. They are not repeats. v1 called them "genuine test-retest", which was wrong.
- The set-phase metrics have about zero cross-rep consistency (r −0.05 to 0.02), so there is nothing on the drill side to transfer.
- The v1 expectation that tackles set deeper than guards and guards deeper than centres (T > G > C) was also wrong; the observed order is T > C > G.
- The in-game wrong-sign finding (deeper early retreat goes with more pressure, within players too) is real and interesting, but it has no Combine link. See option (b).

**C2 fails at the first link.**
- Drill bend reaches r 0.40 only after choosing the best of 30 definitions. Re-running that choice inside bootstrap resamples gives 0.22 on the left-out players.
- Drill get-off is not reliable (0.37) and does not transfer to in-game get-off (0.04 once EDGE/IDL is controlled).
- v1's turn window was ill-defined: the turn is an arc, and speed in it rises only from 4.0 to 5.4 yd/s.
- The angle is publicly occupied: "Does It Translate?" already defines centripetal bend and tests drill-to-game transfer.

**C3 passes cleanly, and nothing public resembles it.**
- It finds 8,271 engaged reps.
- Coherence: when the blocker is charged with a pressure, the rusher he was engaged with is credited with one 80% of the time, against 19% for co-occurring pairs that were not engaged.
- The draft-pick positive control works: −0.20 log-odds per SD of the pick difference.
- The pick effect is twice as large on engaged reps as on other co-occurring pairs. That supports the engagement definition.

**v1's "three-link chain" (does it translate) is itself public**, so it cannot be our differentiator. The differentiator has to be the rep-level, opponent-adjusted design.

**The quick trait check [q] shows the DL side is not empty.** Two tracking traits on each side clear the planned reliability and non-redundancy bars:

| Trait | Side | Cross-rep r | n | |r| vs stopwatch / size | Verdict |
|---|---|---|---|---|
| PASS_RUSH_DRILL whole-rep peak speed (side- and year-standardised) | DL | 0.64 (cross-side) | 106 | 0.73 vs forty, 0.65 vs weight | Reliable, partly redundant |
| PASS_RUSH_DROP whole-rep peak speed | OL | 0.50 (cross-side; feasibility report 0.55) | 111 | 0.43 vs forty, 0.11 vs weight | Reliable, non-redundant |
| 40 acceleration shape: time from 2.0 yd/s to 90% of own top speed | OL | 0.69 (true repeats) | 84 | 0.08 vs forty, 0.25 vs ten-yard split, 0.17 vs weight | Reliable, non-redundant |
| 40 acceleration shape (same definition) | DL | 0.60 (true repeats) | 84 | 0.30 vs forty, 0.24 vs ten-yard split, 0.25 vs weight | Reliable, non-redundant |
| 40 tracked top speed | all | 0.91-0.99 | | 0.91-0.98 vs official forty | Fails: pure stopwatch proxy |

The 40 acceleration shape is the most useful thing the check found. It is a sensor-only trait, measured on genuine same-condition repeats, and essentially uncorrelated with the stopwatch 40.

## 1. The options to weigh

**(a) C3 as the main entry: "the athletic gap decides the rep".**
- **Strengths:**
  - It is the only candidate with a validated outcome engine (coherence plus a working positive control).
  - It has a built-in placebo: co-occurring pairs that never engaged should show little or no trait effect.
  - It adjusts for opponents, which is the standard objection to any OL or DL outcome.
  - There is no public overlap.
- **The pass/fail gate is satisfied** by making the primary hypothesis a test of Combine-tracking traits, not of official measures.
- **The collapse risk** ("draft pick predicts pressure") is handled in three ways:
  - Pick, size and the official stopwatch times sit in the baseline.
  - Tracking effects are reported in draft-pick equivalents, so pick becomes the unit rather than the finding.
  - A two-way grouped cross-validation compares information sets: stopwatch-only, tracking-only and both.
- **Weakness: power.** Traits are player-level and there are about 75-80 players per side. The rough minimum detectable effect is a log-odds of about 0.16 per SD of the gap, comparable to the whole draft-pick effect (0.20). The most likely primary result is therefore a bounded estimate, "worth at most X draft slots", rather than a strong positive. The design makes such a result interpretable rather than ambiguous. **Ranked 1.**

**(b) The C1 wrong-sign finding as the story.**
- Deeper and faster early retreat goes with more pressure probability, between players (r up to +0.36) and within players (+0.04 per SD over 45k plays).
- The most likely reading is that the retreat depth reflects the rep (facing a speed rusher, a deeper drop, losing early) rather than a skill. C3 can test that: if the association shrinks once the engaged rusher's identity and traits are conditioned on, it is opponent-driven.
- That is useful to clubs: it warns against treating NFL set depth as a pass-pro skill.
- But it has no Combine-tracking link, so it cannot carry the entry. It also overlaps the public "Pass Protection Over Expected" notebook, which measures NFL pass sets.
- **Use:** an optional, pre-specified secondary inside (a), worth about 100 words. **Ranked 4 as a main entry.**

**(c) The reliability atlas.**
- Which Combine drill traits repeat, which are stopwatch duplicates, and which transfer to games, across every drill with two reps or repeated within-rep segments.
- It always produces a result, and it carries some contrarian findings:
  - The PASS_RUSH_DROP set phase does not repeat.
  - Drill bend reliability is about 0.2 once metric selection is accounted for.
  - The 40 hides a reliable acceleration shape that the stopwatch misses.
- But "Does It Translate? Combine Movement Signatures" covers much of this ground publicly, and the football value is lower: it tells clubs which numbers to trust, not what wins.
- **Use:** step 1 of (a), shown as one table, and the fallback if (a) cannot run. **Ranked 2, as the nested fallback.**

**(d) Anything else.**
- **The 40 acceleration shape as a standalone entry** ("two 4.50s are not the same"). It is clean, sensor-only and has true repeats. But as a standalone it hits the same player-level power wall against position-specific outcomes, and top-speed work from the 40 is the most common entry type. Its best use is as a component of (a), where it supplies the true-repeat backbone the skill drills lack.
- **A coverage version of C3** (WR vs DB engagement, with separation at pass forward as a continuous outcome). It would have more power per rep, but:
  - Man-coverage attribution is unvalidated.
  - The reliability of WR and DB drill traits is unknown.
  - It sits next to the public deceleration angle.
  - It would break the narrow focus.
  - Not for this entry. Possibly a one-line "the engine generalises" in the conclusion.
- **Revised C2 (in-game bend → pressure, with the drill as a weak predictor).** Crowded, the drill side is unreliable, and the EDGE-only mechanism is only r 0.22. **Ranked 3, not recommended.**
- **C4, C5, C6** stay where v1 put them or lower. C6's useful piece (acceleration shape) moves into (a).

## 2. Revised ranking

| Rank | Entry | Football (30) | Data science (30) | Originality | Viz (20) | Two-month risk | Most likely result |
|---|---|---|---|---|---|---|---|
| **1** | **(a) Athletic gap in the trench rep** (C3 engine + qualified tracking traits) | High: 1-on-1 trench matchups are how coaches think; opponent-adjusted | High: validated engine, placebo, positive control, pre-registration | High: nothing public | High: rep animation, matchup surface | Medium: power | Bounded estimate in pick-equivalents; components may show signal; strong secondary findings |
| 2 | (c) Reliability atlas + transfer (fallback, nested) | Medium | High | Low-medium (public overlap) | Medium | Low | Clear, mostly negative findings plus the acceleration shape |
| 3 | C2 revised (in-game bend; drill turn speed) | High | Low (drill r about 0.2 after selection correction) | Low (public) | High | Medium | Weak transfer |
| 4 | (b) "Giving ground" set-depth paradox | Medium | Medium | Medium | Medium | Low | Real, but fails the Combine-link gate on its own |
| 5 | C4 catch in stride | Medium | Low (YACOE noise) | Medium | Medium | Medium | Untested; likely noisy |
| 6 | C5 / C6 standalone | Medium / low | Low / medium | Low | Medium | Medium | Crowded or a null |

## 3. Recommended entry: "The athletic gap: do Combine-tracked movement traits decide NFL trench reps?"

### 3.1 Research question (one sentence)

On NFL pass-protection reps where a cohort blocker is engaged with a cohort rusher, does the difference between their Combine-tracked movement traits predict whether the rep ends in a pressure, beyond what both players' draft slot, size and stopwatch numbers already say?

### 3.2 Tracking-derived traits and the pre-specified rule for choosing them

**Rule, fixed now and applied without any outcome data:**
1. The candidate pool is closed. It is the list below, with definitions frozen before computation; no new traits are added after outcome data are seen.
2. **Reliability gate.** Cross-rep Pearson r ≥ 0.50, with the bootstrap 95% lower bound ≥ 0.30 (2,000 resamples, seed 2027).
   - Measured on true repeats where they exist, otherwise cross-side.
   - Year-standardise if a year mean drifts by more than 0.5 pooled SD.
   - Within-rep segment consistency (single-rep drills) must reach ≥ 0.60, because it overstates test-retest.
   - Any trait whose definition was chosen from a search uses its selection-corrected (out-of-bag) reliability.
3. **Non-redundancy gate.** Within position group, |r| < 0.75 with each of forty, ten-yard split, short shuttle, three-cone (where n ≥ 30), weight and arm length.
   - 0.75 was v1's pre-existing no-go line, set before any of these numbers were seen.
   - Partial redundancy is acceptable because the official measures sit in the baseline model, so only the non-stopwatch part of a trait can count.
4. **Coverage gate.** The trait exists for ≥ 80% of that side's players in the engaged-rep set.
5. **Side composite** = equal-weighted mean of the within-position, within-draft-year z-scores of every trait that passes, oriented so that higher = more athletic (faster, quicker).
   - No weighting and no picking the best: every passing trait enters.
   - A player needs at least one component.
   - Composite reliability is computed with Mosier's formula and reported.
6. **If one side has no passing trait**, the primary hypothesis becomes that side's composite alone. **If neither side has one**, switch to the fallback (section 4).

**Candidate pool:**

| ID | Side | Drill | Definition | Status |
|---|---|---|---|---|
| O1 | OL | PASS_RUSH_DROP | Whole-rep max of the 3-frame-smoothed speed, z within drift side × year, two-rep mean | [q] r 0.50, max \|r\| 0.43: expected to pass |
| O2 | OL | PASS_RUSH_DROP | open_and_run time (feasibility C1 definition) | r 0.34: expected to fail |
| O3 | OL | PASS_PRO-MIRROR_DRILL (one rep) | Median lateral reversal time: last frame with \|vy\| ≥ 1.0 yd/s in the old direction to the first frame with \|vy\| ≥ 1.0 in the new direction. Needs ≥ 4 reversals. Reliability = odd vs even reversals | Unknown; within-rep bar 0.60 |
| O4 | OL | FORTY_YARD_DASH | Time from smoothed s ≥ 2.0 yd/s to 0.9 × own top speed, mean of runs | [q] retest 0.69, \|r\| ≤ 0.25: expected to pass |
| O5 | OL | FORTY_YARD_DASH | Top speed | Fails: \|r\| 0.91 vs forty |
| D1 | DL | PASS_RUSH_DRILL | Whole-rep max smoothed speed, z within side × year, two-side mean | [q] r 0.64, \|r\| 0.73: expected to pass, near the redundancy line |
| D2 | DL | PASS_RUSH_DRILL | turn_min_speed (run reference, 15-60°) | Out-of-bag r 0.22: fails |
| D3 | DL | PASS_RUSH_DRILL | get_off, s 1.0 → 4.0 yd/s | r 0.37: fails |
| D4 | DL | FRONT_START_WAVE_DRILL_AND_LATERAL_REACTION (one rep) | Median lateral reversal time, as O3 | Unknown; within-rep bar 0.60 |
| D5 | DL | FORTY_YARD_DASH | Time from 2.0 yd/s to 0.9 × own top speed | [q] retest 0.60, \|r\| ≤ 0.30: expected to pass |
| D6 | DL | FORTY_YARD_DASH | Top speed | Fails: \|r\| 0.97 vs forty |

The most likely composites are therefore:
- OL = {drop peak speed, 40 acceleration shape} ± mirror reversal.
- DL = {rush-drill peak speed, 40 acceleration shape} ± wave reversal.

The 40 acceleration shape exists for about 80% of linemen (95/121 OL and 93/118 DL have a tracked 40), so it is listed first in the coverage check. The skill-drill speed traits cover about 100%.

**Why these are tracking traits the stopwatch cannot give:**
- The acceleration shape (how quickly a player approaches his own top speed) is near-orthogonal to the 40 and the ten-yard split [q].
- Peak speed inside a football-shaped drill is measured on every lineman, including the 17-20% who skipped the 40 and the 50-64% who skipped the agility tests.

**Qualification job checks:**
- The [q] reliability numbers, with bootstrap CIs and a 5-frame-smoothing sensitivity.
- Why the 40 acceleration metric is missing for some non-linemen: 246 of 375 pairs had values in my query, although the OL and DL pairs were complete.
- That no PASS_RUSH_DROP trait depends on the inferred phase semantics.

### 3.3 Analysis set and outcomes

**Unit and filters.**
- Unit: an engaged rep, using the C3 primary definition (distance ≤ 1.5 yd for ≥ 4 frames, from snap + 0.2 s to the earliest of snap + 3.0 s, `pass_forward` or `qb_sack`).
- Seasons: REG + POST.
- Blocker: `lined_up_position` T/G/C, with the PASS_RUSH_DROP drill.
- Rusher: combine_position DL, lined up at EDGE or INTERIOR_LINE.
- Both players must have a composite. The expected size is roughly 7,500-8,000 reps and about 75-80 players per side, to be confirmed when the dataset is built.

**Outcomes.**
- **Primary:** blocker `pressure_allowed` (binary: "rep lost"). It is the football event, and coherence shows it is attributable to the rep.
- **Key secondary:** `peak_pressure_probability_allowed` (continuous; more power).
- **Secondary:** rusher pressure (`time_to_pressure` non-null) on the same rep.

**Context covariates (rep level):**
- `dropback_duration` (natural spline, 3 df), down and yards-to-go bucket, shotgun / under centre, play-action flag.
- Season, blocker position (T/G/C), rusher alignment (EDGE / interior).
- Double-team flag (more than one cohort OL engaged with the rusher), and `pass_rushers_encountered`.

**Player-level baselines (both players):**
- log draft pick (undrafted = 262) plus an undrafted flag.
- Weight and arm length.
- Official forty, ten-yard split and short shuttle, each with a missing flag.
- `ngs_athleticism_score`.

### 3.4 Model

**Primary.** A Bayesian logistic mixed model with crossed random intercepts for blocker and rusher, fitted in PyMC (Apache-licensed and available on Kaggle).
- Fixed effects: context; both players' baselines entered as rusher-minus-blocker differences, plus each side's position terms; and the **athletic gap** = rusher composite − blocker composite (z units).
- Priors: Normal(0, 1) on standardised coefficients; half-Normal(1) on random-effect SDs.
- **Estimand:** the gap coefficient, in log-odds per SD of the gap, and in **draft-pick equivalents** = gap coefficient / pick-difference coefficient, with its posterior interval.
- **Decision criterion:** the 95% posterior interval for the gap coefficient excludes 0, in the expected direction (positive: a more athletic rusher relative to the blocker means more pressure).

**Frequentist mirror (robustness and permutation).** The same fixed effects in a logistic GLM with two-way cluster-robust SEs (blocker and rusher). This is the specification already shown to behave in C3-G2.

The random intercepts also yield **opponent-adjusted pass-pro and pass-rush ratings** for every engaged player, a by-product clubs can use.

### 3.5 Pre-registration and the single confirmatory run

Sequence (no step uses outcome data until step 5):
1. **Trait qualification** (section 3.2): composites frozen.
2. **Analysis-dataset build**: engaged reps, covariates, composites. Outcome columns are written to a separate file that is not opened yet.
3. **Power and minimum-detectable-effect simulation** on the real design matrix: simulate outcomes from the fitted context-only marginal rate (computed without traits), with a planted gap effect of 0.5× and 1.0× the C3 pick effect. Report the minimum detectable effect for the primary and the key secondary outcome.
4. **`reports/preregistration.md`**, written and frozen before step 5. It contains:
   - The hypotheses (primary H1 plus secondaries S1-S5).
   - The exact model formulas, priors, decision criterion and all sensitivity analyses.
   - The placebo expectations.
   - The SHA-256 of the analysis script.

   Commit it. After that, only the frozen script runs the confirmatory model.
5. **Confirmatory run, once.** Every later specification is labelled exploratory in the writeup, and the log of specifications tried is kept.

**Pre-specified secondaries (reported without confirmatory claims):**
- **S1:** side decomposition (blocker composite and rusher composite as separate terms).
- **S2:** gap × rusher alignment (EDGE vs interior): is speed decisive on the edge but not inside? This feeds the tackle-or-guard use.
- **S3:** the continuous outcome.
- **S4:** information-set comparison by out-of-sample log loss, under two-way grouped cross-validation:
  - Split blockers into 3 groups and rushers into 3 groups.
  - For each cell, train on reps in which neither player is in the held-out groups, and test on that cell.
  - Compare four models: (i) context + pick + size, (ii) + stopwatch, (iii) + tracking composites, (iv) + both.
- **S5 (optional, about 100 words):** the "giving ground" check.
  - On engaged reps, regress pressure on blocker backward depth at snap + 0.5 s.
  - Add rusher identity (random effect) and the rusher composite.
  - The share of the depth association that disappears measures how much of the C1 wrong-sign finding is opponent-driven.

### 3.6 Validation

- **Positive control.** The pick-difference coefficient must reproduce C3-G2 (about −0.20 per SD) inside the final model. If it does not, something is broken; stop.
- **Placebo 1 (built-in): non-engaged pairs.** Fit the same model to co-occurring pairs that never engaged. Pre-specified expectation: gap coefficient ≤ ½ of the engaged estimate. The C3 pick effect showed exactly this pattern.
- **Placebo 2 (permutation).** Shuffle composites among players within position group 2,000 times and refit the GLM mirror. The permutation p-value respects player-level clustering.
- **Out-of-sample.** S4's two-way grouped cross-validation, plus leave-one-season-out with the caveat that players overlap across seasons.
- **Sensitivity analyses** (all pre-listed):
  - The four alternative engagement thresholds from C3.
  - REG only.
  - Excluding double teams.
  - Excluding non-DL rushers.
  - Dropping the 40-derived traits (skill drills only, full coverage).
  - Dropping pick, to show the total association teams might already price in.
  - GLM vs mixed model.
  - Weighting each dyad equally, because the top 10 OL hold 31% of reps.
- **Selection.**
  - Compare composite distributions of players who do and do not appear in engaged reps.
  - Inverse-probability weights for appearing, modelled on pick, NGS score and class.
  - Test whether the gap predicts **being engaged**: faster rushers might slip past without contact and leave the engaged set. If it does, report the all-pairs model with an engaged interaction as the bound.
- **Interpretation of a null.** Report the minimum detectable effect from step 3 in the same pick-equivalent units, so "no detectable effect" reads as "worth less than about N draft slots per SD".

### 3.7 Figure and table plan (8 of the allowed 9)

1. **F1, finding the rep.** One real engaged rep: blocker and rusher paths from the snap on a field strip, with a distance-over-time inset and the 1.5 yd / 4-frame rule marked.
2. **F2, the engine is real.** Coherence (80% vs 19%) and the pick effect on engaged vs non-engaged pairs. Two small panels.
3. **F3, what the Combine measured.** The PASS_RUSH_DROP and PASS_RUSH_DRILL layouts with both reps coloured by speed and the peak-speed segment highlighted, plus two 40 speed curves with the same 40 time but different acceleration shapes.
4. **T1, which tracked traits are real.** Compact reliability atlas: trait, drill, n, cross-rep r [CI], selection-corrected r, max |r| vs stopwatch, pass/fail. It includes the negative findings: PASS_RUSH_DROP set phase about 0, drill bend about 0.2, get-off 0.37.
5. **F4, the main result.** Forest plot of rep-level effects (pick difference, weight, arm, stopwatch, tracking gap, and the S1 components), with a secondary axis in draft-pick equivalents and the minimum detectable effect band.
6. **F5, the matchup surface.** Predicted pressure probability over blocker composite × rusher composite for an average rep, faceted by EDGE vs interior (S2).
7. **F6, robustness.** Permutation null with the observed estimate, the non-engaged placebo estimate, and grouped cross-validation log-loss differences for the S4 information sets.
8. **T2, prospects and cases.** Players whose tracking composite disagreed most with draft slot, with their opponent-adjusted ratings from the random effects. Real names; 2025 class prominent.

The spare ninth slot is held for a figure the skeptical review asks for.

### 3.8 Actionable use for a club

- **Draft evaluation.**
  - A "Trench Athletic Profile" built from drills every lineman runs (no opt-out gap).
  - Calibrated in NFL reps against the actual opponents faced.
  - Expressed in draft-pick equivalents and as expected pressure-rate change against an average NFL opponent.
  - Clubs can see whether, and how much, drill-tracked athleticism should move a lineman on the board once size and stopwatch numbers are known.
  - If the estimate is bounded near zero, that is also actionable: stop paying for it.
- **Tackle-or-guard and edge-or-interior projection (S2).** If the gap matters on the edge but not inside, a lineman with a weak profile is a guard or interior projection, not a tackle or edge one.
- **Pro scouting and game planning.** Predicted pressure probability for a specific blocker against a specific rusher (where to slide protection or chip), plus opponent-adjusted pass-pro and pass-rush ratings for young players.
- **Measurement policy (T1).** Which Combine tracking readings deserve attention: the 40 acceleration shape and drill peak speeds. Which do not: the PASS_RUSH_DROP set phase, drill get-off and drill bend.

### 3.9 Main ways it could fail, and what the entry says then

1. **The primary is underpowered and comes out null** (most likely: perhaps 50-60%).
   - The entry then reads: "Once you know draft slot, size and the stopwatch, Combine-tracked athleticism is worth at most N draft slots per SD in NFL trench reps."
   - It still carries the positive control, the placebo, T1, and S1/S2.
   - This is a legitimate result, but it scores lower on football actionability than a positive. A positive S2 (edge vs interior) would rescue the football story.
2. **Trait qualification leaves one side empty** (about 15%): run the one-sided primary. **Both sides empty** (under 10%, given [q]): fallback.
3. **Engagement selection.** If faster rushers avoid engagement, the engaged-rep estimate is biased toward zero. Detected by the "gap predicts being engaged" check and bounded by the all-pairs model.
4. **2025 concentration.** 69% of engaged reps are from the 2025 season and the 2025 class is overrepresented. Report by season; the conclusions are about NFL-early-career reps.
5. **Attribution is partly mechanical.** Coherence shows real matchups, not causation. A pressure can come from elsewhere. The continuous outcome and the rusher-pressure secondary triangulate.
6. **Over-control by pick.** Pick partly reflects Combine performance, so conditioning on it can hide real value. The no-pick sensitivity shows the size of that effect.
7. **Explaining it in 2,000 words.** The rep-engagement idea must land in F1/F2 within the first 300 words. The writeup should be organised as: the rep, the traits, the gap, what it is worth.

### 3.10 Work plan (two months to January 6)

| Week | Task |
|---|---|
| 1 | Trait qualification and T1. Analysis-dataset build, outcomes sealed. Minimum-detectable-effect simulation. Pre-registration drafted and frozen |
| 2 | Single confirmatory run plus the pre-listed robustness suite (frozen script). Interpretation |
| 3-4 | Figures F1-F6 and T1-T2, case studies, opponent-adjusted ratings |
| 5-6 | Writeup and Kaggle notebook (paths configurable; PyMC fits on Kaggle within limits; checked by a runtime test) |
| 7 | Skeptical-judge review with fresh eyes and fixes |
| 8 | Buffer |

## 4. Fallback: "Which Combine tracking traits are real?" (nested in the recommendation)

**When to use it.** If trait qualification leaves both sides empty, or the confirmatory model cannot be fitted credibly.

**What it is.** The entry becomes T1 expanded into a position-by-drill reliability and redundancy atlas. It covers every drill with two reps or repeated within-rep segments:
- OL PASS_RUSH_DROP and mirror.
- DL PASS_RUSH_DRILL and wave.
- DB BACK_PEDAL_AND_TRANSITION_45 and LINE_DRILL.
- WR and TE GAUNTLET.
- The 40.

It reports:
- Selection-corrected reliability.
- Stopwatch redundancy.
- Drill-to-game kinematic transfer, where an in-game analogue exists (from C1/C2, already computed).
- The C3 engine as the outcome test for the few traits that qualify.

**What it costs.** It satisfies the pass/fail gate through the transfer tests and the C3 outcome test. It reuses roughly 70% of the work for (a). It is more crowded ("Does It Translate?") and has lower football value, but it is safe and contains three findings clubs would want:
- The PASS_RUSH_DROP reps are different drills.
- Drill bend and get-off do not repeat.
- The 40 hides a reliable acceleration shape the stopwatch misses.

## 5. Plain-language summary for the decision-maker

- We tested our two favourite ideas and both failed at the first step. The offensive-line drill's pass-set measurements do not repeat from one rep to the next, because the two reps are different drills. The edge-rusher "bend" measurement repeats only weakly.
- Both ideas also already have close public versions on Kaggle, so they would not stand out even if they had worked.
- The idea that passed every check is new: find the NFL plays where a lineman we have Combine data for actually blocked a pass rusher we have Combine data for. We found about 8,300 such reps. The check behaves as football says it should: better-drafted rushers win more often, and only when the two players actually met.
- The proposal is to ask whether the athletic gap between the two players, measured by the Combine sensors (how quickly each reaches top speed, and his speed inside his position drill), predicts who wins the rep, after allowing for draft slot, size and stopwatch times.
- Nothing public resembles this. It handles the judges' "football complexity" point directly, because it adjusts for the opponent, and it produces club tools: prospect profiles, matchup predictions and opponent-adjusted ratings.
- **The trade-off.** With about 80 players per side, the test can only detect an effect about as large as draft slot itself. The most likely headline is a careful "drill-measured athleticism is worth at most N draft slots", not a big discovery. A positive edge-vs-interior result would strengthen it.
- **The safer alternative** is a "which Combine tracking numbers are trustworthy" report. It is lower risk, but closer to existing public work and less useful to a club.
- **Decision needed:** approve the matchup entry, accepting that the main result may be a well-measured "small or none", or choose the safer report. Either way the first week's work (checking which sensor traits are reliable) is the same.
