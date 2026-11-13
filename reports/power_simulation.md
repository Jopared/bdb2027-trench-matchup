# Power / minimum-detectable-effect simulation (step 3 of the pre-registered design)

Code: `scripts/power_simulation.py` (seed 2027; reproduce with `.venv\Scripts\python.exe scripts\power_simulation.py`). Simulations per setting: 500. Runtime 14.4 min. `data/processed/engaged_outcomes_SEALED.parquet` was **not opened**; every outcome here is simulated. Labels: **[computed]** = from the real design matrix or the simulation; **[assumption]** = a generator input.

## 1. Analysis set [computed]

Primary engaged reps; blocker lined up T/G/C and combine_position OL; rusher combine_position DL aligned EDGE or INTERIOR_LINE (section 3.3); both players with the composite.

| composite | reps | REG reps | blockers | rushers | dyads | dyads with >=2 reps | design columns | top-10 blockers' share | corr(gap, pick diff) |
|---|---|---|---|---|---|---|---|---|---|
| registered | 7,214 | 6,867 | 69 | 97 | 1201 | 958 | 32 (incl. intercept and gap) | 0.351 | -0.020 |
| sensA | 7,720 | 7,297 | 75 | 97 | 1281 | 1028 | 32 (incl. intercept and gap) | 0.328 | 0.029 |

