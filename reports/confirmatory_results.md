# Confirmatory results

Filled by `scripts/confirmatory_analysis.py`; nothing in this file is written by hand.

## R0 Run manifest

| Item | Value |
|---|---|
| Script SHA-256 (computed / registered) | 8d842b70db03e2b0aa223f827bf0a496cb971ca3ea03f0a7c56563be8c046aca / 8d842b70db03e2b0aa223f827bf0a496cb971ca3ea03f0a7c56563be8c046aca |
| preregistration.md SHA-256 | 1c0bba51eb263b36ffd171f2feb50c00234a4be62a86b2830af918be44a1cb24 |
| Git HEAD | deba6bc1772192c60a3980ba85438df1127e2b23 |
| Input hashes match | data/processed/engaged_pairs.parquet: yes; data/processed/player_baselines.parquet: yes; data/processed/combine_traits.parquet: yes; data/processed/engaged_outcomes_SEALED.parquet: yes; data/processed/combine_tracking.parquet: yes; data/processed/combine_results.parquet: yes; src/bdb2027/traits.py: yes; src/bdb2027/paths.py: yes |
| Versions | python 3.12.10, pymc 6.4.0, arviz 1.3.0, pytensor 3.3.7, statsmodels 0.15.0, numpy 2.5.4, pandas 3.1.1, polars 2.1.0 |
| Start / end / CPUs | 2026-11-07T10:31:05 / 2026-11-07T11:34:54 / 32 (cores used per fit: 4) |
| Status | COMPLETE |

## R1 Analysis sets

| Set | Reps | Pressures | Rate | Blockers | Rushers | Dyads | 2023 / 2024 / 2025 | REG | Rows dropped (reason) |
|---|---|---|---|---|---|---|---|---|---|
| P | 7214 | 681 | 0.0944 | 69 | 97 | 1201 | 431 / 1821 / 4962 | 6867 | 0 |
| PL | 17795 | 1442 | 0.081 | 73 | 98 | 1502 | 991 / 4635 / 12169 | 16916 | 4 (null context covariate) |
| ALL | 25009 | 2123 | 0.0849 | 75 | 98 | 1541 | 1422 / 6456 / 17131 | 23783 | 4 (null context covariate) |
| P-A | 7720 | 728 | 0.0943 | 75 | 97 | 1281 | 431 / 1882 / 5407 | 7297 | 0 |
| PL-A | 18849 | 1532 | 0.0813 | 79 | 98 | 1593 | 991 / 4752 / 13106 | 17830 | 4 (null context covariate) |
| P-B | 8087 | 764 | 0.0945 | 79 | 97 | 1342 | 431 / 2046 / 5610 | 7664 | 0 |
| P-DL | 8087 | 764 | 0.0945 | 79 | 97 | 1342 | 431 / 2046 / 5610 | 7664 | 0 |
| SA1 | 6394 | 612 | 0.0957 | 69 | 97 | 1165 | 385 / 1623 / 4386 | 6096 | 0 |
| SA2 | 8924 | 791 | 0.0886 | 70 | 97 | 1269 | 515 / 2229 / 6180 | 8488 | 0 |
| SA3 | 7448 | 695 | 0.0933 | 70 | 97 | 1212 | 442 / 1879 / 5127 | 7085 | 0 |
| SA4 | 6643 | 641 | 0.0965 | 69 | 97 | 1164 | 401 / 1663 / 4579 | 6329 | 0 |
| SA5 | 6867 | 646 | 0.0941 | 68 | 97 | 1169 | 427 / 1771 / 4669 | 6867 | 0 |
| SA6 | 6261 | 618 | 0.0987 | 68 | 96 | 1120 | 431 / 1584 / 4246 | 5992 | 0 |
| SA7 | 5326 | 445 | 0.0836 | 69 | 71 | 895 | 331 / 1279 / 3716 | 5066 | 0 |
| SA9 | 7000 | 647 | 0.0924 | 69 | 97 | 1190 | 427 / 1783 / 4790 | 6676 | 0 |
| SA11 | 7214 | 681 | 0.0944 | 69 | 97 | 1201 | 431 / 1821 / 4962 | 6867 | 0 |
| SA13 | 7214 | 681 | 0.0944 | 69 | 97 | 1201 | 431 / 1821 / 4962 | 6867 | 0 |
| SA15 | 4742 | 437 | 0.0922 | 57 | 77 | 770 | 295 / 1241 / 3206 | 4509 | 0 |
| R (E0 & engaged_primary) | 8087 | 764 | 0.0945 | 79 | 97 | 1342 | 431 / 2046 / 5610 | 7664 | 0 |

