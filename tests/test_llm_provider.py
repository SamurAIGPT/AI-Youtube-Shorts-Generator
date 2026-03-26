"""Unit tests for LLM provider factory."""

import os
import unittest
from unittest.mock import patch, MagicMock


class TestGetProvider(unittest.TestCase):
    """Tests for provider selection logic."""

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API": "sk-test"}, clear=False)
    def test_explicit_openai_provider(self):
        from Components.llm_provider import get_provider
        self.assertEqual(get_provider(), "openai")

    @patch.dict(os.environ, {"LLM_PROVIDER": "minimax", "MINIMAX_API_KEY": "mm-test"}, clear=False)
    def test_explicit_minimax_provider(self):
        from Components.llm_provider import get_provider
        self.assertEqual(get_provider(), "minimax")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test"}, clear=False)
    def test_auto_detect_minimax(self):
        env = os.environ.copy()
        env.pop("LLM_PROVIDER", None)
        env.pop("OPENAI_API", None)
        with patch.dict(os.environ, env, clear=True):
            os.environ["MINIMAX_API_KEY"] = "mm-test"
            from Components.llm_provider import get_provider
            self.assertEqual(get_provider(), "minimax")

    @patch.dict(os.environ, {"OPENAI_API": "sk-test"}, clear=False)
    def test_auto_detect_openai(self):
        env = os.environ.copy()
        env.pop("LLM_PROVIDER", None)
        env.pop("MINIMAX_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            os.environ["OPENAI_API"] = "sk-test"
            from Components.llm_provider import get_provider
            self.assertEqual(get_provider(), "openai")

    @patch.dict(os.environ, {}, clear=True)
    def test_default_provider_when_no_env(self):
        from Components.llm_provider import get_provider
        self.assertEqual(get_provider(), "openai")

    @patch.dict(os.environ, {"LLM_PROVIDER": "unknown_provider"}, clear=False)
    def test_invalid_provider_falls_back(self):
        from Components.llm_provider import get_provider
        provider = get_provider()
        self.assertIn(provider, ["openai", "minimax"])


class TestGetApiKey(unittest.TestCase):
    """Tests for API key retrieval."""

    @patch.dict(os.environ, {"OPENAI_API": "sk-test-key"}, clear=False)
    def test_get_openai_api_key(self):
        from Components.llm_provider import get_api_key
        self.assertEqual(get_api_key("openai"), "sk-test-key")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test-key"}, clear=False)
    def test_get_minimax_api_key(self):
        from Components.llm_provider import get_api_key
        self.assertEqual(get_api_key("minimax"), "mm-test-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_openai_key_raises(self):
        from Components.llm_provider import get_api_key
        with self.assertRaises(ValueError) as ctx:
            get_api_key("openai")
        self.assertIn("OPENAI_API", str(ctx.exception))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_minimax_key_raises(self):
        from Components.llm_provider import get_api_key
        with self.assertRaises(ValueError) as ctx:
            get_api_key("minimax")
        self.assertIn("MINIMAX_API_KEY", str(ctx.exception))


class TestCreateLlm(unittest.TestCase):
    """Tests for LLM instance creation."""

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"OPENAI_API": "sk-test"}, clear=False)
    def test_create_openai_llm(self, mock_chat):
        from Components.llm_provider import create_llm
        llm = create_llm(provider="openai")
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["model"], "gpt-4o-mini")
        self.assertEqual(call_kwargs["api_key"], "sk-test")
        self.assertNotIn("base_url", call_kwargs)

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test"}, clear=False)
    def test_create_minimax_llm(self, mock_chat):
        from Components.llm_provider import create_llm
        llm = create_llm(provider="minimax")
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["model"], "MiniMax-M2.7")
        self.assertEqual(call_kwargs["api_key"], "mm-test")
        self.assertEqual(call_kwargs["base_url"], "https://api.minimax.io/v1")

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test"}, clear=False)
    def test_minimax_temperature_clamping_zero(self, mock_chat):
        from Components.llm_provider import create_llm
        create_llm(provider="minimax", temperature=0.0)
        call_kwargs = mock_chat.call_args[1]
        self.assertGreater(call_kwargs["temperature"], 0.0)
        self.assertLessEqual(call_kwargs["temperature"], 1.0)

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test"}, clear=False)
    def test_minimax_temperature_clamping_high(self, mock_chat):
        from Components.llm_provider import create_llm
        create_llm(provider="minimax", temperature=2.0)
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["temperature"], 1.0)

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"OPENAI_API": "sk-test"}, clear=False)
    def test_openai_temperature_not_clamped(self, mock_chat):
        from Components.llm_provider import create_llm
        create_llm(provider="openai", temperature=1.5)
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["temperature"], 1.5)

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test", "LLM_MODEL": "MiniMax-M2.7-highspeed"}, clear=False)
    def test_custom_model_via_env(self, mock_chat):
        from Components.llm_provider import create_llm
        create_llm(provider="minimax")
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["model"], "MiniMax-M2.7-highspeed")


