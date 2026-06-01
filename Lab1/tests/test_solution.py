"""
Day 1 — LLM API Foundation
Test suite for student solution.

Run from the day folder:
    pytest tests/ -v

All external API calls are mocked — no real API keys required.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

DAY_DIR = Path(__file__).parent.parent
SOLUTION_DIR = DAY_DIR / "solution"


def _load(path: Path, unique_name: str):
    spec = importlib.util.spec_from_file_location(unique_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


if (SOLUTION_DIR / "solution.py").exists():
    _m = _load(SOLUTION_DIR / "solution.py", "solution")
elif (SOLUTION_DIR / "app.py").exists():
    _m = _load(SOLUTION_DIR / "app.py", "solution")
else:
    src = "template.py" if (DAY_DIR / "template.py").exists() else "app.py"
    _m = _load(DAY_DIR / src, "template")

call_openai = getattr(_m, 'call_openai')
call_openai_mini = getattr(_m, 'call_openai_mini')
compare_models = getattr(_m, 'compare_models')
streaming_chatbot = getattr(_m, 'streaming_chatbot')


def _make_openai_response(text: str = "Hello from OpenAI"):
    """Create a minimal mock that looks like an OpenAI ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCallOpenAI(unittest.TestCase):

    @patch("openai.OpenAI")
    def test_returns_non_empty_string(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response("Test response")

        result, latency = call_openai("Hello")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    @patch("openai.OpenAI")
    def test_latency_is_positive_float(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response()

        _, latency = call_openai("Hello")

        self.assertIsInstance(latency, float)
        self.assertGreater(latency, 0.0)

    @patch("openai.OpenAI")
    def test_returns_tuple_of_two(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response()

        result = call_openai("Hello")

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


class TestCallOpenAIMini(unittest.TestCase):

    @patch("openai.OpenAI")
    def test_returns_non_empty_string(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response("Test response")

        result, latency = call_openai_mini("Hello")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    @patch("openai.OpenAI")
    def test_latency_is_positive_float(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response()

        _, latency = call_openai_mini("Hello")

        self.assertIsInstance(latency, float)
        self.assertGreater(latency, 0.0)

    @patch("openai.OpenAI")
    def test_returns_tuple_of_two(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response()

        result = call_openai_mini("Hello")

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


class TestCompareModels(unittest.TestCase):

    def test_returns_dict_with_required_keys(self):
        with patch(f"{compare_models.__module__}.call_openai", return_value=("GPT-4o answer", 0.5)), \
             patch(f"{compare_models.__module__}.call_openai_mini", return_value=("Mini answer", 0.3)):
            result = compare_models("Test prompt")

        required_keys = {
            "gpt4o_response",
            "mini_response",
            "gpt4o_latency",
            "mini_latency",
            "gpt4o_cost_estimate",
        }
        self.assertIsInstance(result, dict)
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_latency_values_are_positive(self):
        with patch(f"{compare_models.__module__}.call_openai", return_value=("GPT-4o answer", 0.5)), \
             patch(f"{compare_models.__module__}.call_openai_mini", return_value=("Mini answer", 0.3)):
            result = compare_models("Test prompt")

        self.assertGreater(result["gpt4o_latency"], 0)
        self.assertGreater(result["mini_latency"], 0)

    def test_responses_are_non_empty_strings(self):
        with patch(f"{compare_models.__module__}.call_openai", return_value=("GPT-4o answer", 0.5)), \
             patch(f"{compare_models.__module__}.call_openai_mini", return_value=("Mini answer", 0.3)):
            result = compare_models("Test prompt")

        self.assertIsInstance(result["gpt4o_response"], str)
        self.assertGreater(len(result["gpt4o_response"]), 0)
        self.assertIsInstance(result["mini_response"], str)
        self.assertGreater(len(result["mini_response"]), 0)

    def test_cost_estimate_is_non_negative(self):
        with patch(f"{compare_models.__module__}.call_openai", return_value=("word " * 100, 0.5)), \
             patch(f"{compare_models.__module__}.call_openai_mini", return_value=("word " * 100, 0.3)):
            result = compare_models("Test prompt")

        self.assertGreaterEqual(result["gpt4o_cost_estimate"], 0)


class TestStreamingChatbot(unittest.TestCase):

    def test_function_exists_and_is_callable(self):
        self.assertTrue(callable(streaming_chatbot))

    @patch("builtins.input", side_effect=["quit"])
    @patch("openai.OpenAI")
    def test_exits_on_quit(self, MockOpenAI, mock_input):
        """Chatbot should exit cleanly when user types 'quit'."""
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        try:
            streaming_chatbot()
        except StopIteration:
            pass  # input() exhausted — acceptable
        except NotImplementedError:
            self.skipTest("streaming_chatbot not yet implemented")


class TestRetryWithBackoff(unittest.TestCase):
    def test_succeeds_on_first_try(self):
        """retry_with_backoff returns value when fn succeeds immediately"""
        result = _m.retry_with_backoff(lambda: 42)
        self.assertEqual(result, 42)

    def test_retries_on_transient_exception(self):
        """retry_with_backoff retries and succeeds after transient failure"""
        call_count = [0]
        def flaky():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("transient")
            return "ok"
        result = _m.retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        self.assertEqual(result, "ok")
        self.assertEqual(call_count[0], 2)

    def test_raises_after_max_retries(self):
        """retry_with_backoff raises exception after exhausting retries"""
        def always_fail():
            raise RuntimeError("permanent failure")
        with self.assertRaises(RuntimeError):
            _m.retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)


class TestBatchCompare(unittest.TestCase):
    def test_returns_correct_length(self):
        """batch_compare returns one result per prompt"""
        with patch.object(_m, 'compare_models', return_value={
            'gpt4o_response': 'a', 'mini_response': 'b',
            'gpt4o_latency': 0.1, 'mini_latency': 0.2,
            'gpt4o_cost_estimate': 0.001
        }):
            results = _m.batch_compare(["q1", "q2", "q3"])
            self.assertEqual(len(results), 3)

    def test_result_contains_prompt_key(self):
        """each result dict contains the original prompt"""
        with patch.object(_m, 'compare_models', return_value={
            'gpt4o_response': 'a', 'mini_response': 'b',
            'gpt4o_latency': 0.1, 'mini_latency': 0.2,
            'gpt4o_cost_estimate': 0.001
        }):
            results = _m.batch_compare(["hello"])
            self.assertIn('prompt', results[0])
            self.assertEqual(results[0]['prompt'], 'hello')


class TestFormatComparisonTable(unittest.TestCase):
    def test_returns_string(self):
        """format_comparison_table returns a string"""
        sample = [{
            'prompt': 'test prompt', 'gpt4o_response': 'response A',
            'mini_response': 'response B', 'gpt4o_latency': 1.0,
            'mini_latency': 1.2, 'gpt4o_cost_estimate': 0.002
        }]
        result = _m.format_comparison_table(sample)
        self.assertIsInstance(result, str)

    def test_contains_column_headers(self):
        """table contains expected column headers"""
        sample = [{
            'prompt': 'q', 'gpt4o_response': 'a', 'mini_response': 'b',
            'gpt4o_latency': 0.5, 'mini_latency': 0.6, 'gpt4o_cost_estimate': 0.001
        }]
        result = _m.format_comparison_table(sample)
        self.assertIn('Prompt', result)
        self.assertIn('GPT-4o', result)
        self.assertIn('Mini', result)


if __name__ == "__main__":
    unittest.main()