Gap SD (registered, P): 1.2535; SD_lpd: 1.3945; SD of the raw pick difference: 96.4 picks.

Dropped columns per model (column hygiene):

| Model | Dropped columns |
|---|---|
| M1 | none |
| M2 | none |
| M0 | none |
| M1-A | none |
| M2-A | none |
| M1-S1 | none |
| M1-S2 | none |
| M1-S3a | pre0 (constant) |
| M1-S3b | none |
| S5a | none |
| S5b | none |
| M1-PL | none |
| M2-PL | none |
| SA1 | none |
| SA2 | none |
| SA3 | none |
| SA4 | none |
| SA5 | none |
| SA6 | double_team (constant) |
| SA7 | none |
| SA9 | none |
| SA15 | f_dash_B (constant); f_dash_R (constant) |
| SA8 | none |
| SA10 | none |
| SA11 | none |
| SA12 | none |
| SA13 | none |
| SA14 | none |
| SA16 | none |
| SA17 | none |
| SA18_0.5 | none |
| SA18_2.5 | none |
| SC2 | none |
| SC3a | none |
| SC3b | none |
| SC4 | none |
| R | none |
| M1-S2s | none |

## R2 Decisive checks

| Check | Expected | Observed | Status |
|---|---|---|---|
| V0 counts and join | Section 2.3 | all section 2.3 counts match (19 sets, 19 facts); outcome join 1:1 (no rows lost or duplicated); no nulls in pressure_allowed on P | PASS |
| PC1 events | 787 | 787 |  |
| PC1 pick coefficient | -0.204 +/- 0.003 | -0.2039 (SE 0.0486) | PASS |
| PC1 dropback coefficient | 0.577 +/- 0.003 | 0.5772 | PASS |
| PC2 M2 d_lpick | 95% interval < 0 | -0.168 [-0.312, -0.031] | PASS |
| Convergence M0 | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0028, min ESS bulk/tail 11133/5981, divergences 0, escalated n | ok |
| Convergence M1 | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0078, min ESS bulk/tail 13420/5178, divergences 0, escalated n | ok |
| Convergence M2 | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0054, min ESS bulk/tail 12199/5947, divergences 0, escalated n | ok |
| Convergence M1-A | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0044, min ESS bulk/tail 8951/6225, divergences 0, escalated n | ok |
| Convergence M2-A | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0089, min ESS bulk/tail 8323/5355, divergences 0, escalated n | ok |
| Convergence M1-S1 | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0046, min ESS bulk/tail 24622/11861, divergences 0, escalated y | ok |
| Convergence M1-S2 | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0036, min ESS bulk/tail 12083/5895, divergences 0, escalated n | ok |
| Convergence M1-S3a | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0029, min ESS bulk/tail 14151/6280, divergences 0, escalated n | ok |
| Convergence M1-S3b | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0056, min ESS bulk/tail 12392/5993, divergences 0, escalated n | ok |
| Convergence M1-PL | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0025, min ESS bulk/tail 7577/6166, divergences 0, escalated n | ok |
| Convergence M2-PL | R-hat <= 1.01, ESS >= 400, divergences <= 0.1% | max R-hat 1.0031, min ESS bulk/tail 6329/5680, divergences 0, escalated n | ok |
| Pre-freeze Bayesian calibration (T1) | <= 9 of 100 null intervals exclude 0 | 6 of 100; coverage 0.94 | contingency INACTIVE |
| Pre-freeze permutation calibration (T1b) | <= 5 of 50 with p < 0.05 | 2 of 50 | ok |

## R3 Primary result (H1, M1, registered composite, set P)

