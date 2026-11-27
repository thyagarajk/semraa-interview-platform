"""Entry point: uvicorn semraa_stt.main:app. Real model loading arrives with the M1 voice spike."""

from semraa_worker_common import ModelState, create_worker_app


async def load_model(state: ModelState) -> None:
    # M1: load the pinned model (safetensors/GGUF, checksum verified) once, off the event loop.
    state.model_id = "placeholder"
    state.loaded = True


app = create_worker_app("stt", load_model)
