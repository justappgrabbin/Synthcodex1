"""Lossless address structure. No invented birth calculation or causal mappings."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from .schema import canonical

FIELDS = ("Gate", "Line", "Color", "Tone", "Base", "Degree", "Minute", "Second", "Axis", "Zodiac", "House")
NUMERIC = set(FIELDS[:8])


@dataclass(frozen=True)
class Address:
    values: dict
    dimensional_context: str
    source_ref: str
    calculation_method: str
    uncertainty: dict

    @classmethod
    def parse(cls, data):
        values = data["values"]
        if set(values) != set(FIELDS):
            raise ValueError("exact canonical address fields required")
        for name, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError("source coordinates must be nonempty strings to retain precision")
            if name in NUMERIC:
                try:
                    if not Decimal(value).is_finite():
                        raise ValueError("nonfinite coordinate")
                except InvalidOperation as error:
                    raise ValueError("invalid numeric coordinate") from error
        for name in ("dimensional_context", "source_ref", "calculation_method"):
            if not isinstance(data.get(name), str) or not data[name]:
                raise ValueError(f"{name} required")
        uncertainty = data.get("uncertainty", {})
        if set(uncertainty) - set(FIELDS):
            raise ValueError("unknown uncertainty coordinate")
        return cls(dict(values), data["dimensional_context"], data["source_ref"],
                   data["calculation_method"], dict(uncertainty))

    def serialize(self):
        # An ordered list preserves the canonical field sequence even in sorted JSON.
        return canonical({"coordinates": [[k, self.values[k]] for k in FIELDS],
                          "dimensional_context": self.dimensional_context,
                          "source_ref": self.source_ref, "calculation_method": self.calculation_method,
                          "uncertainty": self.uncertainty})

    def compare(self, other):
        return [{"field": k, "before": self.values[k], "after": other.values[k],
                 "equal": Decimal(self.values[k]) == Decimal(other.values[k]) if k in NUMERIC
                 else self.values[k] == other.values[k]} for k in FIELDS]

    def shared_contact(self):
        # Conservative boundary: Base and all below-Base fields withheld.
        return {k: self.values[k] for k in FIELDS[:4]}


def evaluate_transition(before, after, rules=None):
    comparison = before.compare(after)
    if rules is None:
        return {"status": "UNRESOLVED", "reason": "source-confirmed transition rules unavailable",
                "contributions": comparison, "permitted": None}
    if not rules.get("version") or not rules.get("source_ref"):
        raise ValueError("versioned, sourced rules required")
    allowed = set(rules.get("mutable_fields", []))
    if allowed - set(FIELDS):
        raise ValueError("unknown rule coordinate")
    changed = [v["field"] for v in comparison if not v["equal"]]
    return {"status": "ENGINEERING HYPOTHESIS", "permitted": set(changed) <= allowed,
            "rule_version": rules["version"], "source_ref": rules["source_ref"],
            "contributions": comparison}