| Quantity | Value |
|---|---|
| beta_gap, log-odds per SD of gap: Bayes | mean -0.152, median -0.153 [-0.299, -0.005] |
| beta_gap per composite-z unit | -0.122 [-0.239, -0.004] |
| P(beta_gap > 0); P(beta_gap < 0.10) | 0.022; 0.999 |
| GLM mirror | -0.154; kappa-calibrated [-0.308, 0.000], p 0.0502; nominal [-0.283, -0.026], SE 0.0644, t df 68, p 0.0195 |
| AME, percentage points per rep (+1 SD gap) | -1.060 [-2.017, -0.102] |
| Extra pressures per 100 engaged reps | -1.060 [-2.017, -0.102] |
| Reps per extra pressure | -94.4 [-984.7, -49.6] |
| Base-rate pp change (power-simulation convention) | -1.235 [-2.283, -0.043] |
| Pick-difference SDs per gap SD (k) | -0.896 [-4.082, 0.035] |
| Pick ratio exp(delta); slots at pick 64 | 0.287 [0.003, 1.050]; -159.13 [-18911.977, 3.037] |
| MDE (section 12), log-odds / pp / pick-difference SDs | 0.247 / 2.35 / 1.23 |
| Verdict category | Opposite; decision basis: bayes |
| Q1 GLM mirror agrees | fail: kappa-calibrated CI [-0.308, 0.000] |
| Q2 Freedman-Lane permutation p | pass: p = 0.0375 |
| Q3 placebo ratio | pass: ratio = 0.275 |
| Q4 discordant sensitivities | fail: discordant: SA12, SA13 |
| Q5 selection | pass: SC2 not flagged |
| Final label | Opposite (qualified: Q1); Q4 failed (discordant: SA12, SA13) |

## R4 Information ladder and forest data

