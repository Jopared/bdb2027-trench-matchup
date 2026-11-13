# Skeptical judge review: `writeup/writeup.md` (pre-submission)

Reviewer stance: a Big Data Bowl 2027 judge who wants to mark this entry down. Read in this order: the writeup and its six PNGs, the notebook and its README (executed copy), the result files (every number checked against them, not against `numbers_appendix.md`), and only then `preregistration.md` and `interpretation.md`. No file other than this one was modified. Git was used read-only (`git log`, `git show`, `git diff`, `git ls-files`).

---

## 1. Provisional score: 66 / 100

| Criterion | Score | One-line justification |
|---|---|---|
| Football (30) | **17** | A well-bounded "these two tracked traits add nothing to size, stopwatch and NGS" is a real, correct finding, and the measurement recommendation is useful. But the title over-generalises from 2 traits to "tracked Combine drills". The "athletic gap" (rusher arc-drill speed minus blocker mirror quickness) is never justified as a football quantity. The scout takeaway ("draft slot predicts") is something every scout already knows. The text is written in model codes (c_B, S0, SA13, Q1) that a line coach cannot read. |
| Data science (30) | **23** | The pre-registration discipline, a single frozen run, honest labelling of the headline and a positive control are rare and excellent. Points are lost for: a post-hoc one-sided p-value; an F6A panel whose p-value contradicts the plotted statistic; a weaker standard applied to draft slot than to the gap; omission of exploratory results that cut against the "coarse trait" story; the contaminated placebo not disclosed; one factual error about seasons; and a frozen-script hash that will not match on a clean Linux clone. |
| Writeup (20) | **13** | Inside the limits (1,812 words; 8 figures and tables) and logically ordered. But the frozen label is quoted without defining its codes, permutation p-values are juxtaposed confusingly, captions repeat numbers instead of telling the reader what to see, and the language is too dense for a football reader. |
| Visualisation (20) | **13** | F1, F2 and F3 are strong and stand alone. F4 mixes two sign conventions on one axis and shades the gap's MDE band across every row. F6A plots coefficients but prints a studentized p (the observed line sits inside the null's 2.5% tail yet is labelled p = 0.037). F6C is a panel the caption itself calls uninformative. F5 is dense, and its caption duplicates every number in the figure. |

## 2. Gates

| Gate | Verdict | Evidence / condition |
|---|---|---|
| Explicit, demonstrated link from Combine tracking data to NFL performance | **PASS (with risk)** | The two tracked traits (O3, D1) are linked to NFL pass-pro pressure in a pre-registered model with a bound. The risk is that a null/opposite result is read as "no link". The opening paragraph should state the link as the deliverable: tracked trait → engaged rep → pressure, bounded at < 0.10 log-odds per SD. |
| Markdown writeup with visuals | **PASS** | `writeup.md` with 6 PNGs. Note: the image paths are relative (`../figures/...`). On Kaggle the images must be uploaded and re-linked, or they will not render. |
| Public notebook | **NOT YET MET** | The notebook exists and runs locally: `executed_local.ipynb` ends "54 of 54 assertions passed". But `REPO_URL = "https://github.com/OWNER/REPO.git"  # TODO`, the repository has **no git remote**, and nothing is published. See also defect 2 (hash/CRLF): on a clean Linux or Kaggle clone the registered script hash will not match. |
| ≤ 2,000 words | **PASS** | My count: **1,812** words, counting whitespace tokens that contain a letter or digit, over the whole file (headings, body, captions, table cells and the reference line), with image lines removed. Body without tables: 1,579. Body without tables or captions: 1,191. Raw `split()` over the whole file (pipes, `---`, image markup included): 1,954. The margin is thin if the counter is naive, so any additions in revision must be offset. |
| < 10 figures + tables | **PASS** | 6 images (F1-F6) + 2 markdown tables (T1, T2) = **8**. |
| Data not redistributed (CC BY-NC 4.0) | **PASS (check before publishing)** | The only tracked data-like files are 5 derived aggregate CSVs in `notebooks/frozen_products/`. `*.csv` is git-ignored, so `figures/F3_combine_measured.csv` (raw per-frame x/y) and `figures/F1_engaged_rep.csv` are not committed. Before making the repository public, check that `reports/audit_*.md` (4,400 lines) contain no row-level extracts. |
| Code licence OSI | **PASS** | `LICENSE` is MIT. The README states the licence. Add one line to the notebook's first cell and set the Kaggle notebook licence. |