Design (section 3.4): intercept; natural cubic spline (3 df) of dropback_duration; down (1, 2, 3+) x yards-to-go bucket (<=3, 4-7, 8+); shotgun; play action; season; blocker position T/G/C; rusher EDGE vs interior; double team; pass_rushers_encountered; rusher-minus-blocker differences of log pick, undrafted flag, weight, arm length, forty, ten-yard split, short shuttle, NGS athleticism and the corresponding missing flags (continuous columns standardised on the analysis-set players, missing values set to 0 after standardising); gap = rusher composite - blocker composite, standardised to SD 1. Constant and exactly duplicated columns are dropped (the forty and ten-yard-split missing-flag differences are identical in this set). The dropback spline is a restricted (natural) cubic spline with 3 df (linear term plus two nonlinear terms, knots at the 5/35/65/95th percentiles; a hand-built Harrell basis because patsy's `cr` basis put almost all its mass on one outlier rep) - **[decision]**. Down 4 is merged into 3+ and the yards-to-go cut points are my choices (section 3.3 does not give them) - **[decision]**.

Engine check on one null draw, my numpy IRLS + two-way cluster SE vs statsmodels GLM `cov_type=cluster` (blocker, rusher): gap estimate -0.02931 vs -0.02931; SE 0.04228 vs 0.04228.

## 2. Generator

- Logistic, `logit P = a + (-0.20) * pickdiff_z + 0.58 * dropback_z + gap_effect * gap_z + u_blocker + u_rusher` **[assumption: coefficients from the feasibility check; no other covariate has an effect]**. pickdiff_z = standardised rusher-minus-blocker log pick; dropback_z = standardised dropback_duration.
- u_blocker, u_rusher ~ N(0, s^2), crossed; s = 0.35 (main), 0.20 and 0.50 (sensitivity) **[assumption]**. Intercept `a` solved so the mean simulated rate is 0.0952 (averaged over 300 random-effect draws) **[computed from the assumed base rate]**.
- Fit: the frequentist mirror, logistic GLM with the full fixed-effect design, two-way cluster-robust SE (blocker + rusher - dyad, statsmodels-style small-sample factors, eigenvalue-clipped only if the gap variance is non-positive); Wald z test at two-sided alpha = 0.05. The fitted model uses a spline for dropback while the generator is linear in dropback, so misspecification is slight but present.

## 3. Power table, random-effect SD 0.35 (main) [computed]

Power = share of simulations with |z| > 1.96. Effect 0 row is the type-I error rate. Bias = mean estimate - planted; SE columns: empirical SD of estimates and mean model-based cluster SE.

### Standard (reps equally weighted)

| planted effect (log-odds/SD) | power: registered | power: sensA | bias: registered | bias: sensA | empirical SD: reg. | mean cluster SE: reg. | empirical SD: sensA | mean cluster SE: sensA | 95% CI coverage: reg. | sensA |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 0.118 | 0.104 | -0.0020 | -0.0021 | 0.0816 | 0.0683 | 0.0734 | 0.0616 | 0.882 | 0.896 |
| 0.10 | 0.352 | 0.378 | -0.0028 | -0.0046 | 0.0833 | 0.0685 | 0.0803 | 0.0611 | 0.888 | 0.856 |
| 0.15 | 0.562 | 0.640 | -0.0031 | -0.0038 | 0.0845 | 0.0675 | 0.0743 | 0.0622 | 0.872 | 0.878 |
| 0.20 | 0.776 | 0.840 | -0.0034 | -0.0046 | 0.0836 | 0.0674 | 0.0733 | 0.0615 | 0.856 | 0.886 |
| 0.30 | 0.974 | 0.992 | -0.0070 | -0.0049 | 0.0790 | 0.0675 | 0.0758 | 0.0630 | 0.904 | 0.878 |
| 0.40 | 0.998 | 1.000 | -0.0050 | -0.0086 | 0.0849 | 0.0665 | 0.0727 | 0.0621 | 0.862 | 0.892 |
| 0.50 | 1.000 | 1.000 | -0.0125 | -0.0056 | 0.0840 | 0.0669 | 0.0795 | 0.0624 | 0.860 | 0.862 |

n reps in this variant: registered 7,214, sensA 7,720.

### Dyad-equal weights

| planted effect (log-odds/SD) | power: registered | power: sensA | bias: registered | bias: sensA | empirical SD: reg. | mean cluster SE: reg. | empirical SD: sensA | mean cluster SE: sensA | 95% CI coverage: reg. | sensA |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 0.124 | 0.100 | -0.0044 | +0.0008 | 0.1020 | 0.0860 | 0.0867 | 0.0766 | 0.876 | 0.900 |
| 0.10 | 0.260 | 0.284 | -0.0017 | -0.0056 | 0.0994 | 0.0852 | 0.0892 | 0.0756 | 0.902 | 0.892 |
| 0.15 | 0.422 | 0.494 | -0.0015 | +0.0003 | 0.0995 | 0.0845 | 0.0852 | 0.0773 | 0.900 | 0.920 |
| 0.20 | 0.640 | 0.678 | -0.0024 | -0.0022 | 0.0979 | 0.0850 | 0.0883 | 0.0769 | 0.894 | 0.888 |
| 0.30 | 0.886 | 0.948 | -0.0070 | -0.0026 | 0.0937 | 0.0854 | 0.0864 | 0.0774 | 0.918 | 0.910 |
| 0.40 | 0.986 | 0.996 | -0.0066 | -0.0041 | 0.0970 | 0.0837 | 0.0851 | 0.0765 | 0.920 | 0.912 |
| 0.50 | 0.998 | 1.000 | -0.0052 | -0.0045 | 0.0978 | 0.0833 | 0.0899 | 0.0778 | 0.886 | 0.894 |

n reps in this variant: registered 7,214, sensA 7,720.

### REG-only reps

| planted effect (log-odds/SD) | power: registered | power: sensA | bias: registered | bias: sensA | empirical SD: reg. | mean cluster SE: reg. | empirical SD: sensA | mean cluster SE: sensA | 95% CI coverage: reg. | sensA |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 0.122 | 0.120 | -0.0023 | -0.0018 | 0.0831 | 0.0688 | 0.0742 | 0.0619 | 0.878 | 0.880 |
| 0.10 | 0.354 | 0.390 | -0.0032 | -0.0045 | 0.0846 | 0.0689 | 0.0812 | 0.0614 | 0.882 | 0.846 |
| 0.15 | 0.552 | 0.628 | -0.0032 | -0.0033 | 0.0853 | 0.0682 | 0.0742 | 0.0627 | 0.870 | 0.890 |
| 0.20 | 0.774 | 0.838 | -0.0032 | -0.0043 | 0.0846 | 0.0678 | 0.0732 | 0.0621 | 0.862 | 0.888 |
| 0.30 | 0.968 | 0.990 | -0.0071 | -0.0047 | 0.0804 | 0.0680 | 0.0757 | 0.0634 | 0.898 | 0.886 |
| 0.40 | 0.996 | 1.000 | -0.0045 | -0.0088 | 0.0865 | 0.0668 | 0.0744 | 0.0625 | 0.846 | 0.874 |
| 0.50 | 1.000 | 1.000 | -0.0116 | -0.0050 | 0.0850 | 0.0674 | 0.0805 | 0.0629 | 0.854 | 0.854 |

n reps in this variant: registered 6,867, sensA 7,297.

### Test calibration (standard weighting, RE SD 0.35) [computed]

The cluster-robust Wald test with ~70 blockers and ~97 rushers is anti-conservative: the mean model SE is below the empirical SD of the estimate. Rows show the type-I rate at effect 0 and power with (i) the test as specified, (ii) a t reference with min(G)-1 df, (iii) size-adjusted power (critical value = 95th percentile of |z| in the null simulations; not an available test in practice, a bound on what a calibrated test could do).

| planted effect | reg. as specified | reg. t-ref | reg. size-adjusted | sensA as specified | sensA t-ref | sensA size-adjusted |
|---|---|---|---|---|---|---|
| 0.00 | 0.118 | 0.114 | 0.050 | 0.104 | 0.102 | 0.050 |
| 0.10 | 0.352 | 0.346 | 0.260 | 0.378 | 0.372 | 0.244 |
| 0.15 | 0.562 | 0.552 | 0.428 | 0.640 | 0.632 | 0.458 |
| 0.20 | 0.776 | 0.774 | 0.674 | 0.840 | 0.834 | 0.716 |
| 0.30 | 0.974 | 0.970 | 0.942 | 0.992 | 0.990 | 0.964 |
| 0.40 | 0.998 | 0.996 | 0.992 | 1.000 | 1.000 | 1.000 |
| 0.50 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## 4. Minimum detectable effect at 80% power [computed]

Interpolated linearly on the simulated power curve (planted-effect grid 0, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50). Draft-pick equivalents = MDE / 0.20. Probability change = expit(logit(0.0952) + MDE) - 0.0952 for a +1 SD gap, at the base rate. The analytic approximation 2.80 x mean cluster SE (at planted 0.20) is shown as a cross-check.

| composite | variant | RE SD | MDE (log-odds/SD), test as specified (normal ref.) | method | draft-pick equivalents (SD of pick diff) | pressure prob. change at base rate (points) | 2.80 x mean SE | MDE with t(G-1) reference | MDE size-adjusted (null 95th pct of abs z) |
|---|---|---|---|---|---|---|---|---|---|
| registered | standard | 0.35 | 0.212 | interpolated | 1.06 | 1.99 | 0.189 | 0.213 | 0.247 |
| registered | standard | 0.2 | 0.168 | interpolated | 0.84 | 1.55 | 0.149 | 0.169 | 0.176 |
| registered | standard | 0.5 | 0.275 | interpolated | 1.37 | 2.64 | 0.233 | 0.278 | 0.333 |
| registered | dyad-weighted | 0.35 | 0.265 | interpolated | 1.33 | 2.54 | 0.238 | 0.269 | 0.306 |
| registered | dyad-weighted | 0.2 | 0.226 | interpolated | 1.13 | 2.13 | 0.209 | 0.228 | 0.242 |
| registered | dyad-weighted | 0.5 | 0.291 | interpolated | 1.46 | 2.82 | 0.268 | 0.294 | 0.369 |
| registered | REG only | 0.35 | 0.213 | interpolated | 1.07 | 2.00 | 0.190 | 0.216 | 0.249 |
| registered | REG only | 0.2 | 0.169 | interpolated | 0.84 | 1.55 | 0.151 | 0.171 | 0.179 |
| registered | REG only | 0.5 | 0.277 | interpolated | 1.39 | 2.67 | 0.234 | 0.280 | 0.336 |
| sensA | standard | 0.35 | 0.190 | interpolated | 0.95 | 1.77 | 0.172 | 0.192 | 0.234 |
| sensA | standard | 0.2 | 0.146 | interpolated | 0.73 | 1.34 | 0.139 | 0.148 | 0.178 |
| sensA | standard | 0.5 | 0.256 | interpolated | 1.28 | 2.44 | 0.217 | 0.258 | 0.288 |
| sensA | dyad-weighted | 0.35 | 0.245 | interpolated | 1.23 | 2.33 | 0.215 | 0.246 | 0.264 |
| sensA | dyad-weighted | 0.2 | 0.205 | interpolated | 1.02 | 1.91 | 0.191 | 0.208 | 0.238 |
| sensA | dyad-weighted | 0.5 | 0.274 | interpolated | 1.37 | 2.64 | 0.247 | 0.277 | 0.310 |
| sensA | REG only | 0.35 | 0.191 | interpolated | 0.95 | 1.78 | 0.174 | 0.192 | 0.236 |
| sensA | REG only | 0.2 | 0.149 | interpolated | 0.75 | 1.36 | 0.141 | 0.150 | 0.173 |
| sensA | REG only | 0.5 | 0.256 | interpolated | 1.28 | 2.44 | 0.217 | 0.258 | 0.287 |

## 5. Random-effect SD sensitivity (standard weighting) [computed under assumed SDs]

| planted effect | reg. power SD 0.35 | reg. power SD 0.2 | reg. power SD 0.5 | sensA power SD 0.35 | sensA power SD 0.2 | sensA power SD 0.5 |
|---|---|---|---|---|---|---|
| 0.00 | 0.118 | 0.090 | 0.144 | 0.104 | 0.112 | 0.108 |
| 0.10 | 0.352 | 0.482 | 0.266 | 0.378 | 0.502 | 0.290 |
| 0.15 | 0.562 | 0.730 | 0.438 | 0.640 | 0.824 | 0.456 |
| 0.20 | 0.776 | 0.926 | 0.560 | 0.840 | 0.958 | 0.650 |
| 0.30 | 0.974 | 1.000 | 0.882 | 0.992 | 1.000 | 0.918 |
| 0.40 | 0.998 | 1.000 | 0.988 | 1.000 | 1.000 | 0.994 |
| 0.50 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

| composite | RE SD | MDE | pick equivalents | empirical SD of gap estimate (at effect 0) | bias at effect 0.20 |
|---|---|---|---|---|---|
| registered | 0.35 | 0.212 | 1.06 | 0.0816 | -0.0034 |
| registered | 0.2 | 0.168 | 0.84 | 0.0626 | +0.0006 |
| registered | 0.5 | 0.275 | 1.37 | 0.1120 | -0.0171 |
| sensA | 0.35 | 0.190 | 0.95 | 0.0734 | -0.0046 |
| sensA | 0.2 | 0.146 | 0.73 | 0.0567 | +0.0015 |
| sensA | 0.5 | 0.256 | 1.28 | 0.0910 | -0.0114 |

## 6. Continuous secondary outcome (peak pressure probability allowed): ASSUMPTION-BASED

The real distribution is unknown to me, so this is **not** a computed property of the data. Assumed: outcome mean 0.25, total SD 0.20 on the probability scale; blocker and rusher random-intercept SDs 0.05 each (assumed ICC about 6% per side), the rest independent residual; no other covariate effects planted. Fit: OLS with the full fixed-effect design and two-way cluster-robust SE. Effects are in probability units per SD of the gap.

| planted effect (prob. per SD of gap) | power: registered | power: sensA | mean SE: registered | mean SE: sensA |
|---|---|---|---|---|
| 0.000 | 0.132 | 0.100 | 0.0078 | 0.0071 |
| 0.005 | 0.176 | 0.162 | 0.0078 | 0.0072 |
| 0.010 | 0.328 | 0.316 | 0.0078 | 0.0071 |
| 0.015 | 0.458 | 0.544 | 0.0078 | 0.0072 |
| 0.020 | 0.724 | 0.738 | 0.0078 | 0.0071 |
| 0.030 | 0.922 | 0.948 | 0.0078 | 0.0071 |
| 0.040 | 0.992 | 0.998 | 0.0078 | 0.0070 |

- registered: MDE (80% power) = 0.0238 probability units per SD of gap (interpolated), i.e. 0.119 outcome SDs per gap SD. [assumption-based]
- sensA: MDE (80% power) = 0.0230 probability units per SD of gap (interpolated), i.e. 0.115 outcome SDs per gap SD. [assumption-based]

## 7. What the design can and cannot detect

- With the registered composite and RE SD 0.35 the design has 80% power for a gap effect of about **0.21 log-odds per SD** (1.1 draft-pick-difference SDs; a +1 SD gap raises pressure probability from 9.52% by about 2.0 points). For sensitivity composite A: 0.19. These MDEs depend on the assumed random-effect SD: 0.17 at SD 0.2 and 0.27 at SD 0.5 (registered).
- Dyad-equal weighting and REG-only reps are less powerful or similar: MDE 0.27 and 0.21 (registered).
- Interpretation of a null: an interval that excludes effects larger than the MDE is the most that can be claimed; effects smaller than the MDE (for example the planted 0.10) are mostly missed, and the power table gives the exact miss rate. The effective sample size is driven by the 69 (sensA: 75) blockers and 97 rushers (the cluster count), not by the thousands of reps, because the gap varies at the player level; this is why the MDE is large relative to the pick effect.
- **Test size:** the as-specified two-way cluster Wald test rejects a true null in about 12% (registered) and 10% (sensA) of simulations at nominal 5%, because the cluster SE is about 15-20% too small with this few clusters (the t reference barely helps). The as-specified MDE (0.21 registered) is therefore optimistic; the size-adjusted MDE (0.25 registered, 0.23 sensA, i.e. 1.2 draft-pick SDs) is the honest planning number, and the preregistered decision rule should use a calibrated test (permutation, wild/cluster bootstrap) or the Bayesian interval rather than the plain cluster Wald z.
- Caveats: the generator is a simplified logistic model with assumed REs and only two non-zero nuisance effects; the Wald test uses the normal reference with few clusters, so type-I error and coverage (see table) should be read from the effect-0 row; the Bayesian primary model (priors, shrinkage) will not have identical power to this frequentist mirror; the continuous-outcome section is assumption-based throughout.