| Model | Term | Bayes median [95%] | GLM [95% CI] | Pick-equivalent k [95%] |
|---|---|---|---|---|
| M0 | gap | -0.059 [-0.185, 0.070] | -0.054 [-0.159, 0.052] {-0.142, 0.034} | -0.343 [-2.105, 0.575] |
| M1 | gap | -0.153 [-0.299, -0.005] | -0.154 [-0.308, 0.000] {-0.283, -0.026} | -0.896 [-4.082, 0.035] |
| M2 | gap | -0.125 [-0.273, 0.025] | -0.138 [-0.306, 0.031] {-0.278, 0.003} | -0.741 [-3.860, 0.208] |
| M1 | d_weight | 0.068 [-0.126, 0.261] | 0.067 [-0.126, 0.261] {-0.094, 0.228} |  |
| M1 | s_weight | -0.106 [-0.279, 0.062] | -0.097 [-0.286, 0.092] {-0.254, 0.060} |  |
| M1 | d_arm | 0.010 [-0.133, 0.159] | -0.006 [-0.168, 0.156] {-0.141, 0.129} |  |
| M1 | s_arm | 0.048 [-0.110, 0.214] | 0.008 [-0.172, 0.187] {-0.142, 0.157} |  |
| M1 | d_forty | -0.035 [-0.333, 0.253] | -0.016 [-0.305, 0.273] {-0.257, 0.225} |  |
| M1 | s_forty | 0.101 [-0.224, 0.438] | 0.130 [-0.183, 0.442] {-0.131, 0.390} |  |
| M1 | d_ten | -0.100 [-0.388, 0.198] | -0.095 [-0.345, 0.154] {-0.303, 0.112} |  |
| M1 | s_ten | -0.036 [-0.348, 0.278] | -0.108 [-0.410, 0.195] {-0.360, 0.144} |  |
| M1 | d_shuttle | 0.134 [-0.052, 0.320] | 0.121 [-0.079, 0.322] {-0.046, 0.289} |  |
| M1 | s_shuttle | 0.059 [-0.129, 0.237] | 0.065 [-0.110, 0.240] {-0.081, 0.211} |  |
| M1 | d_cone | -0.181 [-0.353, -0.006] | -0.180 [-0.362, 0.003] {-0.332, -0.027} |  |
| M1 | s_cone | -0.056 [-0.230, 0.117] | -0.062 [-0.228, 0.103] {-0.200, 0.076} |  |
| M1 | d_ngs | 0.078 [-0.114, 0.271] | 0.088 [-0.101, 0.278] {-0.070, 0.247} |  |
| M1 | s_ngs | 0.191 [-0.001, 0.398] | 0.157 [-0.059, 0.374] {-0.023, 0.338} |  |
| M1 | f_dash_B | -0.027 [-0.394, 0.339] | -0.032 [-0.407, 0.342] {-0.344, 0.280} |  |
| M1 | f_dash_R | -0.018 [-0.331, 0.317] | -0.022 [-0.367, 0.324] {-0.309, 0.266} |  |
| M1 | f_shuttle_B | 0.005 [-0.312, 0.307] | 0.009 [-0.368, 0.387] {-0.305, 0.324} |  |
| M1 | f_shuttle_R | 0.097 [-0.247, 0.457] | 0.045 [-0.318, 0.408] {-0.258, 0.348} |  |
| M1 | f_cone_B | -0.051 [-0.394, 0.296] | -0.071 [-0.507, 0.366] {-0.435, 0.293} |  |
| M1 | f_cone_R | 0.001 [-0.394, 0.382] | 0.022 [-0.409, 0.452] {-0.337, 0.380} |  |
| M1 | sigma_B | 0.259 [0.094, 0.427] |  |  |
| M1 | sigma_R | 0.283 [0.044, 0.501] |  |  |
| M2 | d_weight | 0.075 [-0.118, 0.263] | 0.073 [-0.111, 0.256] {-0.080, 0.226} |  |
| M2 | s_weight | -0.102 [-0.274, 0.070] | -0.088 [-0.277, 0.100] {-0.245, 0.069} |  |
| M2 | d_arm | 0.011 [-0.130, 0.157] | -0.005 [-0.170, 0.161] {-0.142, 0.133} |  |
| M2 | s_arm | 0.037 [-0.123, 0.201] | -0.000 [-0.184, 0.183] {-0.153, 0.153} |  |
| M2 | d_forty | -0.006 [-0.297, 0.280] | -0.011 [-0.304, 0.282] {-0.255, 0.233} |  |
| M2 | s_forty | 0.095 [-0.240, 0.426] | 0.136 [-0.196, 0.467] {-0.140, 0.412} |  |
| M2 | d_ten | -0.137 [-0.425, 0.155] | -0.128 [-0.374, 0.118] {-0.333, 0.077} |  |
| M2 | s_ten | -0.022 [-0.322, 0.295] | -0.106 [-0.420, 0.208] {-0.368, 0.156} |  |
| M2 | d_shuttle | 0.142 [-0.042, 0.334] | 0.134 [-0.066, 0.334] {-0.033, 0.301} |  |
| M2 | s_shuttle | 0.075 [-0.111, 0.253] | 0.082 [-0.091, 0.255] {-0.062, 0.226} |  |
| M2 | d_cone | -0.194 [-0.374, -0.019] | -0.199 [-0.375, -0.023] {-0.345, -0.052} |  |
| M2 | s_cone | -0.052 [-0.223, 0.116] | -0.056 [-0.220, 0.108] {-0.193, 0.080} |  |
| M2 | d_ngs | 0.019 [-0.179, 0.223] | 0.029 [-0.157, 0.216] {-0.126, 0.185} |  |
| M2 | s_ngs | 0.215 [0.011, 0.418] | 0.190 [-0.037, 0.416] {0.001, 0.378} |  |
| M2 | f_dash_B | -0.006 [-0.372, 0.351] | 0.006 [-0.354, 0.366] {-0.294, 0.306} |  |
| M2 | f_dash_R | -0.030 [-0.366, 0.305] | -0.021 [-0.382, 0.339] {-0.322, 0.279} |  |
| M2 | f_shuttle_B | 0.060 [-0.270, 0.379] | 0.055 [-0.338, 0.447] {-0.272, 0.382} |  |
| M2 | f_shuttle_R | 0.114 [-0.225, 0.478] | 0.055 [-0.309, 0.419] {-0.249, 0.358} |  |
| M2 | f_cone_B | -0.009 [-0.358, 0.345] | -0.042 [-0.477, 0.393] {-0.405, 0.320} |  |
| M2 | f_cone_R | -0.007 [-0.388, 0.375] | 0.015 [-0.410, 0.440] {-0.340, 0.369} |  |
| M2 | d_lpick | -0.168 [-0.312, -0.031] | -0.138 [-0.280, 0.004] {-0.256, -0.019} |  |
| M2 | f_undr_B | -0.053 [-0.798, 0.639] | -0.051 [-0.635, 0.534] {-0.538, 0.436} |  |
| M2 | f_undr_R | 0.254 [-0.243, 0.721] | 0.214 [-0.311, 0.739] {-0.224, 0.652} |  |
| M2 | sigma_B | 0.269 [0.102, 0.433] |  |  |
| M2 | sigma_R | 0.275 [0.029, 0.479] |  |  |
| M1-A | gap | -0.154 [-0.288, -0.022] | -0.143 [-0.308, 0.022] {-0.280, -0.006} | -0.896 [-4.155, -0.058] |
| M2-A | gap | -0.149 [-0.285, -0.009] | -0.144 [-0.323, 0.035] {-0.293, 0.005} | -0.830 [-3.060, -0.035] |

## R5 Secondaries