---

## 3. Defects, ordered by severity

### Critical (fix before submission)

**1. The public notebook is not public, and it cannot run as published.** (Notebook cell 1; `notebooks/README.md` "Run on Kaggle"; writeup §6 and the references line.)
- Wrong: `REPO_URL` is a TODO placeholder, there is no remote, and the writeup cites "the public notebook repository" with no URL. This fails a hard gate.
- Fix:
  - Push the repository.
  - Fill `REPO_URL`, and set `REPO_REF = "prereg-frozen"` or a release tag.
  - Publish the Kaggle notebook and run it there once (not only locally).
  - Replace the references line with: "*Code, pre-registration (tag `prereg-frozen`), frozen results and specification log: <URL>; Kaggle notebook: <URL>. Data: Big Data Bowl 2027 (CC BY-NC 4.0), not redistributed.*"

**2. The registered script hash only matches a Windows CRLF checkout.** (Pre-registration §13.1; README "What is loaded"; notebook step 8.)
- Wrong:
  - `SCRIPT_SHA256 8d842b70…` is the hash of the CRLF working copy. `git ls-files --eol` shows `i/lf w/crlf`, and `core.autocrlf=true`.
  - The committed blob at `prereg-frozen` hashes to **`4b3d06a4…`** (verified: `git show prereg-frozen:scripts/confirmatory_analysis.py | sha256sum`). The same applies to `src/bdb2027/traits.py`: the registered hash is `2965e188…`, the committed blob is `d65191d2…`.
  - On Kaggle or Linux, the notebook will print "frozen script hash matches the manifest: False", and `confirmatory_analysis.py --mode confirmatory` will refuse to run. A judge who checks your pre-registration claim will conclude that the frozen script was altered.
  - The underlying claim is true: `git diff prereg-frozen HEAD -- scripts/confirmatory_analysis.py reports/preregistration.md` is empty, and the CRLF-converted blob reproduces `8d842b70…` exactly.
- Fix: do not edit the frozen files. Add a `.gitattributes` with `scripts/confirmatory_analysis.py text eol=crlf` and `src/bdb2027/traits.py text eol=crlf`, so every checkout reproduces the registered bytes (this does not change the committed blobs). Also add a README sentence:
  > "The registered SHA-256 values were computed on a CRLF (Windows) checkout; the LF blob of the same commit hashes to 4b3d06a4… (script) and d65191d2… (traits.py). `.gitattributes` forces CRLF so the guard passes on any OS."
- In the notebook, assert on the CRLF-normalised hash rather than printing a bare False.

### Major (statistical honesty / correctness)

**3. Post-hoc one-sided p-value.** (§4, first bullet: "the blocker term's calibrated p is 0.065 (two-sided; 0.0375 one-sided)".)
- Wrong: 0.0375 is the one-sided p **in the observed direction** (`x2_permutation_summary.csv`, column `p_one_same_direction`). The pre-registered direction for c_B was **negative** (S1: β_B < 0), so a one-sided p in the post-hoc direction has no meaning. It also coincides numerically with the gap's two-sided p (0.0375, §3), and readers will conflate the two.
- Fix: "**Permutation:** the blocker term's calibrated two-sided p is 0.065 (coefficient-based 0.100): not distinguishable from permutation noise."

**4. The gap's permutation p is listed as a weakness, and is not labelled.** (§3: "The opposite sign is weak: the calibrated frequentist interval touches zero ([-0.308, 0.000]), the permutation p is 0.0375, and …")
- Wrong:
  - p = 0.0375 is the registered Q2 test, and it **passed** (two-sided studentized, R3/R6). Placed in a list of weaknesses, it reads as if it were one.
  - The coefficient-based p is 0.0535, and the GLM κ p is 0.0502. Omitting both hides that every calibrated route lands at about 0.04-0.05.
  - The reader is never told that 12 of 18 Bayesian sensitivity fits put 0 inside the interval: SA2, SA5, SA7, SA10, SA11, SA12, SA13, SA14, SA15, SA16, SA17, SA18_0.5. The R8 count is 13 of 19 if GLM-only SA8 is included.
  - The registered prior sensitivity N(0, 0.5) gives [-0.298, +0.005].
