from copy import deepcopy
import time
import threading
from datetime import datetime, timezone
import numpy as np
from .schema import TIERS, ContactEvent, digest
from .components import MLP
from .activation import select
from .topology import aggregate, validate_edges, slots
from .state_store import Store


class Runtime:
    def __init__(self, root, owner="local-owner"):
        self.store = Store(root)
        self.owner = owner
        self.lock = threading.RLock()
        self.cache = {}
        latest = self.store.latest()
        if latest:
            self.head, self.state = latest["id"], latest["state"]
            if self.state["owner"] != owner:
                raise ValueError("this private store belongs to another owner")
            self.store.verify()
        else:
            self.state = {"schema_version": 1, "owner": owner, "dimension_codes": [0] * 5,
                          "active_masks": ["0"] * 5, "models": {}, "model_version": 0,
                          "edges": [], "topology_version": digest([]), "contacts": [], "corrections": {},
                          "meso": {"nine_center_mapping": "UNRESOLVED"}, "macro": {}, "last_run": None}
            self.head = None
            self._commit("initialize", {"lineage": "independent infrastructure; originals unavailable"}, self.state)

    def _commit(self, kind, payload, state):
        head = self.store.append(self.owner, kind, payload, state, self.head)
        self.head, self.state = head, deepcopy(state)
        return head

    def model(self, index, state=None):
        value = self.state if state is None else state
        model = MLP(index)
        if str(index) in value["models"]:
            model.restore(value["models"][str(index)])
        return model

    def _compute(self, features, tier, state, candidates=None, cache=True):
        selected = select(features, tier, candidates)
        micro = {}
        messages = []
        inputs = {}
        hits = 0
        macs = 0
        relevant = {k: state[k] for k in ("models", "topology_version", "edges")}
        key = digest({"features": features, "tier": tier, "state": relevant, "selected": selected})
        if cache and key in self.cache:
            result = deepcopy(self.cache[key])
            result["cache_hits"] = len(selected) * TIERS[tier].rounds
            result["macs"] = 0
            return result
        models = {item["component_id"]: self.model(item["index"], state) for item in selected}
        for round_number in range(TIERS[tier].rounds):
            next_micro = {}
            for item in selected:
                name = item["component_id"]
                x = np.array(features, dtype=float)
                for edge in state["edges"]:
                    if edge["dst"] == name and edge["src"] in micro:
                        payload = np.array(micro[edge["src"]]) * edge["weight"]
                        x[:2] += payload
                        messages.append({"round": round_number, "src": edge["src"], "dst": name,
                                         "type": edge["type"], "payload": payload.tolist(),
                                         "rule_version": edge["rule_version"]})
                next_micro[name] = models[name].forward(x).tolist()
                inputs[str(item["index"])] = x.tolist()
                macs += MLP.macs
            micro = next_micro
        meso, macro = aggregate(micro, state["edges"])
        result = {"selected": selected, "micro": micro, "meso": meso, "macro": macro,
                  "messages": messages, "component_inputs": inputs, "macs": macs,
                  "cache_hits": hits, "cache_key": key}
        if cache:
            # Bounded process-local cache; checkpoints and model changes alter the key.
            if len(self.cache) >= 128:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = deepcopy(result)
        return result

    def execute(self, features, tier=1, reason="explicit request", candidates=None):
        with self.lock:
            start = time.perf_counter()
            features = [float(v) for v in features]
            before_hash = self.store.put(self.state)
            result = self._compute(features, tier, self.state, candidates)
            state = deepcopy(self.state)
            masks = [0] * 5
            for item in result["selected"]:
                index = item["index"]
                masks[index // 64] |= 1 << (index % 64)
            state["active_masks"] = [str(v) for v in masks]
            for dim in range(5):
                choices = [s for s in result["selected"] if s["index"] // 64 == dim]
                if choices:
                    state["dimension_codes"][dim] = choices[0]["index"] % 64
            state["meso"], state["macro"] = result["meso"], result["macro"]
            result.update({"features": features, "tier": tier, "tier_reason": reason,
                           "candidates": candidates, "before_hash": before_hash,
                           "topology_version": state["topology_version"], "model_version": state["model_version"],
                           "output": result["macro"]["state"],
                           "output_semantics": "untrained binary probabilities unless task-specific training is supplied",
                           "latency_ms": (time.perf_counter() - start) * 1000})
            state["last_run"] = digest(result)
            key = self._commit("execute", result, state)
            return {"id": key, **result}

    def feedback(self, run_id, target, evidence_ref, steps=1):
        if not evidence_ref:
            raise ValueError("feedback evidence reference required")
        if type(steps) is not int or not 1 <= steps <= 100:
            raise ValueError("steps must be 1..100")
        with self.lock:
            record = self.record(run_id)
            if record["kind"] != "execute":
                raise ValueError("feedback must reference an execution")
            run = record["payload"]
            if run["model_version"] != self.state["model_version"]:
                raise ValueError("stale feedback; execute with current model version")
            state = deepcopy(self.state)
            deltas = []
            for item in run["selected"]:
                index = item["index"]
                model = self.model(index)
                before = digest(model.snapshot())
                inputs = run["component_inputs"][str(index)]
                losses = [model.update(inputs, target) for _ in range(steps)]
                state["models"][str(index)] = model.snapshot()
                deltas.append({"component": item["component_id"], "before": before,
                               "after": digest(model.snapshot()), "loss_before": losses[0],
                               "loss_after": float(-np.log(max(float(model.forward(inputs)[target]), 1e-15)))})
            state["model_version"] += 1
            return {"id": self._commit("feedback", {"run_id": run_id, "target": target,
                    "evidence_ref": evidence_ref, "deltas": deltas,
                    "credit_rule": "broadcast-supervised-target-v1; engineering hypothesis"}, state), "deltas": deltas}

    def contact(self, event):
        with self.lock:
            if not isinstance(event, ContactEvent):
                event = ContactEvent(**event)
            if event.actor_ref != self.owner:
                raise ValueError("actor differs from store owner")
            observations = event.observed_features
            # Observation retrieval is a real investigation operation; no sensor is simulated.
            related = [self.record(r)["payload"]["observation"] for r in self.state["contacts"][-10:]]
            pattern = digest({"modality": event.modality, "features": observations, "context": event.context_ref})
            correction = self.state.get("corrections", {}).get(pattern)
            meaning = correction["meaning"] if correction else observations.get("verified_meaning")
            clarification = not correction and (event.uncertainty > .35 or not meaning)
            f = [0.] * 8
            modality_order = ["text", "speech", "gesture", "image", "video", "audio", "environment", "code"]
            f[modality_order.index(event.modality) if event.modality in modality_order else 6] = 1.
            f[7] = event.uncertainty
            if "neural_features" in observations:
                # Native extractor features participate in computation; selection validates them.
                f = observations["neural_features"]
            run = self.execute(f, 2 if clarification else 1, "ambiguity investigation" if clarification else "grounded observation")
            result = {"observation": event.payload(), "field_run": run["id"],
                      "missing_modalities": {m: "UNKNOWN" for m in modality_order if m != event.modality},
                      "pattern": pattern, "correction": correction,
                      "interpretation": meaning if not clarification else None,
                      "investigation": {"operation": "retrieve_recent_observations", "retrieved": len(related),
                                        "alternatives": ["meaning confirmed", "meaning unresolved"]},
                      "action": "request_clarification" if clarification else "acknowledge_verified_observation",
                      "response": "What did this contact mean in this situation?" if clarification else str(meaning),
                      "stages": ["Observe", "Interpret", "Investigate", "Verify"],
                      "status": "bounded observation workflow; general conversation not implemented"}
            state = deepcopy(self.state)
            # Contact IDs reference their own preceding observation entry, avoiding self-hash cycles.
            observation_id = self._commit("contact", result, state)
            state = deepcopy(self.state)
            state["contacts"].append(observation_id)
            self._commit("contact_index", {"contact_id": observation_id}, state)
            return {"id": observation_id, **result}

    def ingest_audio(self, data, consent_scope="private"):
        from .acoustics import analyze_wav
        analysis = analyze_wav(data)
        with self.lock:
            source_hash = self.store.put_bytes(data, "audio/wav")
            analysis_hash = self.store.put(analysis)
            event = ContactEvent(actor_ref=self.owner, modality="audio",
                timestamp=datetime.now(timezone.utc).isoformat(),
                observed_features={"neural_features": analysis["neural_features"],
                    "analysis_ref": analysis_hash, "duration_s": analysis["duration_s"],
                    "signal_quality": "uncalibrated PCM; no semantic labels"},
                source_ref=source_hash, uncertainty=1., consent_scope=consent_scope)
            result = self.contact(event)
            state = deepcopy(self.state)
            artifacts = state.setdefault("artifacts", {})
            artifacts[source_hash] = {"media_type": "audio/wav", "bytes": len(data),
                "kind": "original-audio", "contact_id": result["id"], "consent_scope": consent_scope}
            artifacts[analysis_hash] = {"media_type": "application/json", "kind": "acoustic-analysis",
                "source_ref": source_hash, "contact_id": result["id"], "extractor": analysis["decoder"]}
            self._commit("audio_artifacts", {"source_hash": source_hash, "analysis_hash": analysis_hash,
                "contact_id": result["id"]}, state)
            return {"contact": result, "source_hash": source_hash, "analysis_hash": analysis_hash,
                    "analysis": analysis}

    def artifact(self, key):
        if key not in self.state.get("artifacts", {}):
            raise KeyError(key)
        return self.state["artifacts"][key], self.store.get_bytes(key)

    def correct_contact(self, contact_id, meaning, evidence_ref):
        if not isinstance(meaning, str) or not meaning.strip() or not evidence_ref:
            raise ValueError("meaning and evidence reference required")
        with self.lock:
            record = self.record(contact_id)
            if record["kind"] != "contact":
                raise ValueError("contact id required")
            state = deepcopy(self.state)
            correction = {"meaning": meaning, "evidence_ref": evidence_ref, "contact_id": contact_id,
                          "scope": "exact observed features and context for this owner"}
            state.setdefault("corrections", {})[record["payload"]["pattern"]] = correction
            return {"id": self._commit("contact_correction", correction, state)}

    def transfer(self, source, target, evidence_ref):
        if any(type(i) is not int or not 0 <= i < 320 for i in (source, target)) or source == target:
            raise ValueError("distinct component indices in 0..319 required")
        if not evidence_ref:
            raise ValueError("transfer experiment evidence required")
        with self.lock:
            state = deepcopy(self.state)
            parameters = self.model(source).snapshot()
            before = digest(self.model(target).snapshot())
            state["models"][str(target)] = parameters
            state["model_version"] += 1
            payload = {"source": source, "target": target, "before": before, "after": digest(parameters),
                       "rule": "explicit-parameter-copy-v1", "evidence_ref": evidence_ref,
                       "status": "engineering operation; held-out utility must be measured per experiment"}
            return {"id": self._commit("transfer", payload, state), **payload}

    def topology(self, edges=None):
        with self.lock:
            if edges is not None:
                version = validate_edges(edges)
                state = deepcopy(self.state)
                state["edges"], state["topology_version"] = edges, version
                self._commit("topology", {"version": version, "edges": edges}, state)
            return {"slots": slots(), "edges": self.state["edges"],
                    "version": self.state["topology_version"], "dimensions": 5,
                    "dimension_semantics": "UNRESOLVED", "nine_center_rules": "UNRESOLVED"}

    def record(self, key):
        for record in self.store.records(self.owner):
            if record["id"] == key:
                return record
        raise KeyError(key)

    def checkpoint(self):
        with self.lock:
            key = self._commit("checkpoint", {"checkpoint_hash": self.store.put(self.state)}, self.state)
            return {"id": key, "state_hash": self.store.put(self.state)}

    def restore(self, key):
        with self.lock:
            record = self.record(key)
            state = self.store.get(record["state_hash"])
            head = self._commit("restore", {"source_record": key, "source_state_hash": record["state_hash"]}, state)
            return {"id": head, "restored_from": key}

    def replay(self, key):
        with self.lock:
            record = self.record(key)
            if record["kind"] != "execute":
                raise ValueError("replay expects an execution")
            original = record["payload"]
            before = self.store.get(original["before_hash"])
            actual = self._compute(original["features"], original["tier"], before, original["candidates"], cache=False)
            fields = ("selected", "micro", "meso", "macro", "messages", "component_inputs")
            matches = {field: actual[field] == original[field] for field in fields}
            return {"run_id": key, "exact": all(matches.values()), "checks": matches,
                    "journal": self.store.verify()}