| ID | Model | Estimand | Expected | Bayes median [95%] | P(expected direction) | GLM [95% CI] | n | Category (H2, S0 only) |
|---|---|---|---|---|---|---|---|---|
| H2 | M2 | gap | + | -0.125 [-0.273, 0.025] | 0.049 | -0.138 [-0.306, 0.031] {-0.278, 0.003} | 7214 | Inconclusive |
| M0 | M0 | gap | + | -0.059 [-0.185, 0.070] | 0.184 | -0.054 [-0.159, 0.052] {-0.142, 0.034} | 7214 |  |
| S0 | M1-A | gap | + | -0.154 [-0.288, -0.022] | 0.012 | -0.143 [-0.308, 0.022] {-0.280, -0.006} | 7720 | Opposite |
| S0 | M2-A | gap | + | -0.149 [-0.285, -0.009] | 0.019 | -0.144 [-0.323, 0.035] {-0.293, 0.005} | 7720 | Opposite |
| S1 | M1-S1 | c_R | + | -0.033 [-0.209, 0.160] | 0.361 | -0.064 [-0.260, 0.132] {-0.227, 0.099} | 7214 |  |
| S1 | M1-S1 | c_B | - | 0.156 [0.020, 0.301] | 0.012 | 0.143 [-0.005, 0.290] {0.020, 0.266} | 7214 |  |
| S1 | M1-S1 | c_R + c_B | none | 0.123 [-0.101, 0.363] |  | 0.079 [-0.173, 0.331] {-0.131, 0.289} | 7214 |  |
| S2 | M1-S2 | gap x edge | + | -0.052 [-0.255, 0.146] | 0.317 | 0.015 [-0.291, 0.321] {-0.240, 0.270} | 7214 |  |
| S2 | M1-S2 | gap (interior) | >=0 | -0.123 [-0.304, 0.066] | 0.103 | -0.163 [-0.384, 0.058] {-0.347, 0.021} | 7214 |  |
| S2 | M1-S2 | gap (edge) | + | -0.173 [-0.350, -0.002] | 0.024 | -0.148 [-0.365, 0.069] {-0.329, 0.033} | 7214 |  |
| S3a | M1-S3a | gap, pp of peak pressure probability | + | -0.851 [-1.793, 0.095] | 0.040 | -0.797 [-1.753, 0.159] {-1.594, -0.001} | 7100 |  |
| S3b | M1-S3b | gap | + | -0.135 [-0.274, -0.001] | 0.025 | -0.127 [-0.296, 0.041] {-0.268, 0.013} | 7214 |  |
| S5 | S5a | beta_depth | + | 0.322 [0.206, 0.441] | 1.000 | 0.314 [0.139, 0.488] {0.168, 0.459} | 7214 |  |
| S5 | S5b | beta_depth | none | 0.318 [0.193, 0.435] |  | 0.308 [0.130, 0.486] {0.160, 0.456} | 7214 |  |
| S5 | S5a/S5b | share = 1 - med(S5b)/med(S5a) | + | 0.011 (point estimate) |  |  | 7214 |  |

Secondary results carry no confirmatory claim; with about 10 secondary intervals, about one in 20 would exclude 0 by chance if every effect were null.

## R6 Permutation and placebo

| Statistic | Value |
|---|---|
| Observed GLM beta_gap (M1) | -0.1542 (t = -2.393) |
| Null distribution of beta*: mean, SD, 2.5% / 97.5% | -0.0136, 0.0819, -0.1641 / 0.1447 |
| Permutation p, two-sided / one-sided (studentized) | 0.0375 / 0.9770 |
| Permutation p, coefficient-based two-sided | 0.0535 |
| Placebo M1-PL beta_gap: Bayes / GLM | -0.042 [-0.156, 0.071] / -0.051 [-0.178, 0.076] {-0.157, 0.055} |
| ratio_gap (PL / P) | 0.275 -> Q3 pass |
| Pick calibration: M2-PL beta_lpd, ratio_pick | -0.080 [-0.179, 0.016], 0.479 (C3 reference about 0.37) |

## R7 Out-of-sample