- Fix (replace the sentence):
  > "The opposite sign is weak. Every calibrated route puts it about two standard errors from zero (registered permutation test p = 0.0375 two-sided, which passes; coefficient-based 0.054; calibrated frequentist interval [-0.308, 0.000], which touches zero). Twelve of the 18 pre-registered Bayesian sensitivity fits, including a tighter N(0, 0.5) prior, put zero inside the interval. Two met the registered discordance rule: 5-frame smoothing (-0.074 [-0.227, 0.083]) and the rusher-only version (-0.042 [-0.197, 0.125]). The bound survives all of them: every sensitivity's upper limit is at most 0.125."

**5. Draft slot is held to a weaker standard than the gap.** (§1 "It does."; T2 row "Draft slot … predictive"; F2B.)
- Wrong: the writeup discounts the gap because its calibrated GLM interval touches zero. The M2 draft-pick coefficient's calibrated GLM interval also includes zero: -0.138 [-0.280, 0.004] (R4, M2 `d_lpick`). The strong evidence for draft slot is PC1 (-0.204, SE 0.049, all 8,271 engaged reps; R2), which the writeup never cites.
- Fix, §1:
  > "Positive control: draft slot should predict who wins. It does: the pre-registered reproduction gives -0.204 log-odds per SD of the pick difference (SE 0.049, 8,271 engaged reps), and in the full model -0.168 [-0.312, -0.031] (Bayes; calibrated GLM -0.138 [-0.280, 0.004])."
- Fix, T2 verdict for draft slot: "predictive (PC1 -0.204, SE 0.049)".

**6. The non-engaged "half" (ratio 0.48) is presented as support for the engine.** (§1 "about half that on non-engaged pairs (ratio 0.48; F2B)"; F2 caption "The engine is real"; F2B subtitle "The draft-pick effect is clearest on engaged reps".)
- Wrong:
  - The two estimates (-0.168 vs -0.080) were not tested against each other, and their intervals overlap almost entirely.
  - The pre-registration expected about 0.37 (§8 V6); the observed 0.48 is close to the 0.5 placebo threshold.
  - The outcome is the blocker's play-level pressure charge, so **2,882 of 17,795 non-engaged pairs (16%) carry the identical outcome of an engaged rep on the same play** (E0.6; `interpretation.md` B6 says this must go in the limitations). Part of any "placebo" effect is therefore mechanical.
  - The evidence that the engine finds real matchups is F2A (79.7% vs 19.3%), not F2B.
- Fix, §1: replace "and about half that on non-engaged pairs (ratio 0.48; F2B)" with:
  > "On non-engaged pairs the pick effect is smaller (-0.080 [-0.179, 0.016]; F2B), though the two estimates are not statistically distinguishable."
- Fix, F2B subtitle: "Draft-pick effect on engaged reps and on non-engaged pairs".
- Fix, limitations: add "a blocker's pressure is shared by all his pairs on a play, so 16% of non-engaged 'placebo' pairs share an engaged rep's outcome."

**7. Exploratory results that contradict the narrative were dropped.** (§4 "We read it as consistent with chance acting on a coarse trait"; §5 measurement recommendation; F5.)
- Wrong: `numbers_appendix.md` line 66 says "Fast/slow reversal groups: removed from the writeup".
  - X3(a) is the one test of the "one-frame coarseness" reading. It showed a **monotone** pattern: fast (≤ 0.45 s) +0.214 [-0.014, 0.442], slow (≥ 0.55 s) -0.215 [-0.596, 0.166]. Its mechanical reading was that "carried by a one-frame difference" is **not triggered**.
  - X4(a) found the blocker effect larger for later picks: +0.136 [0.041, 0.231], with a κ-CI that also excludes 0.
  - X4(e): the blocker effect is concentrated in guards and centres (c_B × tackle -0.257 [-0.461, -0.052]).
  - Dropping the one result that cuts against your preferred explanation, after seeing it, is exactly what a judge reading the spec log will find. The "coarse trait" explanation is post hoc, and the text does not say so.
