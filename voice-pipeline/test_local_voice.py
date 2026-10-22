import json
import os
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

import local_voice


class CheckLlamaServerTests(unittest.TestCase):
    def test_defaults_target_configured_ollama_model(self):
        # The project env files may pin a local endpoint and a smaller model for
        # this box, so the constants have to follow the same precedence as
        # env_value() instead of hardcoding the documented defaults.
        self.assertEqual(
            local_voice.LLAMA_BASE_URL,
            local_voice.env_value("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/"),
        )
        self.assertEqual(
            local_voice.LLAMA_MODEL,
            local_voice.env_value("LLAMA_MODEL", "qwen2.5:3b"),
        )

    @patch("local_voice.urlopen")
    def test_returns_loaded_model_alias(self, urlopen):
        urlopen.return_value = BytesIO(
            json.dumps({"data": [{"id": "gemma3:1b"}]}).encode()
        )

        result = local_voice.check_llama_server(
            "http://localhost:8080/v1",
            "gemma3:1b",
        )

        self.assertEqual(
            result,
            {
                "url": "http://localhost:8080/v1/models",
                "model": "gemma3:1b",
            },
        )

    @patch("local_voice.urlopen")
    def test_rejects_unloaded_model_alias(self, urlopen):
        urlopen.return_value = BytesIO(
            json.dumps({"data": [{"id": "other-model"}]}).encode()
        )

        with self.assertRaisesRegex(RuntimeError, "ollama run gemma3:1b"):
            local_voice.check_llama_server(
                "http://localhost:8080/v1",
                "gemma3:1b",
            )


