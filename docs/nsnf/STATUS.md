# Capability ledger — 9 November 2026

This is an unfinished implementation of the cumulative specification. It is not a completed Cynthia/Synthia release. No feature has been USER-VERIFIED in this session.

| Capability | Status | Evidence and limit |
|---|---|---|
| 5 × 64 slots, separate codes/masks/parameters | TESTED | `tests/nsnf/test_core.py`, `evidence/nsnf/python-tests.txt` |
| Sparse execution and five budgets | TESTED | Real NumPy MLP computations; synthetic feature-salience router |
| Micro / meso / macro | TESTED as engineering hypothesis | Activity-connected groups and mean deviation, not verified nine-center emergence |
| Dimensional perception | TESTED | Three expressed dimensions including current; actual message-group mapping, stored decision, restart/replay, API and browser evidence |
| Nine emergent centers | SPECIFIED / UNRESOLVED | Legacy fixed gate buckets do not meet this requirement |
| Local parameter learning | TESTED on synthetic task | Disjoint held-out vectors; parameter deltas persisted |
| Transfer | TESTED on narrow synthetic task | Explicit parameter copy improves receiving model; no claim of general transfer learning |
| Typed message effects | TESTED | Receiving output changes; topology version persisted and replayed |
| SQLite history, checkpoints, restore, replay | TESTED | Append-only triggers, hash chain, corruption detection, competing writer rejection |
| Bounded contact investigation | CONNECTED / TESTED | Typed supplied observations → recent-observation retrieval → real field run → clarification → stored correction |
| Native acoustic input and artifact retrieval | TESTED | PCM WAV bytes → timed acoustic measurements → neural features → stored original/analysis; restart and browser tests pass |
| General contact understanding / conversation | SPECIFIED | Bounded workflow is not a general conversational model |
| Source address parser/comparison | IMPLEMENTED / TESTED | Lossless values and conservative sharing boundary; full semantics unresolved |
| Birth-derived address and exclusion | SPECIFIED / UNRESOLVED | Existing upstream providers preserved; legacy coordinates differ from v0.9 |
| Bantu relational kernel | SPECIFIED | Language-specific cited fixtures and rule packs still needed |
| Existing Computer integration | CONNECTED / TESTED | Optional service → live local API → actual MLP run → persisted Computer event; integration patch included |
| Diagnostic UI | IMPLEMENTED / CONNECTED through API | Desktop/mobile browser verification passed; checkpoint request method fixed |
| Code / image / video generation | SPECIFIED | No production adapters built or verified in this increment |
| Voice, listening, proactive speech | SPECIFIED for integration | Existing sources preserved; no device test performed |
| Personal understanding network | PARTIAL | Private single-owner store; shared network and ratified Base transformations absent |
| Comparative benchmark | TESTED, limited | Synthetic classification compute ablation; small dense baseline is faster than sparse field |
| Sequence recall / learned graph task / calibration | SPECIFIED | Required comparative benchmarks remain unfinished |
| AutoDev / emergent Space / acoustic analysis | SPECIFIED | Not built in this increment |

## Incomplete work

The full requested application remains unfinished. Required next work includes source-confirmed center and transition rules, language-specific morphology fixtures, production modality adapters, shared-user semantics, browser and device verification, and remaining comparative benchmarks. The source specification is retained locally and is not included in this public repository.

## Verified results

21 Python core/API/audio/perception tests passed; 13 original Computer test files passed after restoring declared dependencies; 1 real Computer-to-field integration test passed. The integration patch preserves upstream implementation and identifies its base commit. Synthetic held-out benchmark accuracy was 0.98 for all three variants; the small dense baseline was faster than the sparse field. See benchmark limitations.

Browser verification now passes using Playwright Chromium at desktop and mobile sizes, including actual WAV upload, playback URL and evidence retrieval. The prior approval-review usage limit has cleared. Audible-device and microphone tests remain pending.
