from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import (
    IceServer,
    SmallWebRTCConnection,
)
from pipecat.transports.smallwebrtc.request_handler import (
    IceCandidate,
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from local_voice import (
    SPEED,
    VOICE,
    build_llm_service,
    check_configuration,
    load_groq_key_from_project_env,
    project_env_value,
)

APP_URL = (
    os.environ.get("DIALDESK_APP_URL")
    or project_env_value("DIALDESK_APP_URL")
    or os.environ.get("APP_URL")
    or project_env_value("APP_URL")
).strip().rstrip("/")
GROQ_MODEL = "whisper-large-v3"
TOOL_DEFINITIONS = (
    {
        "name": "check_availability",
        "description": "List open appointment times on a date in the business time zone. Always do this before offering times.",
        "properties": {
            "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
        },
        "required": ["date"],
    },
    {
        "name": "book_appointment",
        "description": "Book only after the caller agrees to a time and provides their name and phone number.",
        "properties": {
            "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
            "time": {"type": "string", "description": "Available time in HH:MM 24-hour format."},
            "customer_name": {"type": "string"},
            "customer_phone": {"type": "string"},
            "customer_email": {"type": "string", "description": "Optional email address."},
            "notes": {"type": "string", "description": "Short reason for the visit or job details."},
        },
        "required": ["date", "time", "customer_name", "customer_phone"],
    },
    {
        "name": "capture_lead",
        "description": "Save caller details when they cannot or do not want to book now.",
        "properties": {
            "name": {"type": "string"},
            "phone": {"type": "string"},
            "email": {"type": "string"},
            "reason": {"type": "string", "description": "What the caller needs."},
        },
        "required": ["name", "phone"],
    },
)
LEGACY_VOICE_MAP = {
    "marin": "af_heart",
    "cedar": "am_michael",
    "alloy": "af_bella",
    "ash": "am_adam",
    "ballad": "af_nicole",
    "coral": "af_sarah",
    "echo": "am_michael",
    "sage": "af_nova",
    "shimmer": "af_sarah",
    "verse": "af_nicole",
}


async def get_session_config(call_token: str) -> dict[str, Any]:
    if not APP_URL:
        raise RuntimeError("DIALDESK_APP_URL must point to the DialDesk app.")
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client:
            async with client.post(
                f"{APP_URL}/api/realtime/voice-config",
                headers={"Authorization": f"Bearer {call_token}"},
            ) as response:
                payload = await response.json()
                if response.status != 200:
                    message = payload.get("message", "Invalid call session.") if isinstance(payload, dict) else "Invalid call session."
                    raise HTTPException(status_code=response.status, detail=message)
                if (
                    not isinstance(payload, dict)
                    or not isinstance(payload.get("instructions"), str)
                    or not isinstance(payload.get("greeting"), str)
                    or not payload["greeting"].strip()
                ):
                    raise RuntimeError("DialDesk returned an invalid voice configuration.")
                return payload
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as error:
        logger.exception("Could not retrieve voice configuration from DialDesk")
        raise HTTPException(status_code=502, detail="DialDesk voice configuration is unavailable.") from error


def make_tool_handler(
    app_url: str,
    call_token: str,
    client: aiohttp.ClientSession,
) -> Callable[[FunctionCallParams], Awaitable[None]]:
    async def handle(params: FunctionCallParams) -> None:
        try:
            async with client.post(
                f"{app_url}/api/realtime/tool",
                headers={"Authorization": f"Bearer {call_token}"},
                json={"name": params.function_name, "args": params.arguments},
            ) as response:
                result = await response.json()
                if response.status >= 400:
                    logger.error("DialDesk tool {} returned HTTP {}", params.function_name, response.status)
                    result = {"ok": False, "error": "tool_unavailable"}
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
            logger.exception("DialDesk tool request failed: {}", params.function_name)
            result = {"ok": False, "error": "tool_unavailable"}
        await params.result_callback(result)

    return handle


async def run_call(connection: SmallWebRTCConnection, call_token: str, config: dict[str, Any]) -> None:
    client_timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=client_timeout) as client:
        transport = SmallWebRTCTransport(
            webrtc_connection=connection,
            params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
        )
        tools = [
            FunctionSchema(
                name=tool["name"],
                description=tool["description"],
                properties=tool["properties"],
                required=tool["required"],
                handler=make_tool_handler(APP_URL, call_token, client),
            )
            for tool in TOOL_DEFINITIONS
        ]
        context = LLMContext(
            messages=[{"role": "system", "content": config["instructions"]}],
            tools=tools,
        )
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
        )
        stt = GroqSTTService(
            api_key=os.environ["GROQ_API_KEY"],
            settings=GroqSTTService.Settings(model=GROQ_MODEL),
        )
        llm = build_llm_service()
        configured_voice = config.get("voice")
        voice = LEGACY_VOICE_MAP.get(configured_voice, configured_voice) if isinstance(configured_voice, str) else VOICE
        tts = KokoroTTSService(
            settings=KokoroTTSService.Settings(
                voice=voice or VOICE,
                speed=SPEED,
            )
        )
        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                user_aggregator,
                llm,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        )
        worker = PipelineWorker(
            pipeline,
            params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        )

        @user_aggregator.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(_, strategy, message):
            # Pipecat passes (aggregator, strategy, message) here.
            if message.content:
                connection.send_app_message({"type": "transcript", "role": "user", "text": message.content})

        @assistant_aggregator.event_handler("on_assistant_turn_stopped")
        async def on_assistant_turn_stopped(_, message):
            if message.content:
                connection.send_app_message({"type": "transcript", "role": "assistant", "text": message.content})

        @transport.event_handler("on_client_connected")
        async def on_client_connected(_, __):
            await queue_initial_greeting(worker, config["greeting"])

        runner = WorkerRunner()
        await runner.add_workers(worker)
        await runner.run()


