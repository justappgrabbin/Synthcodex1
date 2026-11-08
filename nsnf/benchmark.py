"""Reproducible compute-only benchmark. Synthetic classification, no human-model claims."""
import json
import time
import platform
import resource
from pathlib import Path
import numpy as np
from .components import MLP
from .activation import select


def main():
    rng=np.random.default_rng(101)
    train=rng.normal(size=(160,8))
    test=rng.normal(size=(100,8))
    labels=(test[:,0]>0).astype(int)
    learned=MLP(3)
    for _ in range(18):
        for x in train:
            learned.update(x,int(x[0]>0))
    models=[MLP(i) for i in range(320)]
    for model in models:
        model.restore(learned.snapshot())
    dense=MLP(3)
    dense.restore(learned.snapshot())
    results=[]
    for mode in ('sparse','all-active','small-dense'):
        latencies=[]
        correct=0
        total_macs=0
        for x,y in zip(test,labels):
            start=time.perf_counter_ns()
            if mode=='small-dense':
                output=dense.forward(x)
                count=1
            else:
                indices=[s['index'] for s in select(x,1)] if mode=='sparse' else list(range(320))
                output=np.mean([models[i].forward(x) for i in indices],axis=0)
                count=len(indices)
            latencies.append((time.perf_counter_ns()-start)/1e6)
            correct+=int(np.argmax(output)==y)
            total_macs+=count*MLP.macs
        results.append({'mode':mode,'accuracy':correct/len(test),'p50_ms':float(np.percentile(latencies,50)),
             'p95_ms':float(np.percentile(latencies,95)),'macs_per_request':total_macs/len(test),
             'active_components':5 if mode=='sparse' else 320 if mode=='all-active' else 1,
             'estimated_dollars_per_1000_requests':None,'cost_reason':'hardware billing rate unspecified'})
    report={'seed':101,'task':'synthetic binary sign classification on disjoint held-out vectors',
            'samples':100,'training_samples':160,'quality_threshold':.9,'results':results,
            'hardware':{'platform':platform.platform(),'processor':platform.processor(),'numpy':np.__version__},
            'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'scope':'compute-only; excludes persistence, HTTP and UI. All-active and sparse use identically trained replicated modules.',
            'limitations':['Replicated modules make this a compute ablation, not evidence of distributed field intelligence.',
                           'Small dense baseline can be faster; sparse superiority is not established.',
                           'Per-scenario peak memory, sequence recall and learned graph propagation benchmarks remain required.',
                           'Calibration, VRAM, media success rates and address ablations remain unmeasured.']}
    destination=Path('evidence/nsnf/benchmark.json')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
