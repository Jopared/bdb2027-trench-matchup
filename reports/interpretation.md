# Interpretation of the frozen confirmatory result

Date: 2026-11-07.
Inputs: `confirmatory_results.md/.json` (frozen run, R0-R11), `preregistration.md`, `trait_qualification.md`, `feasibility_c3.md`, `candidates_v2.md` §3.
Everything in this document beyond the frozen numbers is **exploratory**. The checks I ran are logged as entry E0 in `reports/specification_log.md`, with exact specifications. The proposed follow-up programme is entries X1-X5 in the same file.

**Frozen label (must appear verbatim in the writeup):** `Opposite (qualified: Q1); Q4 failed (discordant: SA12, SA13)`.

---

## Summary

1. **The robust result is a bound, not the sign.**
   - The hypothesised effect is ruled out: P(β_gap < 0.10) = 0.999.
   - The 97.5% upper bound is −0.005 (M1) and +0.025 (M2, pick controlled). In pick units the upper bound is 0.035 pick-difference SDs, about 3% of what draft slot is worth.
   - All 19 sensitivity rows (R8) have a 95% upper bound ≤ 0.125, and 15 of them ≤ 0.035.
   - Beyond size, stopwatch and NGS score, Combine-tracked drill athleticism gave linemen **no** edge in NFL pass-pro reps.
2. **The opposite sign is weak.**
   - It sits at p ≈ 0.04-0.05 by every calibrated route.
   - It drops inside the interval under a moderately skeptical prior: N(0, 0.2) gives [−0.272, +0.004].
   - At this power, an estimate that just clears the threshold is likely exaggerated about 1.4-2.6×.
3. **The opposite sign comes from one fragile measurement, and the effect does not carry beyond the engaged reps.**
   - S1 puts the effect entirely on the blocker composite, which is one mirror-drill rep. Its value is the median of about 4 reversals, quantised at 10 Hz: 35 of 69 blockers are tied at 0.50 s.
   - With 5-frame smoothing (r = 0.78 with the registered values) the blocker term falls from +0.143 to +0.061 (E0.4).
   - Across the same blockers' 46,000 pass-pro snaps it is +0.036 [−0.027, 0.098] (E0.7).
   - It does not predict in-game set depth (E0.11).
   - Composite A's "Opposite" (S0) sits on the **rusher** side, not the blocker side (E0.12), so S0 is not a replication of the same signal.
4. **Most likely explanation: chance acting on a coarse, single-rep trait.**
   - Collider selection and assignment confounding do not fit the numbers (§B).
   - The three-cone coefficient is **not** the same pattern. It is in the expected direction on both sides (§B5).
   - The "stopwatch adds 10.2 millinats" reading in the brief is inverted: the CV shows no player-level information, not even pick, improving held-out prediction (§A6).
5. **Writeup.** Lead with the engine and the positive control. Report the frozen label and immediately translate it into the robust bound. Give the surprise one honest "forensics" figure. Close on a measurement recommendation and a reusable validation tool. Takeaway in §D4.

---

## A. What the frozen result does and does not establish

### A1. Point estimate and its evidential weight

- M1 β_gap = −0.153 log-odds per SD of the gap, 95% CrI [−0.299, −0.005].
- In probability units this is −1.06 pp of pressure per rep [−2.02, −0.10] at a 9.4% base rate.
- Every calibrated route lands at the same evidential strength, about **p ≈ 0.04-0.05 two-sided**:

| Route | Evidence |
|---|---|
| Bayesian, N(0, 1) prior | P(β > 0) = 0.022 (one-sided), roughly two-sided 0.044 |
| GLM, κ-calibrated | p = 0.050 |
| Freedman-Lane, studentized | p = 0.0375 |
| Freedman-Lane, coefficient-based | p = 0.0535 |
| GLM, nominal | p = 0.0195 (known to be anti-conservative: simulated type-I 0.114) |