| Table | Item | Mean log loss | Mean Brier | Columns |
|---|---|---|---|---|
| information sets | I0 | 0.27814 | 0.077561 | 21 |
| information sets | I1 | 0.2828 | 0.078204 | 28 |
| information sets | I2 | 0.293 | 0.08068 | 44 |
| information sets | I3 | 0.28354 | 0.078291 | 30 |
| information sets | I4 | 0.29509 | 0.081159 | 46 |
| contrast | I4 - I2 (tracking beyond club measures and pick) | 2.093 millinats/rep | [-0.829, 5.652] over repetitions | share < 0: 0.10 |
| contrast | I3 - I1 (tracking beyond pick and size) | 0.734 millinats/rep | [-0.777, 2.552] over repetitions | share < 0: 0.20 |
| contrast | I2 - I1 (stopwatch beyond pick and size, reference) | 10.193 millinats/rep | [6.347, 15.726] over repetitions | share < 0: 0.00 |
| leave-one-class-out | class 2023 | n test 4990; LL(I2) 0.30220; LL(I4) 0.31033 | dLL 8.131 millinats |  |
| leave-one-class-out | class 2024 | n test 4084; LL(I2) 0.29181; LL(I4) 0.29745 | dLL 5.644 millinats |  |
| leave-one-class-out | class 2025 | n test 2419; LL(I2) 0.26057; LL(I4) 0.26160 | dLL 1.030 millinats |  |
| leave-one-season-out | season 2023 | n test 431; LL(I2) 0.31092; LL(I4) 0.31176 | dLL 0.833 millinats |  |
| leave-one-season-out | season 2024 | n test 1821; LL(I2) 0.28459; LL(I4) 0.28363 | dLL -0.962 millinats |  |
| leave-one-season-out | season 2025 | n test 4962; LL(I2) 0.27477; LL(I4) 0.27563 | dLL 0.860 millinats |  |
| by-season GLM M1 | 2023 | beta_gap -0.164 [-1.495, 1.168] | n 431 | imprecise (431 reps) |
| by-season GLM M1 | 2024 | beta_gap -0.279 [-0.606, 0.047] | n 1821 |  |
| by-season GLM M1 | 2025 | beta_gap -0.101 [-0.252, 0.050] | n 4962 |  |

## R8 Sensitivities

| ID | Description | Reps | Blockers / rushers | GLM beta_gap [95% CI] | Bayes beta_gap [95%] | Discordant? |
|---|---|---|---|---|---|---|
| SA1 | 1.25 yd / 4 frames (double-team flag recomputed) | 6394 | 69 / 97 | -0.198 [-0.355, -0.042] {-0.329, -0.068} | -0.200 [-0.341, -0.055] | no |
| SA2 | 2.0 yd / 4 frames (double-team flag recomputed) | 8924 | 70 / 97 | -0.139 [-0.288, 0.010] {-0.263, -0.015} | -0.128 [-0.269, 0.012] | no |
| SA3 | 1.5 yd / 3 frames (double-team flag recomputed) | 7448 | 70 / 97 | -0.157 [-0.314, -0.001] {-0.288, -0.027} | -0.155 [-0.299, -0.007] | no |
| SA4 | 1.5 yd / 6 frames (double-team flag recomputed) | 6643 | 69 / 97 | -0.180 [-0.342, -0.018] {-0.315, -0.045} | -0.179 [-0.321, -0.036] | no |
| SA5 | REG only | 6867 | 68 / 97 | -0.140 [-0.296, 0.015] {-0.270, -0.011} | -0.139 [-0.285, 0.011] | no |
| SA6 | Exclude double teams | 6261 | 68 / 96 | -0.165 [-0.335, 0.006] {-0.307, -0.022} | -0.158 [-0.308, -0.005] | no |
| SA7 | Rushers with NFL position DE/DT/NT | 5326 | 69 / 71 | -0.152 [-0.356, 0.052] {-0.322, 0.018} | -0.157 [-0.346, 0.029] | no |
| SA9 | One pair per (game, play, blocker), smallest min_dist | 7000 | 69 / 97 | -0.162 [-0.329, 0.004] {-0.301, -0.024} | -0.157 [-0.308, -0.013] | no |
| SA15 | Complete cases for the dash (both players have a forty) | 4742 | 57 / 77 | -0.160 [-0.357, 0.038] {-0.325, 0.005} | -0.158 [-0.327, 0.012] | no |
| SA8 | Dyad-equal weighting w = (N / D) / n_dyad (GLM only) | 7214 | 69 / 97 | -0.120 [-0.341, 0.102] {-0.304, 0.065} | (GLM only) | no |
| SA10 | Composite B | 8087 | 79 / 97 | -0.104 [-0.265, 0.058] {-0.238, 0.031} | -0.102 [-0.233, 0.033] | no |
| SA11 | Composite A on the rows of P (common sample) | 7214 | 69 / 97 | -0.134 [-0.303, 0.035] {-0.275, 0.007} | -0.131 [-0.278, 0.022] | no |
| SA12 | DL-only: rusher composite replaces gap | 8087 | 79 / 97 | -0.060 [-0.234, 0.115] {-0.205, 0.086} | -0.042 [-0.197, 0.125] | yes |
| SA13 | 5-frame smoothing composites (O3, D1 at k=5) | 7214 | 69 / 97 | -0.085 [-0.259, 0.089] {-0.230, 0.060} | -0.074 [-0.227, 0.083] | yes |
| SA14 | No dropback spline | 7214 | 69 / 97 | -0.107 [-0.243, 0.029] {-0.220, 0.006} | -0.099 [-0.239, 0.044] | no |
| SA16 | M2 plus s_lpick (pick asymmetry) | 7214 | 69 / 97 | -0.138 [-0.307, 0.031] {-0.279, 0.003} | -0.128 [-0.277, 0.025] | no |
| SA17 | M1 plus dyad random intercept | 7214 | 69 / 97 | -0.154 [-0.308, 0.000] {-0.283, -0.026} | -0.146 [-0.294, 0.004] | no |
| SA18_0.5 | beta_gap prior Normal(0, 0.5) | 7214 | 69 / 97 | -0.154 [-0.308, 0.000] {-0.283, -0.026} | -0.149 [-0.298, 0.005] | no |
| SA18_2.5 | beta_gap prior Normal(0, 2.5) | 7214 | 69 / 97 | -0.154 [-0.308, 0.000] {-0.283, -0.026} | -0.152 [-0.301, -0.006] | no |