class TestProviderConfigs(unittest.TestCase):
    """Tests for provider configuration completeness."""

    def test_all_providers_have_required_keys(self):
        from Components.llm_provider import PROVIDER_CONFIGS
        required_keys = {"env_key", "default_model", "base_url", "display_name"}
        for name, config in PROVIDER_CONFIGS.items():
            self.assertTrue(
                required_keys.issubset(config.keys()),
                f"Provider '{name}' missing keys: {required_keys - config.keys()}"
            )

    def test_minimax_config_values(self):
        from Components.llm_provider import PROVIDER_CONFIGS
        minimax = PROVIDER_CONFIGS["minimax"]
        self.assertEqual(minimax["env_key"], "MINIMAX_API_KEY")
        self.assertEqual(minimax["default_model"], "MiniMax-M2.7")
        self.assertEqual(minimax["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(minimax["display_name"], "MiniMax")

    def test_openai_config_values(self):
        from Components.llm_provider import PROVIDER_CONFIGS
        openai_config = PROVIDER_CONFIGS["openai"]
        self.assertEqual(openai_config["env_key"], "OPENAI_API")
        self.assertEqual(openai_config["default_model"], "gpt-4o-mini")
        self.assertIsNone(openai_config["base_url"])


class TestGetHighlightWithProvider(unittest.TestCase):
    """Tests for GetHighlight function with different providers."""

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-test", "LLM_PROVIDER": "minimax"}, clear=False)
    def test_get_highlight_uses_minimax(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_chat_cls.return_value = mock_llm

        mock_response = MagicMock()
        mock_response.start = 10.0
        mock_response.end = 130.0
        mock_response.content = "Test highlight content"

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = MagicMock(
            __or__=lambda self, other: mock_chain,
            __ror__=lambda self, other: mock_chain,
        )

        # Build chain manually since | operator is mocked
        with patch("Components.LanguageTasks.create_llm", return_value=mock_llm):
            # Patch the chain pipeline
            with patch("langchain.prompts.ChatPromptTemplate.from_messages") as mock_prompt:
                mock_prompt_instance = MagicMock()
                mock_prompt.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

                from Components.LanguageTasks import GetHighlight
                start, end = GetHighlight("0.0 - 200.0: Test transcription text")

                self.assertEqual(start, 10)
                self.assertEqual(end, 130)

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"OPENAI_API": "sk-test", "LLM_PROVIDER": "openai"}, clear=False)
    def test_get_highlight_uses_openai(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_chat_cls.return_value = mock_llm

        mock_response = MagicMock()
        mock_response.start = 5.0
        mock_response.end = 125.0
        mock_response.content = "OpenAI highlight"

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = MagicMock()

        with patch("Components.LanguageTasks.create_llm", return_value=mock_llm):
            with patch("langchain.prompts.ChatPromptTemplate.from_messages") as mock_prompt:
                mock_prompt_instance = MagicMock()
                mock_prompt.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

                from Components.LanguageTasks import GetHighlight
                start, end = GetHighlight("0.0 - 200.0: Test transcription")

                self.assertEqual(start, 5)
                self.assertEqual(end, 125)

    @patch("Components.llm_provider.ChatOpenAI")
    @patch.dict(os.environ, {"OPENAI_API": "sk-test", "LLM_PROVIDER": "openai"}, clear=False)
    def test_get_highlight_returns_none_on_empty_response(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_chat_cls.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = None

        with patch("Components.LanguageTasks.create_llm", return_value=mock_llm):
            with patch("langchain.prompts.ChatPromptTemplate.from_messages") as mock_prompt:
                mock_prompt_instance = MagicMock()
                mock_prompt.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

                from Components.LanguageTasks import GetHighlight
                start, end = GetHighlight("Test transcription")
                self.assertIsNone(start)
                self.assertIsNone(end)


if __name__ == "__main__":
    unittest.main()