async def queue_initial_greeting(worker: PipelineWorker, greeting: str) -> None:
    if not greeting.strip():
        raise ValueError("A non-empty business greeting is required.")
    await worker.queue_frame(TTSSpeakFrame(text=greeting))


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_groq_key_from_project_env()
    if not APP_URL:
        raise RuntimeError("DIALDESK_APP_URL must point to the DialDesk app.")
    check_configuration()
    try:
        yield
    finally:
        await webrtc_handler.close()


app = FastAPI(lifespan=lifespan)
webrtc_handler = SmallWebRTCRequestHandler(
    ice_servers=[IceServer(urls=["stun:stun.l.google.com:19302"])],
)
authorized_connections: dict[str, tuple[str, float]] = {}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/offer")
async def offer(request: Request):
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    call_token = authorization[7:]
    if not call_token or len(call_token) > 2000:
        raise HTTPException(status_code=401, detail="Unauthorized.")

    config = await get_session_config(call_token)

    payload = await request.json()
    sdp = payload.get("sdp") if isinstance(payload, dict) else None
    offer_type = payload.get("type") if isinstance(payload, dict) else None
    if not isinstance(sdp, str) or not 20 <= len(sdp) <= 30000 or offer_type != "offer":
        raise HTTPException(status_code=400, detail="Invalid WebRTC offer.")

    async def start_pipeline(connection: SmallWebRTCConnection):
        async def run():
            try:
                await run_call(connection, call_token, config)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Pipecat call pipeline failed")

        asyncio.create_task(run())

    try:
        answer = await webrtc_handler.handle_web_request(
            SmallWebRTCRequest(sdp=sdp, type=offer_type),
            start_pipeline,
        )
        pc_id = answer.get("pc_id") if isinstance(answer, dict) else None
        if isinstance(pc_id, str):
            now = time.monotonic()
            expired = [key for key, (_, expiry) in authorized_connections.items() if expiry <= now]
            for key in expired:
                authorized_connections.pop(key, None)
            authorized_connections[pc_id] = (call_token, now + 7200)
        return answer
    except Exception:
        logger.exception("Pipecat could not establish a WebRTC connection")
        raise HTTPException(status_code=502, detail="Could not establish the WebRTC connection.") from None


@app.patch("/patch")
async def patch_ice_candidates(request: Request):
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    call_token = authorization[7:]
    if not call_token or len(call_token) > 2000:
        raise HTTPException(status_code=401, detail="Unauthorized.")

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid ICE candidate update.")
    pc_id = payload.get("pc_id")
    raw_candidates = payload.get("candidates")
    if not isinstance(pc_id, str) or not 1 <= len(pc_id) <= 200:
        raise HTTPException(status_code=400, detail="Invalid peer connection ID.")
    authorized = authorized_connections.get(pc_id)
    if not authorized or authorized[0] != call_token or authorized[1] <= time.monotonic():
        authorized_connections.pop(pc_id, None)
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if not isinstance(raw_candidates, list) or not 1 <= len(raw_candidates) <= 32:
        raise HTTPException(status_code=400, detail="Invalid ICE candidate list.")

    candidates = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Invalid ICE candidate.")
        candidate = item.get("candidate")
        sdp_mid = item.get("sdp_mid")
        sdp_mline_index = item.get("sdp_mline_index")
        if (
            not isinstance(candidate, str)
            or not candidate
            or len(candidate) > 2048
            or not isinstance(sdp_mid, str)
            or not 1 <= len(sdp_mid) <= 256
            or not isinstance(sdp_mline_index, int)
            or isinstance(sdp_mline_index, bool)
            or not 0 <= sdp_mline_index <= 255
        ):
            raise HTTPException(status_code=400, detail="Invalid ICE candidate.")
        candidates.append(
            IceCandidate(
                candidate=candidate,
                sdp_mid=sdp_mid,
                sdp_mline_index=sdp_mline_index,
            )
        )

    try:
        await webrtc_handler.handle_patch_request(
            SmallWebRTCPatchRequest(pc_id=pc_id, candidates=candidates)
        )
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Pipecat could not apply ICE candidate updates")
        raise HTTPException(status_code=502, detail="Could not update the WebRTC connection.") from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("VOICE_PIPELINE_HOST", "127.0.0.1"),
        port=int(os.environ.get("VOICE_PIPELINE_PORT", "7860")),
    )
