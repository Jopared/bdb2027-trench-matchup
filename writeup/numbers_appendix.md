# Numbers appendix (not submitted)

**Word count of writeup.md: 1,868** by the token rule (whitespace-separated tokens containing a letter or digit; headings, captions, table cells and the references line counted; image lines excluded). An independent count was 1,873 (small tokenizer difference). Naive `split()` over all non-image lines: 1,998; over every line including the six image lines: 2,004. Limit 2,000. Figures + tables = 8 (F1-F6, T1, T2).

Abbreviations: CR = reports/confirmatory_results.md (R-sections; same numbers as confirmatory_results.json); INT = reports/interpretation.md; XR = reports/exploratory_results.md; XT = reports/exploratory/tables; TQ = reports/trait_qualification.md; C3 = reports/feasibility_c3.md; DB = reports/dataset_build.md; PR = reports/preregistration.md; AC = reports/audit_combine.md.

## Frozen / design numbers

| Number in writeup | Source |
|---|---|
| 8,271 engaged reps; 29,269 pairs; 1.5 yd on at least 4 frames (count, not a run), window snap+0.2 s to earliest of 3.0 s / pass_forward / qb_sack | DB sections 1-2 (Engaged = at least k frames with d <= thr); C3 G1 |
| 79.7% (627 of 787) vs 19.3% (333 of 1,725) | C3 G1; figures/F2_engine_is_real.csv panel A |
| PC1 -0.204, SE 0.049, 8,271 engaged reps | CR R2 (PC1 pick coefficient -0.2039, SE 0.0486); C3 G2 |
| Full model draft pick -0.168 [-0.312, -0.031] (M2, set P) | CR R2 PC2, R4 M2 d_lpick |
| Calibrated GLM interval for draft pick [-0.280, 0.004] | CR R4 M2 d_lpick, GLM column (first bracket = kappa-calibrated) |
| Non-engaged pick effect about half (ratio 0.48, -0.080); pre-registered expectation about 0.37 | CR R6 (0.479; "C3 reference about 0.37"); figures/F2 csv |
| Not tested against each other | no such test exists in CR; statement of absence |
| 2,882 of 17,795 non-engaged pairs share a play and blocker with an engaged rep | INT B6 (E0.6, logged in specification_log.md; exploratory); 17,795 = CR R1 set PL |
| Filters to 7,214 reps, 69 blockers, 97 rushers, 681 pressures, 9.44% | CR R1 set P; DB section 4 (T/G/C; DL EDGE/INTERIOR) |
| Closed pool of 11 traits (O1-O5, D1-D6); two passed | TQ sections 0-1, 5; PR section 3 |
| Feasibility stage had seen draft-pick and weight effects on pressure | PR section 0 (disclosure table, C3 G2 row) |
| Gates: |r| < 0.75; 80% coverage; reliability r 0.50 with CI bound 0.30 (O3: 0.60 odd/even) | TQ section 1 gate rules |
| T1 rows: repeat r, 5-frame r, max abs r, verdicts (n column removed from the table; CIs removed) | TQ section 1 table (r, max abs r, verdict); section 6 (5-frame r) |
| T1 caption: 84-118 players each (n = 118, 116, 105, 84, 84, 106, 92, 84, 84, 84 for the ten rows shown) | TQ section 1 table, n pairs column; range checked: min 84, max 118 |
| T1 caption: D4 omitted, two players | TQ section 1 (D4 n pairs 2; players with a value 2 of 118) |
| O3 0.704 (3-frame) vs 0.570 (5-frame) | TQ section 1a O3, section 6 |
| O3 = median reversal time in one rep, at least four reversals | TQ O3 detail |
| D1 left vs right cross-side r | TQ section 7 (D1 pairs left with right) |
| Pass-rush-drop reps are mirrored drills from different stances | AC finding 3; TQ section 6 side-label checks |
| F1 caption: Wright vs Van Ness, 2023 week 1, 14 frames within 1.5 yd | figures/F1_engaged_rep.png title; F1_engaged_rep.csv (n_close_150 = 14 in engaged_pairs.parquet) |
| F1 caption: "no pressure allowed" | data/processed/engaged_outcomes_SEALED.parquet row game_id 2023091008, play_id 619, blocker 55874, rusher 55877: pressure_allowed False, rusher_time_to_pressure null (verified read-only; the outcome file is unsealed after the frozen run) |
| F3 caption: two tackles, official 40 5.38 s; 4- vs 5-frame reversal | figures/F3_combine_measured.png |
| H1 definition, sign, covariates; S1; draft slot excluded from primary, in H2 | PR sections 1.2, 1.4 |
| Bayesian logistic with crossed random intercepts for blocker and rusher | PR section 5.3 / 1.5 |
| Frozen and hashed before the sealed outcome file was opened; script ran once | PR sections 0, 13.1; CR R0 (hashes match) |
| Decision rule: Supported if lo > 0, Opposite if hi < 0, else Inconclusive; qualifiers change wording only | PR section 6.3 |
| MDE 0.247; 26-35% power for half of that (the "1.2 SDs" phrase is no longer in the text) | PR 12.3-12.5 |
| Q1 = GLM mirror agrees (fails); Q4 = discordant sensitivities | PR section 6.3 qualifier table; CR R3 |
| Label "Opposite (qualified: Q1); Q4 failed (discordant: SA12, SA13)" (once, verbatim) | CR R3 final label |
| -0.153 [-0.299, -0.005]; -1.06 pp [-2.02, -0.10]; P(beta < 0.10) = 0.999 | CR R3 |
| SESOI 0.10 = half the pick effect 0.20 | PR 6.3, 12.5 |
| About ten secondary intervals, about one in 20 by chance | PR 6.4; CR R5 footnote |
| H2 Inconclusive -0.125 [-0.273, 0.025] | CR R4, R5 |
| S0: 7,720 reps, 75 blockers; M1-A -0.154 [-0.288, -0.022]; M2-A -0.149 [-0.285, -0.009] | CR R1 (P-A), R5 |
| SA11 (composite A on P's rows) -0.131 [-0.278, 0.022]; 506 = 7,720 - 7,214; 6 = 75 - 69 | CR R8 SA11; R1 |
| Registered permutation check p = 0.0375 (two-sided studentized), passed; coefficient-based 0.0535; observed t -2.393 | CR R3 Q2, R6; F6 panel A |
| Calibrated GLM interval [-0.308, 0.000] | CR R3 |
| 13 of 19 pre-listed sensitivity intervals include zero (SA2, SA5, SA7, SA15, SA8, SA10-SA14, SA16, SA17, SA18_0.5); SA8 is GLM-only | CR R8 (counted; re-verified); F6 panel C title |
| N(0, 0.5) prior [-0.298, 0.005] | CR R8 SA18_0.5 Bayes |
| SA13 -0.074 [-0.227, 0.083]; SA12 -0.042 [-0.197, 0.125] | CR R8 |
| Every sensitivity's upper limit at most 0.125 | CR R8 Bayes column max = SA12 0.125; SA8 GLM nominal 0.065, calibrated 0.102; INT summary item 1 |
| S1: blocker +0.156 [0.020, 0.301]; rusher -0.033 [-0.209, 0.160] | CR R5 (Bayes) |
| Football translation of the S1 sign | interpretation of c_B (higher composite = faster reversal; O3 oriented so lower time = more athletic, TQ O3 orientation) |
| 3-cone -0.181 [-0.353, -0.006] (Bayes); calibrated GLM -0.180 [-0.362, 0.003] includes zero | CR R4 M1 d_cone |
| T2 rows weight, arm, 40, 10-yd, shuttle, NGS (Bayes) | CR R4 M1 rows d_weight, d_arm, d_forty, d_ten, d_shuttle, d_ngs |
| Seven official-measure differences in M1 (weight, arm, forty, ten, shuttle, cone, ngs) | CR R4 M1 d_ rows |
| Shuttle +0.134 points the unexpected way (raw time, higher = slower: slower rusher, more pressure) | CR R4; INT A6.2 sign convention |
| D1 max abs r 0.715 vs forty | TQ D1 |
| Trait reliabilities "0.83 and 0.78": rounded from 0.826 (OL composite, O3 Spearman-Brown within one rep) and 0.780 (DL composite, D1 Spearman-Brown cross-side), 2 decimals | TQ section 2 (Mosier composite reliability, OL 0.826, DL 0.780) |
| O3 takes six values among 69 blockers, 35 tied at 0.50 s; frame 0.1 s | XT/x3_O3_value_counts.csv (0.4:14, 0.45:11, 0.5:35, 0.55:3, 0.6:5, 0.65:1); INT summary 3 |
| F6 caption: t -2.39, p 0.0375, coefficient-based 0.0535; 13 of 19 include zero; about 1 millinat per rep; every richer set worse than context-only | CR R6, R8, R7 (I0 0.27814 beats I1-I4); INT A6.1 (about 1.2); figure footnote (about 1) |
| Seasons: blockers 2,804 / 2,587 / 1,823 reps in first / second / third NFL season in set P | Computed read-only: engaged_pairs.parquet filtered to engaged_primary, blocker T/G/C and OL, rusher DL at EDGE/INTERIOR_LINE, both composites non-null (7,214 rows, 69 blockers, 97 rushers), joined to player_baselines.parquet draft_year, season minus draft_year. Rushers: 2,597 / 2,654 / 1,963. 1,823 / 7,214 = 25.3% |
| Notebook rebuilds pipeline, PC1, GLM mirror and figures; loads Bayesian results | notebooks/README.md steps 1-8 |
| Hashed files use pinned line endings | repository .gitattributes (scripts/confirmatory_analysis.py and src/bdb2027/traits.py eol=crlf; paths.py and preregistration.md eol=lf) |
| Opponents are Combine DL only (rusher set P: combine_position DL) | CR R1; PR section 2.2 |

## Exploratory numbers (labelled exploratory in the writeup)

| Number | Source |
|---|---|
| Blocker-term permutation p 0.065 two-sided (0.0645); the one-sided value is not used (coefficient-based 0.100 no longer quoted) | XT/x2_permutation_summary.csv (p_two_studentized, p_two_coef); XR X2 |
| All pass-pro snaps: 46,193, +0.037 [-0.027, 0.100] (nominal) | XR X1 (a) |
| Non-engaged snaps +0.019 [-0.045, 0.082] (nominal) | XR X1 (c) |
| 3-frame part +0.219 [0.018, 0.419]; 5-frame part -0.108 [-0.339, 0.124] (calibrated) | XT/x3_glm_fits.csv rows (c), columns lo_k, hi_k; figures/F5_anatomy.csv |
| Fast (0.45 s or less) +0.214 [-0.014, 0.442]; slow (0.55 s or more) -0.215 [-0.596, 0.166] against 0.50 s (nominal) | XT/x3_glm_fits.csv rows fast, slow; XR X3 (a) |
| Later picks: c_B x blocker log pick +0.136 [0.041, 0.231] (nominal; calibrated [0.022, 0.250]) | XT/x4_glm_fits.csv row cB_x_lpick; XR X4 (a) |
| Composite does not significantly predict reps or in-P membership | XR X4 (c): late half logit +0.339 [-0.311, 0.989]; OLS +0.218 [-0.154, 0.588] |
| Set depth at 0.5 s: -0.022 outcome SD [-0.079, 0.035] | XT/x3_glm_fits.csv (e); XR X3 (e) |
| Rusher snaps: 19,672, 98 linemen, +0.021 [-0.112, 0.155] | XR X5 (a) |
| F5 caption: qualitative; the +0.143 GLM estimate is the frozen S1 GLM mirror, only the permutation p 0.0645 is exploratory | CR R5 S1 c_B GLM; XT/x2_permutation_summary.csv; figures/F5_anatomy.csv (no other numbers in the caption) |
| Spec status: X2 and X5 blind; others written after a first look | XR header; INT section C ("Blind?" column); specification_log.md |
| Removed from the writeup (no longer in text): the +0.096 to +0.152 adjustment range, the 3-cone sentence, "S0 sits on the rusher side", the dropback-free estimate (SA14 -0.099 [-0.239, 0.044]), the "1.2 pick SDs" phrase, T1's n and CI columns, the coefficient-based p 0.100 | n/a |

## Could not source / conflicts / disagreements

- "13 traits tried" (original brief) is in no file; the files say 11. The writeup says 11.
- Review point 10: "one of 16 covariates". I could not reproduce 16 from CR R4 (M1 has seven official-measure difference terms, seven sum terms and six missing-flag terms). The writeup says "seven official-measure differences", which is traceable.
- Review point 4 (corrected): 13 of 19, used throughout; SA8 counts with its GLM interval, so the F6 axis mixes Bayes and GLM for that row (labelled in the figure).
- "About 1 millinat per rep": INT A6.1 computes about 1.2; the F6 footnote says about 1; the writeup follows the figure.
- F1: the caption now says "no pressure allowed" (verified, see table above).
- The F4 image still prints the frozen label in its subtitle; the writeup body states it once.
- Judge items on figures only (F4 shading, F6A, F5 interval types, F1 legend, F3 panel labels) are not fixable from the markdown; the F5 caption now notes mixed interval types only implicitly (nominal / calibrated are named in the text bullets). F5's X1 intervals are nominal one-way-clustered and its "per SD" unit differs slightly (X1 standardises over blockers); this is not stated in the text for lack of words.
- The judge's items 16-23 and 29-31 were applied where cheap (frames-not-run, filter chain, multiplicity line, dropback, reliability wording, "NGS-attributed", exploratory blindness status, 40-yard sentence removed). Not applied: jargon glosses for M1/M2/kappa in all captions; S1/S0/SA labels are glossed once in the text.
