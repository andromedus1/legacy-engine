# Decomposition rationale — recurrent stable-era intervals

## Candidate 1: method families

- Recurrent-state models such as hidden-state or switching models.
- Change-point segmentation followed by segment-similarity clustering.
- Direct historical-window matching against the current deck population.

This cut makes algorithm comparison easy, but risks isolating discovery methods from the validity
and consumption contracts that determine whether recovered history is actually safe to use.

## Candidate 2: failure modes

- False reunion of superficially similar eras.
- Missed reunion of genuinely equivalent eras.
- Outcome-driven selection and multiple-testing bias.
- Sparse overlap, nonrandom scheduling, and event-concentration risk.

This cut foregrounds safety, but gives no natural owner to the positive end-to-end model or the
historical report selector.

## Candidate 3: lifecycle — chosen

- **Discover:** segment entity history and nominate older intervals similar to the current form.
- **Certify:** decide whether nominated intervals are transportable using outcome-free features and
  explicit statistical guards.
- **Consume and validate:** intersect subject/opponent interval sets, pool eligible matches, expose
  provenance, and test whether added coverage improves future decisions.

This cut maps directly to the system boundary and lets each candidate method be judged by the same
downstream safety contract.

## Comparative assessment

The method-family cut is strongest for literature coverage but weakest at integration. The
failure-mode cut is strongest for disconfirmation but can become a catalogue without a deliverable.
The lifecycle cut contains both: discovery compares methods, certification owns the failure modes,
and consumption makes the estimand and validation obligations explicit.

## Self-flag

The chosen decomposition assumes configuration equivalence is the primary transport criterion. An
identical deck can behave differently in a changed surrounding format, rules environment, or pilot
population. Pairwise subject/opponent interval intersection reduces but does not eliminate this
context-transport problem; certification and validation must test it rather than assume it away.

## Bracket framing

This engagement does not attempt to model individual pilot effects, causal card effects, or infer
historical legality from outcomes. It may therefore foreclose useful history whose transportability
depends on a richer latent context than deck composition and opponent configuration can represent.