- Fix: add one bullet to §4.
  > "**Not a one-frame artefact:** grouped by reversal time, fast-reversing blockers (≤ 0.45 s) went with more pressure (+0.214 [-0.014, 0.442]) and slow ones with less (-0.215 [-0.596, 0.166]), a graded pattern; the effect was also larger for later-drafted blockers (+0.136 [0.041, 0.231]). We have no football explanation and do not offer one."
- Change "We read it as consistent with chance acting on a coarse trait" to:
  > "Our post-hoc reading, which these checks support but cannot establish, is chance acting on a fragile single-rep trait."

**8. Factual error about seasons.** (§6 Limits: "rookie and second-year reps only".)
- Wrong: set P includes **1,823 reps (25%) from blockers' third NFL season**. Season minus draft year: 0 → 2,804, 1 → 2,587, 2 → 1,823. Verified by tabulating P; it matches E0.8.
- Fix: "reps from players' first three NFL seasons (blockers: 2,804 rookie, 2,587 second-year, 1,823 third-year reps)".

**9. Sign conventions are a trap for the reader.** (F4, T2, §4 S1 sentence.)
- Wrong:
  - In F4 and T2, the tracked gap and composites are oriented "higher = more athletic", while the official times are raw "higher = slower".
  - So in F4, "Tracking gap -0.15" means the *more athletic* rusher did worse, while "40-yard -0.04" means the *faster* rusher did better. They sit on one axis with the same colour.
  - "Blocker composite +0.156" is never translated. A reader who knows O3 is a time (lower = faster) and has been told "times are raw" will read +0.156 as "slow-reversing blockers allowed more pressure", which is the *expected* direction and the opposite of what it means.
  - T2 flags only the 3-cone as "raw time". The shuttle (+0.134) is also a raw time and points the *unexpected* way, without comment.
- Fix (preferred): re-orient all official time rows in F4 and T2 as "rusher faster by 1 SD", flipping their sign, so that every row reads "positive = the more athletic rusher wins more". Then 3-cone becomes +0.181 and shuttle -0.134. Change the F4 caption to:
  > "All rows are per SD and oriented so that positive means the more athletic (or better-drafted) rusher, relative to the blocker, won more reps."
- Fix (minimum): add a T2 column "Direction" with entries such as:
  - "+0.156: blockers with *quicker* mirror reversals allowed *more* pressure (opposite of expected)";
  - "3-cone: slower-coning rusher, less pressure (expected)";
  - "shuttle: slower-shuttle rusher, more pressure (unexpected)".
- In §4 write: "The frozen split (S1) puts the signal on the blocker side: blockers with quicker mirror reversals allowed slightly more pressure, +0.156 [0.020, 0.301] (secondary; expected sign negative)."

**10. The 3-cone row is cherry-picked.** (§4 "The official 3-cone behaves as football predicts…"; T2 "expected direction; thin n".)
- Wrong:
  - d_cone is one of 16 covariate coefficients in M1 and not a registered secondary.
  - Its calibrated GLM interval includes zero: -0.180 [-0.362, 0.003].
  - Only 32 of 69 blockers and 37 of 97 rushers have a 3-cone (verified).
  - The shuttle, another agility time, points the wrong way (+0.134 [-0.052, 0.320]), and the 40 and 10-yard split are flat. Selecting the one covariate that "behaves" is the same error the entry criticises.
- Fix: delete the 3-cone sentence from §4 (it saves 35 words). In T2, change the verdict to "nothing reliable (frequentist interval includes 0; 32 blockers, 37 rushers)". If it is kept anywhere, report the shuttle next to it.

**11. "Before touching any outcome" is literally false.** (§2 "We closed the candidate pool before touching any outcome"; pre-registration paragraph "frozen and hashed before the outcomes were opened".)
- Wrong: pre-registration §0 discloses that pressure outcomes on the same 8,271 engaged reps had been modelled against draft pick and weight, and the 79.7% coherence had been seen, before the freeze. What was never done before the freeze was relating any *tracked trait* to an outcome. A judge who reads §0 will catch the overstatement.
- Fix, §2: "We closed the candidate pool before any tracked trait was related to any NFL outcome."
- Fix, pre-registration paragraph: "…frozen and hashed before the sealed outcome file was opened; the only outcome results seen earlier were the feasibility checks of draft pick and weight (disclosed in the pre-registration)."