- The minimum Bayes factor at p = 0.0375 is 0.34. Starting from even odds, the posterior probability of a real effect is at most 0.75. Starting from skeptical odds, which are appropriate for a sign *opposite* to every football prior, it is well below 0.5.

### A2. Why the Bayesian and GLM criteria split

They do not really disagree. The estimates are −0.153 and −0.154. The scales differ by about 5%:

| Criterion | Scale | Half-width of the 95% interval |
|---|---|---|
| Bayesian | posterior SD ≈ 0.075, z 1.96 | 0.147 |
| GLM, κ-calibrated | SE 0.0644 × κ 1.20 = 0.0773, t(68) 1.995 | 0.154 |

- The estimate sits about 2.0 units from zero on either scale. One interval ends at −0.005, the other at 0.000.
- **The split is a rounding-level difference at a knife edge.** It is not a model discrepancy. The writeup should say: "both inferences put the estimate about two standard errors from zero; the registered Bayesian interval just excludes zero, the calibrated frequentist one just touches it."
- Calibration note: T1 found 6 of 100 null intervals excluding 0. That rate has a 95% CI of roughly 2-13%, so the Bayesian criterion is known not to be grossly anti-conservative, but it is not shown to be exactly nominal.

### A3. Prior sensitivity

- SA18 with Normal(0, 0.5) gives [−0.298, +0.005], which already changes the category.
- E0.13 (analytic, using a normal approximation to the likelihood):

| Prior on β | Posterior median | 95% interval |
|---|---|---|
| N(0, 0.2), the scale of the whole pick effect | −0.134 | [−0.272, 0.004] |
| N(0, 0.1), the SESOI scale | −0.098 | [−0.216, 0.020] |

- The registered N(0, 1) prior is very diffuse relative to plausible effects in this setting (the pick effect is about 0.17-0.20 per SD). The "Opposite" category therefore depends on that diffuseness.
- This is not a reason to override the frozen verdict. It is a reason to give it little weight.

### A4. Size of the effect relative to the MDE

- The MDE is 0.247. Power at |β| = 0.15 is about 0.43-0.49.
- The significance filter therefore inflates any estimate that clears the bar (E0.13):

| True effect | Power | Expected exaggeration of significant estimates |
|---|---|---|
| 0.15 | 0.49 | 1.4× |
| 0.10 | 0.25 | 2.0× |
| 0.075 | 0.16 | 2.6× |

- The honest reading of "−0.15, interval ends at −0.005": if anything is there, it is probably smaller than −0.15, and plausibly zero.
- **The bound is the solid part.** P(β < SESOI 0.10) = 0.999. H2's upper bound is +0.025 log-odds, about +0.19 pp per rep, 0.21 pick SDs.

### A5. Sensitivity discordance (Q4): what SA12 and SA13 each mean

- **SA12 (DL-only, rusher composite alone, −0.042 [−0.197, 0.125]).**
  - This discordance is *predicted* by S1: the rusher composite is −0.033 [−0.209, 0.160].
  - Remove the blocker term and nothing is left. SA12 is not separate evidence of fragility. It localises the gap effect to the blocker side.
  - In the writeup: "the gap result is carried by the blocker's mirror-drill trait."
- **SA13 (5-frame smoothing, −0.074 [−0.227, 0.083]).** This is the real robustness test, and it fails.
  - D1 is identical under k5 (player-level r = 1.000), so SA13 changes **only O3**.
  - O3 at k5 correlates only 0.78 with O3 at k3 across the 69 blockers.
  - In the side model the blocker term falls to +0.061 [−0.078, 0.200] (E0.4).
  - With both versions in one model, the k3-specific part carries the effect (+0.219) and the k5 version is −0.108.
  - So the effect lives in the component of a 10 Hz reversal timing that disappears with slightly more smoothing. `trait_qualification.md` flagged this before outcomes: O3 reliability is 0.70 at k3 but 0.57 at k5, which fails the gate.
