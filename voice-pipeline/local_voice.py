from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def project_env_value(name: str) -> str:
    project_root = Path(__file__).resolve().parents[1]
    for env_path in (
        project_root / ".env.local",
        project_root / ".env",
        Path(__file__).resolve().parent / ".env",
    ):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                value = value.strip().strip("'\"")
                if value:
                    return value
    return ""


def env_value(name: str, fallback: str) -> str:
    """Resolve a setting from the process environment, then the project env files."""
    return os.environ.get(name, "").strip() or project_env_value(name).strip() or fallback


LLAMA_BASE_URL = env_value("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
LLAMA_MODEL = env_value("LLAMA_MODEL", "qwen2.5:3b")
VOICE = env_value("KOKORO_VOICE", "af_heart")
SPEED = float(env_value("KOKORO_SPEED", "1.1"))
LLM_PROVIDER = env_value("LLM_PROVIDER", "ollama").lower()
GROQ_BASE_URL = env_value("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_LLM_MODEL = env_value("GROQ_LLM_MODEL", "openai/gpt-oss-120b")

SYSTEM_INSTRUCTION = (
    "You are a helpful, concise voice assistant. Keep replies to one or two short "
    "sentences. Speak naturally and do not use markdown, lists, or emoji."
)


def check_llm_provider(provider: str = LLM_PROVIDER) -> str:
    """Validate the configured LLM provider name.

    Only ``ollama`` (local, zero-dependency) and ``groq`` (hosted, tool-capable)
    are supported. Any other value is a configuration mistake that must fail
    loudly instead of silently falling back to a model that cannot call tools.
    """
    if provider not in ("ollama", "groq"):
        raise RuntimeError(
            f"LLM_PROVIDER must be 'ollama' or 'groq', got {provider!r}. "
            "Set it in your environment, the project .env.local, or voice-pipeline/.env."
        )
    return provider


def check_llama_server(base_url: str = LLAMA_BASE_URL, model: str = LLAMA_MODEL) -> dict:
    """Check that Ollama is serving the configured model alias."""
    url = f"{base_url.removesuffix('/v1')}/v1/models"
    try:
        with urlopen(url, timeout=3) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Ollama is not responding at {url}. Start the Ollama service."
        ) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError(f"Ollama returned an invalid model list from {url}.")

    model_ids = {
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if model not in model_ids:
        raise RuntimeError(
            f"Ollama is up, but model alias {model!r} is not available. "
            f"Run `ollama run {model}` and sign in to Ollama if prompted. "
            f"Available aliases: {', '.join(sorted(model_ids)) or '(none)'}."
        )
    return {"url": url, "model": model}


def check_model_supports_tools(base_url: str = LLAMA_BASE_URL, model: str = LLAMA_MODEL) -> dict:
    """Check that the configured model can be called with tool definitions.

    Ollama rejects requests that carry tools for models without tool support
    (``does not support tools``). Pipecat turns that rejection into a fatal
    pipeline error on the first user turn, so the call dies after the greeting
    instead of answering. Detect it before the service accepts a call.
    """
    url = f"{base_url.removesuffix('/v1')}/api/show"
    request = Request(
        url,
        data=json.dumps({"model": model}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(
            f"Ollama returned HTTP {error.code} when describing model {model!r}."
        ) from None
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach Ollama to describe model {model!r}.") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Ollama returned an invalid description for model {model!r}.") from error

    capabilities = payload.get("capabilities") if isinstance(payload, dict) else None
    if not isinstance(capabilities, list):
        raise RuntimeError(f"Ollama returned no capability list for model {model!r}.")
    if "tools" not in capabilities:
        raise RuntimeError(
            f"Ollama model {model!r} does not support tool calling, but the DialDesk "
            "receptionist needs check_availability, book_appointment and capture_lead. "
            "Use a tool-capable model, for example `ollama pull qwen2.5:3b`, and set "
            "LLAMA_MODEL to it."
        )
    return {"model": model, "capabilities": capabilities}


def load_groq_key_from_project_env() -> None:
    if os.environ.get("GROQ_API_KEY", "").strip():
        return
    key = project_env_value("GROQ_API_KEY")
    if key:
        os.environ["GROQ_API_KEY"] = key


def check_groq_api() -> dict:
    load_groq_key_from_project_env()
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured in the environment, project .env.local, "
            "or voice-pipeline/.env."
        )

    request = Request(
        "https://api.groq.com/openai/v1/models",
        headers={
            "Authorization": f"Bearer {key}",
            # Groq's edge (Cloudflare, error 1010) rejects urllib's default
            # ``Python-urllib`` User-Agent, so name the client explicitly.
            "User-Agent": "DialDesk/1.0",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Groq API key check failed with HTTP {response.status}.")
            payload = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Groq API key check failed with HTTP {error.code}.") from None
    except (URLError, TimeoutError) as error:
        raise RuntimeError("Could not reach the Groq API to validate the configured key.") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Groq returned an invalid response while validating the API key.") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Groq returned an invalid model list while validating the API key.")
    return {"status": 200, "ok": True}


def check_groq_llm_model(base_url: str = GROQ_BASE_URL, model: str = GROQ_LLM_MODEL) -> dict:
    """Check that the Groq account can actually reach the configured chat model."""
    load_groq_key_from_project_env()
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is required for the Groq LLM provider. Set it in your "
            "environment, the project .env.local, or voice-pipeline/.env file."
        )

    url = f"{base_url.rstrip('/')}/models"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            # Groq's edge (Cloudflare, error 1010) rejects urllib's default
            # ``Python-urllib`` User-Agent, so name the client explicitly.
            "User-Agent": "DialDesk/1.0",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Groq model check failed with HTTP {response.status}.")
            payload = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Groq model check failed with HTTP {error.code}.") from None
    except (URLError, TimeoutError) as error:
        raise RuntimeError(
            "Could not reach the Groq API to check the configured chat model."
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Groq returned an invalid model list.") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Groq returned an invalid model list.")

    model_ids = [
        item.get("id")
        for item in payload["data"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if model not in model_ids:
        raise RuntimeError(
            f"Groq is reachable, but model {model!r} is not available to this account. "
            f"Available models: {', '.join(sorted(model_ids)) or '(none)'}. "
            "Set GROQ_LLM_MODEL to one of them."
        )
    return {"model": model, "capabilities": ["completion", "tools"]}


def check_configuration() -> dict:
    load_groq_key_from_project_env()
    if not os.environ.get("GROQ_API_KEY", "").strip():
        raise RuntimeError(
            "GROQ_API_KEY is required for Whisper STT. Set it in your environment "
            "or add it to the ignored project .env.local or voice-pipeline/.env file."
        )
    if not 0.5 <= SPEED <= 2.0:
        raise RuntimeError("KOKORO_SPEED must be between 0.5 and 2.0.")
    provider = check_llm_provider(LLM_PROVIDER)
    if provider == "groq":
        model = check_groq_llm_model(GROQ_BASE_URL, GROQ_LLM_MODEL)
        return {
            "provider": "groq",
            "model": GROQ_LLM_MODEL,
            "url": GROQ_BASE_URL,
            "supports_tools": True,
            "capabilities": model["capabilities"],
        }
    result = check_llama_server()
    tools = check_model_supports_tools(LLAMA_BASE_URL, LLAMA_MODEL)
    return {**result, "provider": "ollama", "supports_tools": True, "capabilities": tools["capabilities"]}


def build_llm_service(system_instruction: str | None = None):
    """Create the LLM service for the configured provider."""
    provider = check_llm_provider(LLM_PROVIDER)
    if provider == "groq":
        from pipecat.services.groq.llm import GroqLLMService

        load_groq_key_from_project_env()
        # Groq's budget is deliberately larger than Ollama's, do not unify them:
        # gpt-oss counts reasoning tokens against ``max_tokens``, so a 160-token
        # budget is consumed while thinking and the model returns empty content
        # (silent turn) after tool calls. ``reasoning_effort="low"`` bounds the
        # thinking without hurting tool-call accuracy.
        settings = {
            "model": GROQ_LLM_MODEL,
            "temperature": 0.2,
            "max_tokens": 512,
            "reasoning_effort": "low",
        }
        if system_instruction is not None:
            settings["system_instruction"] = system_instruction
        return GroqLLMService(
            api_key=os.environ["GROQ_API_KEY"],
            base_url=GROQ_BASE_URL,
            settings=GroqLLMService.Settings(**settings),
        )

    from pipecat.services.ollama.llm import OLLamaLLMService

    settings = {"model": LLAMA_MODEL, "temperature": 0.2, "max_tokens": 160}
    if system_instruction is not None:
        settings["system_instruction"] = system_instruction
    return OLLamaLLMService(
        base_url=LLAMA_BASE_URL,
        settings=OLLamaLLMService.Settings(**settings),
    )


async def run_voice_pipeline() -> None:
    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.worker import PipelineParams, PipelineWorker
        from pipecat.processors.aggregators.llm_context import LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMContextAggregatorPair,
            LLMUserAggregatorParams,
        )
        from pipecat.services.groq.stt import GroqSTTService
        from pipecat.services.kokoro.tts import KokoroTTSService
        from pipecat.transports.local.audio import (
            LocalAudioTransport,
            LocalAudioTransportParams,
        )
        from pipecat.workers.runner import WorkerRunner
    except ImportError as error:
        raise RuntimeError(
            "Voice dependencies are missing. Install them with "
            "`python -m pip install -r voice-pipeline/requirements-local.txt`."
        ) from error

    check_configuration()

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )
    stt = GroqSTTService(
        api_key=os.environ["GROQ_API_KEY"],
        settings=GroqSTTService.Settings(model="whisper-large-v3"),
    )
    llm = build_llm_service(system_instruction=SYSTEM_INSTRUCTION)
    tts = KokoroTTSService(
        settings=KokoroTTSService.Settings(
            voice=VOICE,
            speed=SPEED,
        )
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
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
    runner = WorkerRunner()
    print("Local voice assistant ready. Speak into the default microphone; press Ctrl+C to stop.")
    await runner.add_workers(worker)
    await runner.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local DialDesk voice pipeline.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the configured LLM provider, its model and tool support without starting audio.",
    )
    parser.add_argument(
        "--check-groq",
        action="store_true",
        help="Validate the configured Groq API key without starting audio.",
    )
    args = parser.parse_args()
    try:
        if args.check and args.check_groq:
            parser.error("Choose only one of --check or --check-groq.")
        if args.check_groq:
            print(json.dumps(check_groq_api(), indent=2))
        elif args.check:
            print(json.dumps(check_configuration(), indent=2))
        else:
            asyncio.run(run_voice_pipeline())
    except (RuntimeError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            print("\nStopped.")
            return
        parser.error(str(error))


if __name__ == "__main__":
    main()