**12. The S0 wording hides the sample change and the second model; the "rusher side" claim is half-reported.** (§3 S0 sentence; §4 "Composite A's signal (S0) sits on the rusher side, so it is not a second look at the same signal.")
- Wrong:
  - S0 is fitted on a different set: P-A, 7,720 reps, 75 blockers.
  - On P's own rows (SA11) it is -0.131 [-0.278, 0.022], which includes 0.
  - The second S0 model (M2-A, -0.149 [-0.285, -0.009]) is omitted.
  - Composite A *contains* O3, so "not a second look at the same signal" is confusing.
  - The rusher-side decomposition (E0.12: c_R -0.134 [-0.240, -0.028]) is an unreplicated scratch GLM. The formal X5(c) test of composite A on the same rushers' 19,672 snaps found nothing (-0.003 [-0.135, 0.129]).
- Fix, §3:
  > "With the 40 acceleration shape added to both composites (S0, pre-registered; 7,720 reps, 75 blockers) it is also Opposite: -0.154 [-0.288, -0.022], and -0.149 [-0.285, -0.009] with draft slot; on the primary set's own rows it is -0.131 [-0.278, 0.022]."
- Fix, §4:
  > "S0 does not corroborate the blocker-side signal: split by side (exploratory), its gap sits mostly on the rusher (-0.134 [-0.240, -0.028]), and on those rushers' full pass-rush snaps composite A predicts nothing (-0.003 [-0.135, 0.129])."

**13. F6A's p-value contradicts the plotted statistic.** (F6, panel A.)
- Wrong:
  - The histogram is of the *coefficient* β*, with its null 2.5-97.5% range printed as [-0.16, 0.14]. The observed -0.154 visibly sits inside the lower 2.5% bin, yet the label says "two-sided p = 0.037 (studentized)".
  - The studentized p belongs to t* (t_obs = -2.393). The coefficient-based p for the plotted statistic is 0.0535 (R6). A reader sees a figure that says "not significant" and a label that says "significant".
- Fix: plot t* (from `permutation_null.csv`) with t_obs = -2.39 and keep p = 0.037. Or keep β* and label it "coefficient-based two-sided p = 0.054; studentized (registered) p = 0.037".

**14. Undefined label codes.** (§3, the frozen label.)
- Wrong: "Opposite (qualified: Q1); Q4 failed (discordant: SA12, SA13)" is quoted (correctly, verbatim) but Q1, Q4, SA12 and SA13 are never defined at that point. The decision rule ("Opposite if the 95% interval lies below 0") is never stated anywhere.
- Fix: keep the label verbatim and add the gloss:
  > "(Opposite: the registered 95% interval lies entirely below zero. Q1: the calibrated frequentist check did not agree. Q4: two registered sensitivity checks, SA12 rusher-only and SA13 5-frame smoothing, disagreed.)"
- State the decision rule in the pre-registration paragraph:
  > "H1 is Supported if the 95% posterior interval lies above zero, Opposite if below, otherwise Inconclusive."

### Moderate

**15. The title and scope over-generalise.** (Title; §5 "the tracked drill numbers did not move the needle".)
- Wrong:
  - Only 2 of 11 traits were tested. One (D1) is a near-copy of the 40 (r 0.715); the other (O3) is one rep.
  - "Did not win" makes drills the subject of a sports verb.
  - "Did not move the needle" contradicts the frozen label "Opposite", which says the needle moved, the wrong way.
- Fix, title:
  > "Two Combine-tracked drill traits added no edge in NFL pass-protection reps: a pre-registered test"
- Fix, §5 first sentence:
  > "Once you have a lineman's size, stopwatch times and NGS score, the two tracked drill traits that passed our gates gave no positive edge on 7,214 NFL pass-protection reps: an edge of even half the draft-slot effect is ruled out, and the small signal we found ran the wrong way and did not survive 5-frame smoothing."

**16. The engagement rule is misdescribed.** (§1 "stayed within 1.5 yards for at least four frames (0.4 s)".)
- Wrong: the code counts frames, not a run: `(d <= 1.5).sum() >= 4` in `engaged_reps.py`. "Stayed … for 0.4 s" implies contact without a break.
- Fix: "were within 1.5 yards of each other on at least four frames (0.4 s in total, not necessarily consecutive)".