class CheckModelSupportsToolsTests(unittest.TestCase):
    @patch("local_voice.urlopen")
    def test_accepts_model_that_reports_tool_support(self, urlopen):
        urlopen.return_value = BytesIO(
            json.dumps({"capabilities": ["completion", "tools"]}).encode()
        )

        result = local_voice.check_model_supports_tools(
            "http://localhost:8080/v1",
            "qwen2.5:3b",
        )

        self.assertEqual(result["capabilities"], ["completion", "tools"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:8080/api/show")

    @patch("local_voice.urlopen")
    def test_rejects_model_without_tool_support(self, urlopen):
        urlopen.return_value = BytesIO(
            json.dumps({"capabilities": ["completion"]}).encode()
        )

        with self.assertRaisesRegex(RuntimeError, "does not support tool calling"):
            local_voice.check_model_supports_tools(
                "http://localhost:8080/v1",
                "gemma3:1b",
            )

    @patch("local_voice.urlopen")
    def test_rejects_unknown_model(self, urlopen):
        urlopen.return_value = BytesIO(json.dumps({"capabilities": []}).encode())

        with self.assertRaisesRegex(RuntimeError, "does not support tool calling"):
            local_voice.check_model_supports_tools(
                "http://localhost:8080/v1",
                "missing-model",
            )


class DependencyConfigurationTests(unittest.TestCase):
    def test_local_requirements_keep_microphone_audio_extra(self):
        requirements_path = os.path.join(
            os.path.dirname(__file__), "requirements-local.txt"
        )
        with open(requirements_path, encoding="utf-8") as requirements_file:
            requirements = requirements_file.read()

        self.assertIn("pipecat-ai[local]", requirements)

    def test_deployment_requirements_omit_local_audio_extra(self):
            requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
            with open(requirements_path, encoding="utf-8") as requirements_file:
                requirements = requirements_file.read()

            pipecat_requirement = next(
                line for line in requirements.splitlines() if line.startswith("pipecat-ai[")
            )
            self.assertNotIn(
                "local",
                pipecat_requirement.partition("[")[2].partition("]")[0].split(","),
                "The Vercel Python runtime cannot compile PyAudio without PortAudio headers.",
            )


class CheckGroqApiTests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("local_voice.urlopen")
    def test_validates_key_without_returning_model_data(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps({"data": []}).encode()
        response.__enter__.return_value = response
        urlopen.return_value = response

        self.assertEqual(local_voice.check_groq_api(), {"status": 200, "ok": True})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/models")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        # Groq's edge rejects urllib's default User-Agent with HTTP 403.
        self.assertEqual(request.get_header("User-agent"), "DialDesk/1.0")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("local_voice.urlopen", side_effect=local_voice.HTTPError(
        "https://api.groq.com/openai/v1/models", 401, "Unauthorized", {}, None
    ))
    def test_reports_auth_failure_without_response_body(self, _urlopen):
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            local_voice.check_groq_api()


class CheckLlmProviderTests(unittest.TestCase):
    def test_accepts_each_supported_provider(self):
        self.assertEqual(local_voice.check_llm_provider("ollama"), "ollama")
        self.assertEqual(local_voice.check_llm_provider("groq"), "groq")

    def test_rejects_an_unknown_provider(self):
        with self.assertRaisesRegex(
            RuntimeError, "LLM_PROVIDER must be 'ollama' or 'groq'"
        ):
            local_voice.check_llm_provider("openai")


class CheckGroqLlmModelTests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    @patch("local_voice.load_groq_key_from_project_env")
    def test_requires_a_groq_key(self, load_key):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY"):
            local_voice.check_groq_llm_model(
                "https://api.groq.com/openai/v1",
                "openai/gpt-oss-120b",
            )
        load_key.assert_called_once()

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("local_voice.urlopen", side_effect=local_voice.HTTPError(
        "https://api.groq.com/openai/v1/models", 401, "Unauthorized", {}, None
    ))
    def test_reports_auth_failure_without_response_body(self, _urlopen):
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            local_voice.check_groq_llm_model(
                "https://api.groq.com/openai/v1",
                "openai/gpt-oss-120b",
            )

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("local_voice.urlopen")
    def test_rejects_a_model_the_account_cannot_reach(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(
            {"data": [{"id": "llama-3.3-70b-versatile"}]}
        ).encode()
        response.__enter__.return_value = response
        urlopen.return_value = response

        with self.assertRaisesRegex(RuntimeError, "openai/gpt-oss-120b"):
            local_voice.check_groq_llm_model(
                "https://api.groq.com/openai/v1",
                "openai/gpt-oss-120b",
            )

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("local_voice.urlopen")
    def test_returns_capabilities_for_an_available_model(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(
            {"data": [{"id": "openai/gpt-oss-120b"}]}
        ).encode()
        response.__enter__.return_value = response
        urlopen.return_value = response

        result = local_voice.check_groq_llm_model(
            "https://api.groq.com/openai/v1",
            "openai/gpt-oss-120b",
        )

        self.assertEqual(result["model"], "openai/gpt-oss-120b")
        self.assertEqual(result["capabilities"], ["completion", "tools"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/models")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        # Groq's edge rejects urllib's default User-Agent with HTTP 403.
        self.assertEqual(request.get_header("User-agent"), "DialDesk/1.0")


class ConfigurationTests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    @patch("local_voice.load_groq_key_from_project_env")
    def test_requires_groq_key(self, _load_key):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY is required"):
            local_voice.check_configuration()

    @patch.dict(os.environ, {"GROQ_API_KEY": "configured-for-test"})
    @patch.object(local_voice, "LLM_PROVIDER", "ollama")
    @patch("local_voice.check_model_supports_tools")
    @patch("local_voice.check_llama_server")
    def test_checks_llama_after_key_is_configured(self, check_server, check_tools):
        expected = {"url": "http://localhost:8080/v1/models", "model": "gemma3:1b"}
        check_server.return_value = expected
        check_tools.return_value = {"model": "gemma3:1b", "capabilities": ["tools"]}

        result = local_voice.check_configuration()

        self.assertEqual(result["model"], "gemma3:1b")
        self.assertTrue(result["supports_tools"])
        check_server.assert_called_once()
        check_tools.assert_called_once()

    @patch.dict(os.environ, {"GROQ_API_KEY": "configured-for-test"})
    @patch.object(local_voice, "LLM_PROVIDER", "ollama")
    @patch("local_voice.urlopen")
    @patch("local_voice.check_llama_server")
    def test_refuses_to_start_when_model_cannot_call_tools(self, check_server, urlopen):
        check_server.return_value = {
            "url": "http://localhost:8080/v1/models",
            "model": "gemma3:1b",
        }
        urlopen.return_value = BytesIO(json.dumps({"capabilities": ["completion"]}).encode())

        with self.assertRaisesRegex(RuntimeError, "does not support tool calling"):
            local_voice.check_configuration()

    @patch.dict(os.environ, {"GROQ_API_KEY": "configured-for-test"})
    @patch.object(local_voice, "LLM_PROVIDER", "groq")
    @patch("local_voice.check_groq_llm_model")
    @patch("local_voice.check_llama_server")
    def test_groq_provider_skips_the_local_llama_check(self, check_server, check_groq):
        check_groq.return_value = {
            "model": "openai/gpt-oss-120b",
            "capabilities": ["completion", "tools"],
        }

        result = local_voice.check_configuration()

        self.assertEqual(result["provider"], "groq")
        self.assertEqual(result["model"], local_voice.GROQ_LLM_MODEL)
        self.assertEqual(result["url"], local_voice.GROQ_BASE_URL)
        self.assertTrue(result["supports_tools"])
        self.assertEqual(result["capabilities"], ["completion", "tools"])
        check_server.assert_not_called()
        check_groq.assert_called_once_with(
            local_voice.GROQ_BASE_URL, local_voice.GROQ_LLM_MODEL
        )

    @patch.dict(os.environ, {"GROQ_API_KEY": "configured-for-test"})
    @patch.object(local_voice, "LLM_PROVIDER", "ollama")
    @patch("local_voice.check_groq_llm_model")
    @patch("local_voice.check_model_supports_tools")
    @patch("local_voice.check_llama_server")
    def test_ollama_provider_reports_the_local_checks(
        self, check_server, check_tools, check_groq
    ):
        check_server.return_value = {
            "url": "http://localhost:8080/v1/models",
            "model": "qwen2.5:3b",
        }
        check_tools.return_value = {
            "model": "qwen2.5:3b",
            "capabilities": ["completion", "tools"],
        }

        result = local_voice.check_configuration()

        self.assertEqual(result["provider"], "ollama")
        self.assertTrue(result["supports_tools"])
        check_server.assert_called_once()
        check_tools.assert_called_once()
        check_groq.assert_not_called()


class BuildLlmServiceTests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch.object(local_voice, "LLM_PROVIDER", "groq")
    @patch.object(local_voice, "GROQ_BASE_URL", "https://groq.example/v1")
    def test_builds_a_groq_service_for_the_groq_provider(self):
        from pipecat.services.groq.llm import GroqLLMService

        service = local_voice.build_llm_service()

        self.assertIsInstance(service, GroqLLMService)
        self.assertEqual(service.settings.model, local_voice.GROQ_LLM_MODEL)
        self.assertEqual(service.settings.temperature, 0.2)
        # Deliberately larger than Ollama's 160: gpt-oss spends reasoning tokens
        # out of max_tokens, and a 160-token budget returns empty content.
        self.assertEqual(service.settings.max_tokens, 512)
        self.assertEqual(service.settings.reasoning_effort, "low")
        self.assertEqual(
            str(service._client.base_url).rstrip("/"),
            "https://groq.example/v1",
        )

    @patch.object(local_voice, "LLM_PROVIDER", "ollama")
    def test_builds_an_ollama_service_for_the_ollama_provider(self):
        from pipecat.services.ollama.llm import OLLamaLLMService

        service = local_voice.build_llm_service()

        self.assertIsInstance(service, OLLamaLLMService)
        self.assertEqual(service.settings.model, local_voice.LLAMA_MODEL)
        self.assertEqual(service.settings.temperature, 0.2)
        self.assertEqual(service.settings.max_tokens, 160)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch.object(local_voice, "LLM_PROVIDER", "groq")
    def test_passes_the_system_instruction_through_to_groq(self):
        service = local_voice.build_llm_service(system_instruction="Speak briefly.")

        self.assertEqual(service.settings.system_instruction, "Speak briefly.")

    @patch.object(local_voice, "LLM_PROVIDER", "ollama")
    def test_passes_the_system_instruction_through_to_ollama(self):
        service = local_voice.build_llm_service(system_instruction="Speak briefly.")

        self.assertEqual(service.settings.system_instruction, "Speak briefly.")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch.object(local_voice, "LLM_PROVIDER", "groq")
    @patch("pipecat.services.groq.llm.GroqLLMService")
    def test_omits_the_system_instruction_for_groq_when_none(self, service_class):
        local_voice.build_llm_service()

        self.assertNotIn("system_instruction", service_class.Settings.call_args.kwargs)

    @patch.object(local_voice, "LLM_PROVIDER", "ollama")
    @patch("pipecat.services.ollama.llm.OLLamaLLMService")
    def test_omits_the_system_instruction_for_ollama_when_none(self, service_class):
        local_voice.build_llm_service()

        self.assertNotIn("system_instruction", service_class.Settings.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
