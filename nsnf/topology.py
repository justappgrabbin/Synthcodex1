from .schema import digest


def slots():
    return [{"id": f"d{d}:g{g}", "dimension_id": d, "slot": g,
             "binary_code": g, "numbering": "binary-slot-not-HD-gate"}
            for d in range(5) for g in range(64)]


def validate_edges(edges):
    valid = {s["id"] for s in slots()}
    seen = set()
    for edge in edges:
        pair = (edge["src"], edge["dst"])
        if pair[0] not in valid or pair[1] not in valid or pair in seen:
            raise ValueError("invalid or duplicate edge")
        if edge.get("type") != "neural-state" or not edge.get("rule_version") or not edge.get("evidence_ref"):
            raise ValueError("typed, versioned, evidence-referenced edges required")
        if not isinstance(edge.get("weight"), (float, int)) or not -1 <= edge["weight"] <= 1:
            raise ValueError("edge weight must be in [-1,1]")
        if edge.get("disposition") != "ENGINEERING HYPOTHESIS":
            raise ValueError("source mechanics are not verified; experimental edges must remain hypotheses")
        seen.add(pair)
    return digest(edges)


def aggregate(micro, edges):
    # Actual activity-connected groups, with no arbitrary nine-center assignment.
    unseen = set(micro)
    groups = []
    while unseen:
        stack = [min(unseen)]
        members = set()
        while stack:
            node = stack.pop()
            if node in members:
                continue
            members.add(node)
            unseen.discard(node)
            for edge in edges:
                if node in (edge["src"], edge["dst"]):
                    peer = edge["dst"] if edge["src"] == node else edge["src"]
                    if peer in micro and peer not in members:
                        stack.append(peer)
        values = [micro[n] for n in sorted(members)]
        groups.append({"members": sorted(members), "state": [sum(v[i] for v in values) / len(values) for i in range(2)]})
    mean = [sum(v[i] for v in micro.values()) / len(micro) for i in range(2)] if micro else [0., 0.]
    return {"groups": groups, "rule": "activity-connected-components-v1",
            "status": "ENGINEERING HYPOTHESIS", "nine_center_mapping": "UNRESOLVED"}, {
                "state": mean, "coherence": 1 - (max((abs(v[0] - mean[0]) for v in micro.values()), default=0.)),
                "rule": "mean-deviation-v1", "status": "ENGINEERING HYPOTHESIS"}
