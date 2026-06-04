---
id: idea-custom-field-counts-and-normalization
created: 2026-06-04
tags: [advisory]
---

Two custom-field issues: (1) a custom field is share-only (counts=None), so positioning can't model field-share uncertainty the way a corpus-derived field can — allow supplying counts or a confidence per row; (2) partial-sum fields renormalize to 1.0, silently redistributing the unspecified 'Other' mass onto named decks (top-12 summing to 49% doubled every share), which materially shifts field-weighted means. Make the renormalization consequence explicit, or support an explicit Other/unspecified bucket.