## R9 Selection

| Check | Result |
|---|---|
| SC1 composite OL, in-P vs out-of-P | n 69/36; mean difference 0.285 [-0.129, 0.743]; KS p 0.243 |
| SC1 log_pick OL, in-P vs out-of-P | n 69/36; mean difference -1.199 [-1.463, -0.967]; KS p 0.000 |
| SC1 ngs_athleticism_score OL, in-P vs out-of-P | n 69/36; mean difference 6.827 [2.933, 10.674]; KS p 0.020 |
| SC1 composite DL, in-P vs out-of-P | n 97/21; mean difference 0.128 [-0.389, 0.651]; KS p 0.904 |
| SC1 log_pick DL, in-P vs out-of-P | n 97/21; mean difference -0.757 [-0.974, -0.551]; KS p 0.000 |
| SC1 ngs_athleticism_score DL, in-P vs out-of-P | n 97/21; mean difference 7.293 [3.123, 11.660]; KS p 0.015 |
| SC1 the excluded engaged blockers vs the included | 10 blockers, 873 engaged reps; mean log pick 3.704 vs 4.272; NGS 78.2 vs 77.9; % missing forty 40.0 vs 17.4 |
| SC2 gap -> engaged: GLM [95% CI] | -0.034 [-0.113, 0.044] {-0.100, 0.031} (n 25005) -> not flagged |
| SC3a all-pairs gap | -0.080 [-0.200, 0.039] {-0.180, 0.019}; engaged_primary 0.001 [-0.112, 0.115] {-0.093, 0.096} (n 25005) |
| SC3b gap, engaged, gap x engaged | -0.084 [-0.207, 0.039] {-0.187, 0.018}; 0.001 [-0.114, 0.116] {-0.095, 0.096}; 0.013 [-0.098, 0.124] {-0.080, 0.105} |
| SC4 IPW-weighted M1 gap | -0.178 [-0.352, -0.005] {-0.323, -0.034} (weights 0.74-14.49) |

## R10 Variance components and ratings

