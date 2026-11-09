# Dimensional perception rule

The user's clarified model: perception in dimension 3, 4 or 5 requires expression in at least three dimensions, **including the current dimension**. Repetition in a dimension is not another dimension. This is implemented as `three-dimensions-including-current-v1`.

The channel produces the changing line; this change does not reverse that relationship or identify a changing line with a channel. It does not introduce a majority vote over gates or require the same line position to change in each dimension. Changing-line production itself is not implemented by this increment.

## Execution mapping

Public dimensions are numbered 1–5. Existing internal nodes `d0`–`d4` map to those dimensions without renumbering stored slots. “Prior including current” is implemented as dimensions up to and including the current numbered dimension. Later dimensions cannot satisfy an earlier dimension's requirement.

An expression is represented provisionally by a connected group of active nodes whose connections carried actual typed messages in the run. Unconnected activities are not pooled, even if their slot numbers match. Merely configuring an edge does not count as channel activity. The graph grouping is an explicit engineering convention; it does not establish Human Design channel semantics or nine-center emergence.

Each expression records its members, expressed dimensions, counted dimensions, excluded later dimensions, current-dimension presence, acceptance/block reason and rule version. Only qualifying expressions contribute to `perception.perceived_outputs` for dimensions 3, 4 and 5. No qualifying expression yields `null`, rather than fabricated perception.

Raw neural outputs remain available under the existing `output` field for diagnostic compatibility; they are not represented as perceived outputs. The UI distinguishes raw probabilities from dimensional perception. The decision is stored in state and execution records, versioned in cache keys, and checked in replay. Historical runs without the rule remain historical rather than acquiring an invented old decision.

## Examples

| Expressed dimensions in one related group | Perception dimension | Result |
|---|---|---|
| 1, 2, 3 | 3 | Perceptible: current is one of three |
| 2, 3 | 3 | Not perceptible: only two |
| 2, 3, 4 | 4 | Perceptible |
| 1, 3, 5 | 5 | Perceptible |
| 1, 2, 3 | 4 | Not perceptible: no expression in current dimension |
| 3, 4, 5 | 3 | Not perceptible: later dimensions do not count as prior |

Run `python -m nsnf.perception_demo` for real sparse neural execution showing the two-dimension blocked case, three-dimension accepted case, saved decision and exact replay. Tests exhaust all subsets of the five dimensions and cover unrelated activity, repeated dimensions, the HTTP path, restore and restart.
