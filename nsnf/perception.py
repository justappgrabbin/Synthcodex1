"""User-defined dimensional perception rule, separate from HD channel taxonomy.

An expression is represented here by an activity-connected group of components.
Only edges that actually carried messages in this run establish that grouping.
This graph mapping is an engineering convention, not a completed HD mechanism.
"""
from .topology import aggregate

RULE_VERSION = "three-dimensions-including-current-v1"


def eligibility(dimensions, current):
    """Public dimensions are 1..5; prior is ordered inclusively through current."""
    if type(current) is not int or current not in (3, 4, 5):
        raise ValueError("perception target must be dimension 3, 4 or 5")
    if any(type(d) is not int or not 1 <= d <= 5 for d in dimensions):
        raise ValueError("expression dimensions must be integers 1..5")
    expressed = sorted(set(dimensions))
    prior = [d for d in expressed if d <= current]
    present = current in prior
    count = len(prior)
    permitted = present and count >= 3
    reason = ("current dimension has no expression" if not present else
              "fewer than three expressed dimensions including current" if count < 3 else
              "at least three expressed dimensions including current")
    return {"current_dimension": current, "expressed_dimensions": expressed,
            "counted_dimensions": prior, "excluded_later_dimensions": [d for d in expressed if d > current],
            "current_included": present, "distinct_count": count, "minimum": 3,
            "perceptible": permitted, "reason": reason, "rule_version": RULE_VERSION}


def perceive(micro, messages):
    edges = [{"src": m["src"], "dst": m["dst"]} for m in messages]
    meso, _ = aggregate(micro, edges)
    expressions = []
    for group in meso["groups"]:
        dimensions = sorted({int(node.split(":")[0][1:]) + 1 for node in group["members"]})
        expressions.append({"members": group["members"], "state": group["state"],
                            "dimensions": dimensions,
                            "decisions": [eligibility(dimensions, d) for d in (3, 4, 5)]})
    outputs = {}
    for current in (3, 4, 5):
        accepted = [e for e in expressions if e["decisions"][current - 3]["perceptible"]]
        # Only qualified expressions participate in this dimension's perceived output.
        outputs[str(current)] = ([sum(e["state"][i] for e in accepted) / len(accepted) for i in range(2)]
                                 if accepted else None)
    return {"rule_version": RULE_VERSION, "authority": "user clarification in this conversation",
            "dimension_numbering": "1..5; internal component d0 is dimension 1",
            "expression_mapping": "connected components of actual run messages; engineering convention",
            "prior_convention": "dimensions up to and including current; later dimensions excluded",
            "expressions": expressions, "perceived_outputs": outputs}
