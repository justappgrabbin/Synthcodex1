"""Local single-owner API. Bind to loopback; multi-user hosting is not implemented."""
from pathlib import Path
import os
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from nsnf.runtime import Runtime
from nsnf.schema import ContactEvent


class Execution(BaseModel):
    features: list[float] = Field(min_length=8, max_length=8)
    tier: int = Field(default=1, ge=1, le=5)
    reason: str = "explicit request"
    candidates: list[int] | None = Field(default=None, max_length=320)


class Feedback(BaseModel):
    run_id: str
    target: int = Field(ge=0, le=1)
    evidence_ref: str = Field(min_length=1)
    steps: int = Field(default=1, ge=1, le=100)


def create_app(root=None, owner=None):
    runtime = Runtime(root or os.environ.get("NSNF_DATA", "data"), owner or os.environ.get("NSNF_OWNER", "local-owner"))
    app = FastAPI(title="Cynthia NSNF independent infrastructure", version="0.1.2")
    app.state.runtime = runtime

    @app.exception_handler(ValueError)
    async def bad_request(request, error):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(KeyError)
    async def not_found(request, error):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "record not found"})

    @app.get("/health")
    def health():
        return {"status": "ok", "scope": "local single owner", "journal": runtime.store.verify()}

    @app.post("/execute")
    def execute(body: Execution):
        return runtime.execute(body.features, body.tier, body.reason, body.candidates)

    @app.post("/events")
    def events(body: dict):
        return runtime.contact(body)

    @app.post("/audio")
    async def audio(request: Request):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 16 * 1024 * 1024:
                raise HTTPException(413, "audio exceeds 16 MiB")
        return runtime.ingest_audio(bytes(data))

    @app.get("/artifacts")
    def artifacts():
        return runtime.state.get("artifacts", {})

    @app.get("/artifacts/{key}")
    def artifact(key: str):
        metadata, content = runtime.artifact(key)
        return Response(content, media_type=metadata["media_type"], headers={
            "Content-Disposition": f'inline; filename="{key}"', "X-Content-Type-Options": "nosniff"})

    @app.get("/state/{key}")
    def state(key: str):
        if key == "current":
            return {"id": runtime.head, "state": runtime.state}
        record = runtime.record(key)
        return {"id": key, "state": runtime.store.get(record["state_hash"])}

    @app.get("/topology")
    def topology():
        return runtime.topology()

    @app.post("/topology")
    def update_topology(body: list[dict]):
        return runtime.topology(body)

    @app.get("/runs/{key}")
    def run(key: str):
        return runtime.record(key)

    @app.post("/runs/{key}/replay")
    def replay(key: str):
        return runtime.replay(key)

    @app.get("/history")
    def history():
        return runtime.store.records(runtime.owner)

    @app.post("/feedback")
    def feedback(body: Feedback):
        return runtime.feedback(**body.model_dump())

    @app.post("/contacts/{key}/correction")
    def correction(key: str, body: dict):
        return runtime.correct_contact(key, body.get("meaning"), body.get("evidence_ref"))

    @app.post("/checkpoint")
    def checkpoint():
        return runtime.checkpoint()

    @app.post("/restore")
    def restore(body: dict):
        if not isinstance(body.get("id"), str):
            raise ValueError("record id required")
        return runtime.restore(body["id"])

    @app.get("/")
    def home():
        return FileResponse(Path(__file__).resolve().parents[1] / "ui" / "field.html")

    @app.get("/field.js")
    def script():
        return FileResponse(Path(__file__).resolve().parents[1] / "ui" / "field.js", media_type="text/javascript")

    @app.get("/field.css")
    def style():
        return FileResponse(Path(__file__).resolve().parents[1] / "ui" / "field.css", media_type="text/css")

    @app.get("/capabilities")
    def capabilities():
        return {"neural_execution": "CONNECTED", "contact_investigation": "CONNECTED (bounded observations)",
                "parameter_learning": "TESTED (synthetic binary task)",
                "parameter_transfer": "TESTED (explicit copy; synthetic task)",
                "dimensional_perception": "IMPLEMENTED (three dimensions including current; user-defined rule)",
                "native_audio": "TESTED (PCM measurements, field activation, retrievable artifacts)",
                "nine_center_emergence": "SPECIFIED / UNRESOLVED",
                "general_conversation": "SPECIFIED", "image_generation": "SPECIFIED / BACKEND UNAVAILABLE",
                "video_generation": "SPECIFIED / BACKEND UNAVAILABLE", "voice": "SPECIFIED / DEVICE TEST REQUIRED",
                "bantu_rule_pack": "SPECIFIED / SOURCE FIXTURES REQUIRED",
                "birth_address_calculation": "EXISTING PROVIDERS PRESERVED / v0.9 MAPPING UNRESOLVED"}

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