**17. The step from 8,271 to 7,214 reps is incomplete.** (§1 "Requiring both players to have the registered Combine traits leaves 7,214 reps".)
- Wrong: 8,271 → 8,087 comes from the position filters (T/G/C blockers; DL rushers aligned EDGE or interior). Only then does 8,087 → 7,214 come from requiring both traits.
- Fix: "Restricting to tackles, guards and centres against Combine defensive linemen, and requiring both players' registered traits, leaves 7,214 reps…"

**18. The SESOI and MDE are stated in a pick unit the reader never sees.** (§2 "about 1.2 draft-pick-difference SDs", "half the draft-slot effect"; §3 "(0.10, half the draft-pick effect)".)
- Wrong: both use the pre-registration's pick effect of 0.20 (C3 PC1 = 0.204). The only pick effect in the text is 0.168. With 0.168, 0.10 is 0.6× and 0.247 is 1.47 pick SDs.
- Fix: write "(0.10, half the pre-registered draft-pick effect of 0.20)" and "about 1.2 SDs of the draft-pick difference at the pre-registered pick effect of 0.20". Add that the power figures were simulated for a GLM and carry over to the Bayesian model only approximately (pre-registration §12.1).

**19. Multiplicity is not stated where it bites.** (§3 "Secondaries carry no confirmatory claim"; §4; T2.)
- Wrong: S1 c_B (secondary) and d_cone (covariate) are the two "findings" discussed. The pre-registration requires the line "with about 10 secondary intervals, about one in 20 would exclude 0 by chance". Pre-registration §6.4 also requires "consistent with" wording, not "puts the signal on the blocker side".
- Fix: append to the §3 secondaries sentence:
  > "With about ten secondary intervals, about one would exclude zero by chance even if every effect were null."

**20. The dropback-time control is not disclosed.** (§2 pre-registration paragraph; limits.)
- Wrong: M1 conditions on dropback duration, which the rep's own outcome partly sets (pre-registration SA14). Without it the gap is -0.099 [-0.239, 0.044]. A hostile statistician will ask about conditioning on a post-outcome variable.
- Fix, limits: "the model controls dropback time, which pressure itself shortens; without it the estimate is -0.099 [-0.239, 0.044] (pre-registered sensitivity)."

**21. Composite reliabilities are overstated as "reliabilities".** (Limits "composite reliabilities (0.826, 0.780)".)
- Wrong: 0.826 is the Spearman-Brown value of an odd/even split *within one mirror rep*. 0.780 is a cross-side (left vs right) correlation, not test-retest. Neither measures day-to-day stability, which is what attenuation needs.
- Fix: "composite reliabilities (0.826 within one rep, 0.780 across sides; day-to-day reliability is unknown and likely lower) attenuate effects."

**22. "All code and numbers are in the public notebook" overclaims.** (Opening paragraph; notebook cell 0 "every number … that can be rebuilt".)
- Wrong:
  - The notebook rebuilds the pipeline, PC1 and the GLM mirror, and draws F1-F6.
  - It *loads* the Bayesian results and three exploratory CSVs.
  - It neither computes nor loads the X1(a)/(c), X4 or X5 numbers quoted in §4 (46,193 snaps, the +0.096 to +0.152 range, the 19,672 rusher snaps). These live only in `scripts/exploratory/` and `reports/exploratory_results.md`.
- Fix: "All code is in the public repository; the notebook rebuilds the data pipeline, positive control and figures from the raw files and loads the frozen Bayesian results and the exploratory tables." Also change §6's "loads the frozen Bayesian fits" to "loads the frozen Bayesian results".

**23. The spec-log blindness status is not stated.** (§4 "run after seeing the result and logged in the specification log".)
- Wrong: X1, X3 and X4 reading rules were written after preliminary looks at the same numbers (spec log E0, "not blind"). Only X2 and X5 were blind. The spec log says the writeup "must not present them as pre-specified". "Logged" lets a reader assume they were.
- Fix: "Everything below is exploratory: specified after the frozen result, with X2 and X5 blind and the others written after a first look (specification log)."

