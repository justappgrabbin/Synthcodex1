# Cynthia NSNF descendant infrastructure

Executable, tested infrastructure toward the cumulative v0.9 specification. **The full requested system remains unfinished.** See [capability status and unresolved mechanics](docs/nsnf/STATUS.md), and [changelog](docs/nsnf/CHANGELOG.md).

## Run locally

Python 3.11+ is required. The server is a local, single-owner prototype. Use a separate data directory per owner; it has no multi-user authentication or hosted deployment contract.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . httpx
python -m api.server
```

Open `http://127.0.0.1:8000`. The page submits real field runs and contact observations and reads persisted traces. Untrained output is a binary probability vector, not general language understanding. Desktop (1440 × 1100) and mobile (390 × 844) browser checks pass, including checkpoint, replay and real audio upload. Native audio analysis accepts 16-bit mono/stereo PCM WAV at 8–48 kHz, up to 30 seconds. POST WAV bytes to `/audio`; retrieve the original and measured analysis through `/artifacts/{hash}`. Acoustic measurements do not establish words, emotion or meaning.

Set `NSNF_DATA` to choose the durable SQLite/blob directory. Default owner is `local-owner`; `NSNF_OWNER` can change it for API use. The present diagnostic contact form uses `local-owner` explicitly. Never point distinct owners at the same store.

## Reproduce tests and benchmark

The [dimensional perception rule](docs/nsnf/PERCEPTION.md) now requires at least three expressed dimensions including the current dimension for perception in D3, D4 or D5. Run `python -m nsnf.perception_demo` for a real execution/replay example. Execution traces and the UI distinguish perceived outputs from raw neural values.

```sh
python -m unittest discover -s tests/nsnf -v
python -m nsnf.benchmark
```

The benchmark writes `evidence/nsnf/benchmark.json`. It compares sparse execution, all 320 identically trained replicas, and one small dense module on a synthetic binary classification task. It excludes HTTP and persistence. Its small dense baseline is faster. It does not demonstrate field intelligence or general resource superiority.

## Existing Computer integration

The saved increment includes `integration/synthai-nsnf.patch`, based on SynthAi commit `826ca35217b0d671bf81b3bdc2518afc4402e32e`. It adds an optional field service and its real integration test while preserving original Computer code. Apply it in a separate descendant checkout:

```sh
git clone --recurse-submodules https://github.com/justappgrabbin/SynthAi.git synthai-descendant
cd synthai-descendant
git checkout -b feat/nsnf-v09 826ca35217b0d671bf81b3bdc2518afc4402e32e
git submodule update --init --recursive
git apply /absolute/path/to/Synthcodex1/integration/synthai-nsnf.patch
python -m pip install ephem
npm run test:computer
NSNF_TEST_URL=http://127.0.0.1:8000 node --test computer/tests/nsnf-integration.test.mjs
```

Construct the existing Computer with `{nsnfBaseUrl:'http://127.0.0.1:8000'}`. After `boot()`, `runtime.neuralField.execute({features:[1,0,0,0,0,0,0,0],tier:1})` invokes actual Python neural execution and appends its evidence to the Computer's event history. `runtime.neuralField.contact(observation)` uses the bounded observation/investigation workflow.

## API

`POST /audio`, `GET /artifacts`, `GET /artifacts/{hash}`, `POST /events`, `POST /execute`, `GET /state/{id}`, `GET /topology`, `POST /topology`, `GET /runs/{id}`, `POST /runs/{id}/replay`, `POST /checkpoint`, `POST /restore`, `POST /feedback`, `POST /contacts/{id}/correction`, `GET /history`, `GET /capabilities`, `GET /health`. Local API documentation is at `/docs`.

Weights, topology, source claims, compact state codes and activation masks are distinct. No fixed nine-center mapping or birth-derived address calculation has been invented. Source-confirmed mechanics, Bantu rule packs, full conversation, media backends, device-tested voice, shared learning, and remaining acceptance benchmarks are still required.
