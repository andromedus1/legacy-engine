---
source_handle: recurrent-consume-cluster-inference
fetched: 2026-08-13
source_url: https://escholarship.org/uc/item/1jq5d0pq
provenance: source-direct
substrate_confidence: source-direct
source_class: primary-paper
---

# Cameron and Miller — A Practitioner's Guide to Cluster-Robust Inference

## Summary

Cameron and Miller analyze inference when observations are grouped into clusters with dependence
within clusters and independence across clusters. Their review shows why observation count alone
can overstate precision, discusses how the clustering level should follow the dependence process,
and emphasizes that conventional cluster-robust approximations are unreliable with few clusters.

## Key passages

1. The paper's abstract frames the setting as regression errors correlated within groups but
   independent across groups and states that default standard errors can substantially overstate
   precision.
2. Section IV treats “What to cluster over?” as a substantive modeling decision rather than a
   mechanical choice.
3. Section VI identifies two few-cluster problems: downward-biased cluster-robust variance
   estimates and over-rejection / intervals that are too narrow under conventional critical
   values.
4. The authors state that there is no universal count at which “few clusters” stops being a
   concern; performance depends on the data and model, so more clusters are preferable.

## Structural metadata

A. Colin Cameron and Douglas L. Miller, *Journal of Human Resources* 50(2), 2015, pp. 317–372.
The eScholarship record links the published DOI `10.3368/jhr.50.2.317` and sections on cluster
choice and few clusters.
