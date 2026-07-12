---
source_handle: nist-cusum
fetched: 2026-07-11
source_url: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm
provenance: source-direct
---

## Summary

NIST/SEMATECH e-Handbook of Statistical Methods §6.3.2.3, "Cusum Control Charts". CUSUM
accumulates deviations from a target mean (S_m = Σ(x̄_i − μ̂_0)) so that small persistent shifts —
which a per-point Shewhart chart misses — pile up and cross a decision threshold. The tabular form
signals when either one-sided cumulative statistic exceeds a decision limit h (with reference
value k). The design vocabulary is the average run length (ARL): high ARL when in control (few
false alarms), low ARL after a real shift (fast detection). Relevance to legacy-engine: CUSUM is
the classic sequential detector for the drift-alarm half of the epic (flag a disturbance within a
week or two of it starting), and the ARL framing is the honest way to state the alarm's
false-positive/latency trade.

## Key passages

- §6.3.2.3: "CUSUM charts … have been shown to be more efficient in detecting small shifts in the
  mean of a process" and "they are better than Shewhart control charts when it is desired to
  detect shifts in the mean that are 2 sigma or less."
- §6.3.2.3: the chart plots "S_m = Σ_{i=1}^m (x̄_i − μ̂_0)" (or the standardized S'_m).
- Tabular form: "When either S_hi(i) and S_lo(i) exceeds h, the process is out of control."
- ARL page (pmc3231.htm, same chapter): "The average run length (ARL) at a given quality level is
  the average number of samples (subgroups) taken before an action signal is given." and "We would
  like to see a high ARL, L₀, when the process is on target, (i.e. in control), and a low ARL, L₁,
  when the process mean shifts to an unsatisfactory level."