### Minor

**24. F4.**
- (a) The pink "registered minimum detectable effect ±0.247" band is drawn across every row. The MDE applies only to the gap. Restrict it to the four gap rows or drop it.
- (b) "every other pre-draft signal" is wrong: bench, vertical and broad jump are absent. Use "the club's other Combine measures and draft slot".
- (c) H2 is printed as -0.12 (from -0.125) and S0 with pick as [-0.28, …] (from -0.285). Print three decimals as in the text, or round consistently.

**25. F5.**
- (a) The row "c_B permutation test (X2): GLM estimate +0.143 [-0.005, 0.290]" is in the EXPLORATORY block, but the estimate and κ-CI are the frozen R5 GLM mirror; only p = 0.0645 is exploratory. Move the estimate to FROZEN and put the p in the label.
- (b) Mixed interval types on one axis: Bayes 95%, κ-calibrated, and the X1 nominal one-way-clustered intervals (anti-conservative). Mark each row's interval type or use κ throughout.
- (c) X1 standardises c_B over distinct blockers, while P standardises over reps, so "per SD" is not the same unit. Say so in a footnote.
- (d) The bold footer "lives in the 3-frame-specific part … does not appear on the same blockers' full seasons" asserts what the exploratory readings only suggest. Use "is concentrated in … and is not distinguishable from zero across the same blockers' full seasons (+0.037 [-0.027, 0.100])".
- (e) The writeup caption repeats all ten numbers that the figure already prints (about 90 words). Replace it with what to see:
  > "F5. Anatomy of the surprise. The blocker-side signal is fragile (frozen rows) and does not survive the exploratory checks (grey): it vanishes over the same blockers' full seasons, sits in the 3-frame-specific part of the trait, and does not show up in how far the blocker retreats."

**26. F6C.** The caption itself says the check "could not detect anything". Either drop panel C (and say in one sentence that cross-validation was too insensitive to detect even draft slot) or keep it with "was too insensitive to detect even draft slot (worth about 1 millinat per rep)". "Could not detect anything" is too absolute.

**27. F1.**
- The caption does not say how the rep ended (pressure or not). Add it: the figure exists to show "who won".
- "yards across (field strip)" is unclear; use "yards across the field from the blocker's snap position".
- The panel A legend lists a grey "engagement window" swatch that does not appear in panel A.

**28. F3.**
- Panel letter A covers two sub-panels, and the second shows O1, a *failed* trait.
- The blue shading in A has no colour key.
- Fine otherwise; it is the best figure for a football reader.

**29. §2 data facts.** "The 40-yard recording starts with the athlete already moving, so tracked times sit above official ones." The causal "so" is counter-intuitive (starting already moving would shorten a tracked time). Either explain the mechanism or write "starts with the athlete already moving, and tracked times run 0.2-0.3 s above official ones". This paragraph supports only failed traits and is a candidate for cutting to save words.

**30. "Charted pressure".** (Limits.) `pressure_allowed` is NGS-attributed per the feasibility report ("NGS pressure attribution"); "charted" implies human charting. Use "the NGS-attributed pressure".

**31. Jargon.** c_R, c_B, S0, S1, SA12, SA13, Q1, Q4, M1, M2 and κ appear in the body, captions and T2. Give each a plain-English label at first use. Remove c_R/c_B from T2 entirely ("rusher's rush-drill speed", "blocker's mirror quickness").

**32. T1 detail.** The O3 5-frame value has n = 104 (not 105). D1's "Repeat r" is cross-side (left vs right), like the pass-rush-drop reps. The caption says this only for the OL drop drill. Add "D1 is left vs right".

**33. Notebook.**
- Cell 0's title ("The athletic gap in the trenches…") differs from the writeup title; align them.
- Add the licence line to cell 0.
- Cell 14's bullet "F6 robustness: permutation null, placebo and sensitivities" is wrong: panel C is out-of-sample.

---

## 4. What is strong and must not be lost in revision

- **The pre-registration chain is real and verifiable.**
  - The tag `prereg-frozen` (deba6bc) carries the pre-registration SHA `1c0bba51…`, identical to the current file.
  - The script and pre-registration are byte-unchanged since the tag (empty `git diff`).
  - R0 records the same script hash and Git HEAD; there was one run (10:31-11:34, COMPLETE, no rerun) and all 11 Bayesian fits converged.
  - Section 0 of the pre-registration honestly discloses what outcome information was seen. Fix defect 2 so this survives a Linux clone, and keep it prominent.
