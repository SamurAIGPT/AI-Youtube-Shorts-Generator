"""
Integration tests for MiniMax LLM provider.

These tests make real API calls to the MiniMax API.
Set MINIMAX_API_KEY environment variable to run them.

Run with: python -m pytest tests/test_integration_minimax.py -v
"""

import os
import unittest

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
SKIP_REASON = "MINIMAX_API_KEY not set"


@unittest.skipUnless(MINIMAX_API_KEY, SKIP_REASON)
class TestMiniMaxIntegration(unittest.TestCase):
    """Integration tests that call the real MiniMax API."""

    def test_minimax_basic_chat(self):
        """Test basic chat completion with MiniMax M2.7."""
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model="MiniMax-M2.7",
            temperature=0.7,
            api_key=MINIMAX_API_KEY,
            base_url="https://api.minimax.io/v1",
        )
        response = llm.invoke("Say 'hello' and nothing else.")
        self.assertIsNotNone(response)
        self.assertTrue(len(response.content) > 0)

    def test_minimax_structured_output(self):
        """Test structured output (function calling) with MiniMax."""
        from langchain_openai import ChatOpenAI
        from pydantic import BaseModel, Field

        class TimeSegment(BaseModel):
            start: float = Field(description="Start time")
            end: float = Field(description="End time")
            content: str = Field(description="Selected text")

        llm = ChatOpenAI(
            model="MiniMax-M2.7",
            temperature=0.7,
            api_key=MINIMAX_API_KEY,
            base_url="https://api.minimax.io/v1",
        )

        chain = llm.with_structured_output(TimeSegment, method="function_calling")
        response = chain.invoke(
            "Select a segment: 0.0 - 30.0: Hello world. "
            "30.0 - 60.0: This is interesting. "
            "60.0 - 90.0: Goodbye."
        )
        self.assertIsNotNone(response)
        self.assertIsInstance(response.start, float)
        self.assertIsInstance(response.end, float)
        self.assertIsInstance(response.content, str)

    def test_create_llm_factory_minimax(self):
        """Test the create_llm factory with MiniMax provider."""
        os.environ["LLM_PROVIDER"] = "minimax"
        from Components.llm_provider import create_llm

        llm = create_llm(provider="minimax")
        response = llm.invoke("Say 'test' and nothing else.")
        self.assertIsNotNone(response)
        self.assertTrue(len(response.content) > 0)


if __name__ == "__main__":
    unittest.main()