| Item | Value |
|---|---|
| M1 sigma_B | 0.259 [0.094, 0.427] |
| M1 sigma_R | 0.283 [0.044, 0.501] |
| M2 sigma_B | 0.269 [0.102, 0.433] |
| M2 sigma_R | 0.275 [0.029, 0.479] |
| R sigma_B | 0.223 [0.064, 0.368] |
| R sigma_R | 0.290 [0.131, 0.452] |
| blocker top 10: nfl_id 55924 (192 reps) | 0.414 [0.036, 0.853] (90%) |
| blocker top 10: nfl_id 55930 (117 reps) | 0.236 [-0.062, 0.623] (90%) |
| blocker top 10: nfl_id 55891 (255 reps) | 0.216 [-0.047, 0.538] (90%) |
| blocker top 10: nfl_id 58220 (188 reps) | 0.168 [-0.121, 0.519] (90%) |
| blocker top 10: nfl_id 57299 (50 reps) | 0.147 [-0.182, 0.549] (90%) |
| blocker top 10: nfl_id 56066 (131 reps) | 0.136 [-0.166, 0.499] (90%) |
| blocker top 10: nfl_id 58209 (126 reps) | 0.133 [-0.153, 0.460] (90%) |
| blocker top 10: nfl_id 57183 (169 reps) | 0.131 [-0.146, 0.456] (90%) |
| blocker top 10: nfl_id 55874 (244 reps) | 0.128 [-0.135, 0.426] (90%) |
| blocker top 10: nfl_id 57128 (192 reps) | 0.122 [-0.151, 0.438] (90%) |
| blocker bottom 10: nfl_id 55878 (188 reps) | -0.131 [-0.431, 0.137] (90%) |
| blocker bottom 10: nfl_id 57224 (77 reps) | -0.134 [-0.473, 0.168] (90%) |
| blocker bottom 10: nfl_id 57330 (99 reps) | -0.138 [-0.490, 0.165] (90%) |
| blocker bottom 10: nfl_id 55973 (264 reps) | -0.143 [-0.424, 0.111] (90%) |
| blocker bottom 10: nfl_id 58454 (77 reps) | -0.143 [-0.526, 0.180] (90%) |
| blocker bottom 10: nfl_id 58359 (33 reps) | -0.147 [-0.563, 0.187] (90%) |
| blocker bottom 10: nfl_id 58416 (9 reps) | -0.153 [-0.594, 0.205] (90%) |
| blocker bottom 10: nfl_id 58226 (116 reps) | -0.162 [-0.502, 0.119] (90%) |
| blocker bottom 10: nfl_id 57374 (90 reps) | -0.169 [-0.530, 0.125] (90%) |
| blocker bottom 10: nfl_id 58358 (91 reps) | -0.217 [-0.607, 0.096] (90%) |
| rusher top 10: nfl_id 57156 (173 reps) | 0.414 [0.064, 0.792] (90%) |
| rusher top 10: nfl_id 58362 (147 reps) | 0.341 [-0.012, 0.729] (90%) |
| rusher top 10: nfl_id 55947 (278 reps) | 0.317 [0.010, 0.633] (90%) |
| rusher top 10: nfl_id 55942 (215 reps) | 0.295 [-0.011, 0.622] (90%) |
| rusher top 10: nfl_id 57160 (344 reps) | 0.284 [0.002, 0.582] (90%) |
| rusher top 10: nfl_id 56497 (222 reps) | 0.281 [-0.059, 0.651] (90%) |
| rusher top 10: nfl_id 57142 (146 reps) | 0.276 [-0.057, 0.645] (90%) |
| rusher top 10: nfl_id 57159 (157 reps) | 0.242 [-0.107, 0.631] (90%) |
| rusher top 10: nfl_id 55867 (273 reps) | 0.234 [-0.070, 0.558] (90%) |
| rusher top 10: nfl_id 55879 (264 reps) | 0.232 [-0.064, 0.555] (90%) |
| rusher bottom 10: nfl_id 57169 (207 reps) | -0.184 [-0.558, 0.153] (90%) |
| rusher bottom 10: nfl_id 57334 (64 reps) | -0.186 [-0.625, 0.199] (90%) |
| rusher bottom 10: nfl_id 58369 (75 reps) | -0.199 [-0.665, 0.218] (90%) |
| rusher bottom 10: nfl_id 55918 (335 reps) | -0.211 [-0.530, 0.085] (90%) |
| rusher bottom 10: nfl_id 55995 (90 reps) | -0.212 [-0.689, 0.204] (90%) |
| rusher bottom 10: nfl_id 58318 (50 reps) | -0.241 [-0.728, 0.187] (90%) |
| rusher bottom 10: nfl_id 58348 (57 reps) | -0.252 [-0.746, 0.175] (90%) |
| rusher bottom 10: nfl_id 58282 (45 reps) | -0.259 [-0.734, 0.163] (90%) |
| rusher bottom 10: nfl_id 55974 (96 reps) | -0.268 [-0.727, 0.110] (90%) |
| rusher bottom 10: nfl_id 57148 (122 reps) | -0.383 [-0.888, 0.020] (90%) |

## R11 Verdict sentence

On 7214 engaged NFL pass-protection reps (69 blockers, 97 rushers), the athletic gap (rusher minus blocker) went with *less* pressure: -0.153 [-0.299, -0.005] log-odds per SD of the gap, about -1.06 percentage points per rep, equivalent to -0.90 SDs of draft-pick difference, beyond both players' size, stopwatch times and NGS athleticism score. Label: Opposite (qualified: Q1); Q4 failed (discordant: SA12, SA13). With draft slot also controlled (pre-registered secondary): Inconclusive, -0.125 [-0.273, 0.025]. With the 40-yard acceleration shape added to the composite (pre-registered secondary S0): Opposite, -0.154 [-0.288, -0.022]. Note: discordant sensitivities: SA12, SA13.