- **Composite A / S0 is not a co-replication.**
  - S0's gap is −0.154 [−0.288, −0.022], but decomposed (E0.12) it is c_B +0.078 (n.s.) and c_R −0.134 [−0.240, −0.028].
  - The "Opposite" signal moved to the other side of the ball when D5 joined D1.
  - Two wrong-sign signals in different places are the signature of noise across several noisy traits, not of a mechanism. The writeup must still co-report S0 (decision 1, clause 2). It should not present S0 as corroboration.
- **Other dilution checks** (SA10 composite B −0.104, SA11 composite A on P's rows −0.134, SA14 no spline −0.099) all stay negative but cross zero. Anything that dilutes O3 weakens the result.

### A6. Two numbers in the brief that need correcting before they reach the writeup

1. **CV direction.** In `preregistration.md` §8 V7, "Δ < 0 means tracking improves prediction".
   - I2 − I1 = +10.2 millinats with share < 0 = 0.00 means adding stopwatch and NGS **worsened** held-out log loss in all 20 repetitions.
   - I0 (context only, 0.2781) beats I1 (0.2828), I2 (0.2930), I3 and I4. **No player-level information, including draft slot, improved out-of-sample prediction for unseen players.**
   - Rough arithmetic: a pick-sized effect (0.17/SD) is worth about 0.5·β²·p(1−p) ≈ 1.2 millinats per rep, while estimating 20-40 extra coefficients on about 3,200 training reps costs several millinats.
   - **S4 had essentially no power to detect anything.** "Tracking adds nothing beyond stopwatch + pick out of sample" is true but uninformative. It must not be presented as if the stopwatch passed and tracking failed.
   - The current F6 panel C is technically correct ("left = better"), but its "reference" row invites exactly the misreading in the brief.
2. **Three-cone (d_cone −0.181) is not "the same pattern".**
   - Measures enter as raw z of *times* (higher = slower). A negative d_cone means a slower-coning rusher relative to the blocker goes with less pressure. That is the **expected** direction.
   - Side by side (E0.3): rusher cone −0.225 (slower rusher, less pressure) and blocker cone +0.127 (slower blocker, more pressure). Both are as expected.
   - The official agility drill therefore behaves as football predicts, while O3, whose closest stopwatch correlate is the three-cone (r 0.32 to 0.36), does not. This argues *against* "athletic blockers truly allow more pressure".
   - Caveat: only 32 of 69 blockers and 37 of 97 rushers have a three-cone.
   - The current F4 labels these rows "3-cone difference", which a reader will take as same-direction-as-gap. Either orient them (higher = faster) or label the sign.

### A7. What is established, and what is not

**Established (confirmatory, H1 and H2 as registered):**
- Beyond size, stopwatch and NGS, the registered tracking gap does not have the hypothesised positive effect. It is excluded beyond about 0 log-odds, and beyond +0.025 with pick also controlled.
- The engine has the power to see a pick-sized effect: PC1 reproduced C3 exactly, PC2 gives −0.168 [−0.312, −0.031], and the pick placebo ratio is 0.48.

**Weakly suggested (registered label "Opposite", qualified):**
- The point estimate runs the wrong way at about p 0.04-0.05, it fails the calibrated GLM criterion, and it fails the smoothing check.

**Not established:**
- That athleticism hurts blockers.
- That the effect is a property of matchups (Q3 passed for the gap, but see B6).
- Any mechanism.

---

## B. Candidate explanations for a positive blocker-composite effect

Ranked from most to least plausible given the numbers. Each has its discriminating test (E0 = already looked at, X = proposed).

### B1 (most plausible). Chance, amplified by a coarse single-rep measurement

**For:**
- The boundary p-values (A1).
- The effect does not survive k5 smoothing (A5).
- O3 is quantised: 6 distinct values among in-P blockers. The effect is essentially a contrast between the 25 blockers whose median reversal is 4 to 4.5 frames and the 35 at 5 frames.
- On the 39,100 snaps where the same blockers did not engage a cohort DL, c_B is +0.018 [−0.045, 0.080]. The engaged-vs-not interaction is +0.052 [−0.028, 0.133], p 0.20, so pooling is justified, and the pooled all-snap estimate is +0.036 [−0.027, 0.098] (E0.7).
- No in-game movement correlate (E0.11).
- About 10 secondary intervals. The ones excluding 0 (S0 ×2, S1 c_B, S2 edge, S3b) are re-expressions of the same signal, not independent findings.
- The subgroups where the effect looks concentrated (interior linemen, later picks; E0.9, E0.10) are the pattern noise produces when sliced.

**Against:**
- It is not one outlier: the jackknife range is 0.106-0.200, winsorised +0.152, rank-normal +0.167.
- It is stable to team FE, rusher rating and score context.
- Blocker-level Spearman 0.28 (p 0.02) on engaged reps.
- These show the signal is spread across players. They do not address the multiplicity or the measurement fragility.

**Discriminating tests:** X2 (calibrated permutation p for c_B itself), X1 (blocker-season replication on all snaps), X3(a)(c) (quantisation and smoothing decomposition).

### B2. The trait measures something other than useful quickness

The k3-specific component could be:
- tracking jitter (sensor noise, a property of the chip and session, not the athlete);
- a choppy, over-reactive lateral style that shows up as a "fast" reversal at 3 frames;
- the pace of the coach the player mirrors. A mirror drill is reactive, so the leader's tempo enters every reversal, and odd/even reliability *within one rep* counts that shared tempo as "true score".

**Against the size story** (light or short-armed blockers):
- c_B correlates −0.01 with weight and +0.10 with arm.
- Nonlinear size terms leave it at +0.167 (E0.9).

**Against a football mechanism:**
- c_B does not predict giving ground: −0.02 SD in back displacement at 0.5 s (E0.11). That was the one in-game kinematic where a "quick-feet → oversets → loses inside" story would show.

**Discriminating tests:** X3 (quantised levels, reversal count, k3/k5, stopwatch/production correlates, in-game depth). A cheap qualitative check for the figures: overlay the mirror traces of two blockers at 0.40 and 0.50 s with frames marked.

### B3. Assignment confounding

**What the model already handles:** rusher identity (random intercept), T/G/C, EDGE/interior, double team, dropback, down × distance, shotgun, play action, season.

**What could be left:**
- protection scheme and help (chips, slides, being left on an island);
- QB tendencies beyond dropback time;
- game state;
- the adjacent blocker.

**Numbers:**
- c_B barely correlates with any observable assignment feature: rep-level |r| ≤ 0.13; blocker-level r 0.22 with mean c_R faced and 0.23 with double-team share.
- c_B is unmoved by defense-team FE (+0.151), blocker-team FE (+0.115), the opponent-adjusted rusher rating (+0.129) and score/WP/Q4 (+0.152).
- The "athletic tackle gets the island against the best rusher" story also predicts the effect would sit at **tackle**. It sits, if anywhere, at G/C (c_B×pos_T −0.230). That split does not replicate on all snaps (−0.033).
- Unobserved help schemes remain possible, but there is no observable footprint.

**Discriminating test:** X4(d)-(f).

### B4. Collider / Berkson selection into NFL reps

**Story:** teams play athletic-but-raw blockers, so among players who play, athleticism trades off against technique.

**Numbers:**
- For Berkson bias, selection must depend on the composite. It hardly does:
  - SC1 in-P vs out-of-P composite difference +0.285 [−0.129, 0.743];
  - r(composite, log pass-pro snaps) 0.05;
  - r(composite, log pick) −0.02;
  - SC4 IPW −0.178, no attenuation.
- Scale check: blocker quality SD is about 0.26 log-odds (σ_B). To produce +0.15 per SD of c_B, the selected sample would need corr(c_B, technique) ≈ −0.5. With selection-on-composite correlations of 0.05-0.15, that cannot arise.
- **One observation fits the story:** the c_B effect is larger for later picks (interaction +0.143 [0.042, 0.245], E0.10). Among late picks, the composite weakly predicts making P (r +0.14) and reps (+0.13), which is the right sign but too weak.

**Discriminating test:** X4(a)-(c), with the two-part rule. **Rank: low.**

### B5. Rookie timing

**Story:** reps come from rookie and second-year seasons, so raw athletes get exposed early.

**Numbers:**
- If anything the opposite: in engaged reps c_B is +0.046 as rookies and about +0.22 in season 2+ (interaction +0.177 [−0.046, 0.400]).
- On all snaps the interaction is +0.004, with season-index slopes +0.035 / −0.024 / +0.073 (E0.8).

**Discriminating test:** X1(e). **Rank: low.** Season, class and experience are partly confounded (2023 has 431 reps), so this test is weak either way.

### B6. Three-cone as "the same pattern in official measures"

Not supported (A6.2). The official agility measure is right-signed on both sides. NGS for blockers is +0.058 (n.s.). The wrong-sign pattern is specific to O3 (and, under composite A, to the rusher acceleration shape).

**A note on the placebo (Q3) for the blocker side:**
- The gap's placebo passed (ratio 0.275), partly because c_R and c_B have the same sign on non-engaged pairs and cancel in the difference.
- PL is contaminated for any blocker-side quantity: 2,882 of 17,795 PL rows share the (play, blocker) with an engaged rep and therefore carry the identical outcome. On those rows c_B is +0.268; on the 14,913 clean rows it is +0.054 (E0.6).
- The registered placebo design is fine for the gap but is not evidence that the blocker term is matchup-specific. A judge who reads S1 will ask. Say it in a limitations sentence.

### Ranking

| Rank | Explanation | Plausibility | Decisive test |
|---|---|---|---|
| 1 | Chance on a coarse, single-rep, smoothing-sensitive trait | High | X2 (calibrated p), X1 (season-level replication), X3 |
| 2 | Trait measures something else (jitter, leader tempo, style) | Moderate as the *carrier* of the noise; low as a football mechanism | X3 |
| 3 | Assignment confounding | Low (no observable footprint; wrong position) | X4(d)-(f) |
| 4 | Collider selection | Low (selection on composite is too weak; one supportive interaction) | X4(a)-(c) |
| 5 | Rookie timing | Low (pattern runs the other way) | X1(e) |
| — | Three-cone "same pattern" | Rejected (sign misread) | none needed |

---

## C. Exploratory programme

Five entries (X1-X5), written as specification-log entries with exact specs and reading rules, are in `reports/specification_log.md`. In brief:

| ID | What | Tests | Blind? |
|---|---|---|---|
| X1 | Blocker composite vs pressure allowed on **all** about 46k pass-pro snaps of the same blockers; with/without pick; engaged vs non-engaged plays; rookie interaction; k5 version; blocker-season O/E scatter | B1, B5; the brief's "player-level season pressure rate" request | Not blind (E0.7-8) |
| X2 | Freedman-Lane permutation for c_B and c_R separately in M1-S1 | B1 (calibrated p for the surprise itself) | Blind |
| X3 | Quantised O3 levels, reversal count, k3+k5 jointly, player-level correlates of O3, in-game set depth | B2 | Partly |
| X4 | c_B × pick and × exposure; selection model of in-P on composite by pick half; team FEs, rusher rating, game state; c_B × pos/edge; opponent correlations | B3, B4 | Not blind (E0.9-10) |
| X5 | **Rusher-side** player-level test on all pass-rush snaps: D1, composite A, D5 alone, with/without pick | The original hypothesis at higher power; resolves whether S0's rusher-side signal is real | Blind |

All are GLMs: no new Bayesian fits and a few minutes each. X2 is about 2,000 IRLS fits, under 5 minutes with `fast_logit_cluster`.

---

## D. Writeup framing

### D1. The story

**"We built an engine that sees who wins an NFL pass-pro rep, pre-registered one test of whether Combine tracking predicts it, and the expected edge was ruled out."**

That is a Data-science-30 story: pre-registration, a single frozen run, a positive control that worked, a calibrated null and honest forensics on a surprise. It becomes a Football-30 story through three things:
- what a club should and should not pay attention to;
- why: a 10 Hz single-rep drill metric is too coarse;
- a reusable rep-level validation tool that any club can point at its own Combine metrics.

Do not sell "athletic blockers allow more pressure". The judges will find SA13, and the entry would lose on correctness.

### D2. Structure (about 2,000 words)

1. **Motivation (≈150).** The Combine tracks every lineman's drills; does any of it predict NFL trench reps beyond what clubs already measure? A narrow focus (one matchup unit, two drills) per the host's advice.
2. **The rep engine (≈300; F1, F2).** Finding engaged reps between two cohort players: 7,214 reps, 69 blockers, 97 rushers. Coherence 80% vs 19%. The positive control: draft slot predicts who wins only when the players actually meet (PC1 exact; M2 d_lpick −0.168 [−0.312, −0.031]; placebo ratio 0.48).
3. **What the Combine measured (≈250; F3, T1).** The pool of 11 traits, the gates, and that only two survived. O3 is fragile under smoothing, which was declared before outcomes.
4. **The pre-registered test (≈400; F4).**
   - Estimand and decision rule in one sentence each.
   - State the label verbatim. Then the template sentence: "Contrary to the hypothesis: a more athletic rusher relative to the blocker went with less pressure", −0.153 [−0.299, −0.005].
   - In the **same paragraph**, the robust part: P(β < 0.10) = 0.999; with pick controlled (H2) Inconclusive, at most +0.025 log-odds (≈ +0.2 pp/rep). S0 Opposite, co-reported.
   - Then: "both inferences sit two standard errors from zero; the calibrated frequentist interval touches zero (Q1); 5-frame smoothing halves it (Q4)."
5. **Stress-testing the surprise (≈400; F5-new).** Labelled exploratory.
   - The signal is the blocker's mirror trait (S1).
   - It is a one-frame quantity from one rep.
   - It fades with smoothing.
   - It is absent over the same blockers' other 39k snaps.
   - It is unrelated to in-game set depth.
   - It is not explained by opponents, teams or selection.
   - Three-cone behaves as expected.
   - Verdict: "we find no support for 'athletic blockers allow pressure'; we find strong support for 'these tracked drill traits add nothing'." Add X1-X5 results as they come in.
6. **What clubs should do (≈350; F6, T2).**
   - (a) Don't move linemen on tracked drill quickness or speed once size, stopwatch and NGS are known.
   - (b) Measurement recommendation: single-rep reversal timing at 10 Hz is quantised at about 0.1 s against differences of about 0.05 s. It needs several mirror reps per player or a higher sampling rate before it can be a scouting number.
   - (c) The engine is the product: an opponent-adjusted, rep-level harness that any club can run on its own Combine metric. Show that it detects draft slot, and give the MDE so a club knows what it can and cannot detect (an effect about as large as draft slot's).
   - (d) Out of sample, single rep outcomes are noise-dominated: even pick does not improve held-out prediction. Players should be evaluated on aggregates, not reps.
7. **Limitations (≈150).**
   - Cohort-only opponents; 2025-heavy; early-career reps.
   - Attribution of pressure is NGS's.
   - The PL placebo shares plays for blocker-side quantities.
   - Every post-hoc analysis is exploratory and listed in the spec log.

### D3. Figures and tables (target 8, at most 9)

| Item | Decision | Change |
|---|---|---|
| F1 rep detection | **Keep** | none |
| F2 engine is real | **Keep** | The positive control is now the emotional anchor of the entry; title it that way ("Draft slot predicts who wins the rep — only when they meet") |
| F3 what the Combine measured | **Keep, small addition** | Add an inset or second row: one blocker's mirror trace with frame ticks showing a 0.40 s vs a 0.50 s reversal. This is the "10 Hz is coarse" point made visible, and it costs no figure slot |
| T1 trait atlas | **Keep** | Add the k5 column for O3 (0.70 → 0.57) so the fragility is visible before the result |
| F4 forest | **Keep, revise** | (1) **Add S0 rows (M1-A, M2-A) adjacent to H1/H2.** Decision 1 requires "same table and forest plot, adjacent to H1, regardless of outcome", and the current draft omits them. This is a pre-registration compliance issue. (2) Put the frozen label in the subtitle. (3) Shade the hypothesised region β ≥ 0.10 (SESOI) and annotate "P(β<0.10) = 0.999". (4) Orient the stopwatch rows (higher = faster) or say "rusher − blocker time; negative = expected". (5) Move c_R / c_B into a separate panel or below a rule labelled "secondary S1". (6) Reconsider the nonlinear draft-slot top axis: the slot conversion is unstable (slots64 interval −18,912 to +3). Replace it with a pick-difference-SD axis, or drop it and give the bound in pick SDs in the text |
| F5 matchup surface | **Replace** | The c_R × c_B surface would display the fragile blocker gradient as if it were a usable matchup map, and S2 is null. Replace with **F5 "Anatomy of the surprise"**: a forest of the blocker-side estimate under the frozen S1 (Bayes and GLM), then exploratory rows clearly separated (k5 smoothing; quantised-level contrast; all-snap X1(a); non-engaged snaps; X2 permutation p), with a column "frozen / exploratory". Optional small right panel: blocker-season O/E vs O3 level (X1) |
| F6 robustness | **Keep, revise panel C** | Panels A (permutation) and B (placebo) stay. Panel C: show I0-I4 as Δ vs **I0** (context only), so the reader sees every information set, pick included, is ≥ 0 (worse) out of sample, with a one-line caption: "single-rep outcomes are too noisy for out-of-sample gains at this sample size; the engine's evidence comes from the modelled effects (F2/F4), not prediction". Drop the "reference" wording on I2 − I1 |
| T2 prospects and cases | **Change** | A ranked prospect list on an invalidated composite would be the overclaim judges punish. Make T2 a compact "what to use" table: metric → evidence in NFL reps → recommendation (draft slot: predictive; size/stopwatch/NGS: no rep-level signal beyond pick; tracked mirror reversal: bounded ≤ 0, fragile; rush-drill peak speed: nothing beyond stopwatch). Alternatively, opponent-adjusted ratings (model R) for the 2025 class, with 90% intervals, as the club by-product. Choose one; the decision table is safer |
| Spare | Hold | For the skeptical review |

Total: F1, F2, F3, T1, F4, F5, F6, T2 = 8.

### D4. The one sentence for a scout

> **"Once you have a lineman's size, stopwatch times and NGS score, his sensor-tracked drill numbers — mirror-drill quickness and rush-drill speed — should not move him on your board: across 7,214 NFL pass-pro reps they added no edge (draft slot did), and the only signal we found ran the wrong way and fell apart when we looked closely."**

Shorter version for the abstract: *"Tracked drill quickness didn't win NFL pass-pro reps — draft slot did."*

### D5. Phrasing rules for the writeup

- Use the frozen label verbatim once, in §4. Elsewhere say "the registered verdict".
- Secondary and exploratory results take "consistent with" / "suggests", never "shows".
- Never write "athletic blockers allow more pressure" as a finding. Write: "the blocker's mirror-drill trait went with slightly more pressure on engaged reps; this did not survive smoothing or extend to the same blockers' other snaps (exploratory)".
- Do not call S0 a replication (its signal is on the other side).
- Report the MDE (0.247; about 1.2 pick SDs) with the bound, so "nothing" reads as "nothing as large as half of draft slot".
- Every number checked against `confirmatory_results.json` (frozen) or the X-entry outputs (exploratory), labelled as such.

---

## Exploratory checks behind this document

All numbers marked E0.x above come from GLMs I ran in scratch scripts. They used the frozen script's own builders, imported read-only, and the reproduction matched R3/R5 exactly. The full specifications and results are in `reports/specification_log.md`, entry E0. None of them may be cited in the writeup without being re-run by the formal X-entries, or logged and labelled exploratory as they stand.
