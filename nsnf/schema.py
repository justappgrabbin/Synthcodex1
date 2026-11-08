from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import hashlib
import math


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Evidence(str, Enum):
    SOURCE = "SOURCE CLAIM"
    DOCUMENTED = "DOCUMENTED PHENOMENON"
    HYPOTHESIS = "ENGINEERING HYPOTHESIS"
    VERIFIED = "VERIFIED PREDICTION"


MODALITIES = {"text", "speech", "gesture", "posture", "gaze", "timing", "movement",
              "touch", "environment", "image", "video", "audio", "code"}


@dataclass(frozen=True)
class ContactEvent:
    actor_ref: str
    modality: str
    timestamp: str
    observed_features: dict
    source_ref: str
    context_ref: str = ""
    relation_edges: list = field(default_factory=list)
    uncertainty: float = 1.0
    consent_scope: str = "private"
    ontology_version: str = "spec-v0.9"
    evidence_class: str = Evidence.DOCUMENTED.value

    def __post_init__(self):
        if self.modality not in MODALITIES:
            raise ValueError("unsupported modality")
        if not self.actor_ref or not self.source_ref or not self.timestamp:
            raise ValueError("actor, timestamp and source are required")
        if not math.isfinite(self.uncertainty) or not 0 <= self.uncertainty <= 1:
            raise ValueError("uncertainty must be in [0, 1]")
        if self.consent_scope not in {"private", "shared-contact"}:
            raise ValueError("invalid consent scope")
        Evidence(self.evidence_class)
        canonical(asdict(self))

    def payload(self):
        return asdict(self)


@dataclass(frozen=True)
class Tier:
    max_components: int
    rounds: int
    max_macs: int


TIERS = {1: Tier(5, 1, 10000), 2: Tier(10, 1, 20000),
         3: Tier(20, 2, 80000), 4: Tier(40, 3, 240000),
         5: Tier(80, 4, 640000)}