- **The frozen label is stated verbatim and only once**, and immediately translated into the robust part (P(β < 0.10) = 0.999). Never let the "Opposite" sign become a football claim. The draft currently does not, and "Opposite" is never turned into "athletic blockers allow pressure".
- **F2A (79.7% vs 19.3%, 627/787 vs 333/1,725)** is the single most convincing piece of evidence for the engine. Keep it as the anchor.
- **Every confirmatory number in the text matches the frozen files.** I checked every number in §1-§6, T1, T2 and the captions against R1-R8, `trait_qualification.md`, the exploratory tables and the figure CSVs. The only errors are defect 8 (seasons) and the mislabels in defects 3, 4, 13 and 25a.
- **The notebook really reproduces the pipeline:** 54/54 assertions, PC1 to 4 decimals, and the GLM mirror equal to the frozen run to 3 decimals. It also honestly declares what it loads rather than recomputes.
- **The measurement recommendation** (several mirror reps, raw reversal times, faster sampling, body orientation; "the 40 already gives true repeats; drills should too") is concrete, actionable and was motivated before outcomes (the O3 fragility was flagged in `trait_qualification.md`). It is the entry's best football contribution.
- **T1** shows the pool, the gates and the near-misses (O1 by 0.007, O4/D5 by a player or two) without tuning. It is a model of transparency.
- **S0 is co-reported next to H1** in F4 as the pre-registration requires, and the discordant sensitivities are named.

---

## 5. The three questions a hostile judge would ask

**Q1. "Your headline sign rests on one 10 Hz mirror rep per blocker: six distinct values across 69 blockers, 35 of them tied at 0.50 s. Its interval clears zero by 0.005 under a flat N(0, 1) prior, touches zero in the calibrated GLM, includes zero in 12 of 18 Bayesian sensitivity fits, and vanishes with 5-frame smoothing. Why is any of it more than noise, and why is your bound not flattered by the same noise?"**
- Does the draft answer it? **Partly.**
- It calls the sign "weak", names SA12 and SA13, and correctly calls the bound "the robust finding".
- It does not give the 12-of-18 count, the prior sensitivity, or the fact that every sensitivity's upper bound is ≤ 0.125 (which is what actually answers the second half).
- It also misplaces the passing permutation test among the weaknesses.
- Defect 4's replacement text answers the question in about 90 words.

**Q2. "What is the Combine-tracking → NFL link you have demonstrated, and what should a club do on Monday? You tested two of eleven traits: one is a 40-yard proxy (r 0.715), the other a single rep. Your 'gap' subtracts a defensive lineman's arc speed from an offensive lineman's mirror quickness, as if they traded off one-for-one, and your own split (S1) shows they do not. Your takeaway is 'use draft slot'."**
- Does the draft answer it? **Partly.**
- The bound and the measurement recommendation are a genuine answer for clubs, and the "engine as a tool" paragraph is good.
- But the title over-generalises (defect 15), the gap construct is never justified in football terms, and T2's "what to use" adds nothing a scout does not know.
- Add one sentence after the H1 definition:
  > "The gap asks whether the more athletic player of the pair wins; the side split (S1) tests each player's trait separately."
- End §5 with the concrete measurement ask, not with draft slot.

**Q3. "Does your engine identify who won the rep, or just who was nearby when the blocker was charged? The outcome is the blocker's play-level pressure, shared by all his pairs on that play. 16% of your non-engaged 'placebo' pairs carry an engaged rep's outcome. Draft slot keeps half its effect on non-engaged pairs."**
- Does the draft answer it? **Partly.**
- F2A answers the "matchup" half well: the engaged rusher is credited 79.7% of the time against 19.3%.
- The draft is silent on shared outcomes and placebo contamination, and it oversells the 0.48 ratio as support.
- Defect 6's fixes answer it honestly.
- Add to the limitations that pressure is attributed per play, not per rep, and that rushers are Combine defensive linemen only (edge rushers who tested with the linebackers are not in the cohort of rushers).
