"""Run with python -m nsnf.perception_demo; isolated, real neural execution."""
import json
from tempfile import TemporaryDirectory
from .runtime import Runtime


def main():
    with TemporaryDirectory() as directory:
        runtime = Runtime(directory)
        edges = [{"src": src, "dst": dst, "type": "neural-state", "weight": .5,
                  "rule_version": "dimensional-perception-demo-v1", "evidence_ref": "perception-demo",
                  "disposition": "ENGINEERING HYPOTHESIS"}
                 for src, dst in [("d0:g0", "d1:g0"), ("d1:g0", "d2:g0")]]
        runtime.topology(edges)
        features = [1., 0, 0, 0, 0, 0, 0, 0]
        blocked = runtime.execute(features, 3, candidates=[64, 128])
        permitted = runtime.execute(features, 3, candidates=[0, 64, 128])
        print(json.dumps({"two_dimensions": blocked["perception"],
                          "three_dimensions_including_current": permitted["perception"],
                          "replay": runtime.replay(permitted["id"])}, indent=2))
        runtime.store.db.close()


if __name__ == "__main__":
    main()
