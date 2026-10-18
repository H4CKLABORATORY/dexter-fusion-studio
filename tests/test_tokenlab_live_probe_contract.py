"""OpenAI opt-in probe contract tests only; not evidence of paid inference."""
import os
import unittest
from unittest.mock import patch
from tests import tokenlab_live_probes as probe


class OpenAIProbeContract(unittest.TestCase):
    def test_skip_when_secret_absent_without_network(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with patch.object(probe, "post_json") as request:
                outcome=probe.live_openai()
                request.assert_not_called()
        self.assertEqual(outcome["status"],"SKIPPED_NO_OPENAI_API_KEY")
        self.assertFalse(outcome["real_inference"])

    def test_single_request_with_injected_secret_contract(self):
        fake={"status":"completed","output":[{"type":"message","content":[]}],
              "usage":{"input_tokens":11,"output_tokens":2}}
        with patch.dict(os.environ,{"OPENAI_API_KEY":"TEST_ONLY_FAKE_SECRET","OPENAI_TEST_MODEL":"gpt-4.1-mini"}):
            with patch.object(probe,"post_json",return_value=(fake,123.45)) as post:
                result=probe.live_openai()
        post.assert_called_once()
        args,kwargs=post.call_args
        self.assertEqual(args[0],"https://api.openai.com/v1/responses")
        self.assertEqual(args[1]["max_output_tokens"],24)
        self.assertEqual(args[1]["model"],"gpt-4.1-mini")
        self.assertEqual(kwargs["timeout"],90)
        self.assertEqual(result["latency_ms"],123.45)
        self.assertNotIn("TEST_ONLY_FAKE_SECRET",repr(result))

    def test_error_when_provider_response_not_completed(self):
        with patch.dict(os.environ,{"OPENAI_API_KEY":"TEST_ONLY_FAKE_SECRET"}):
            with patch.object(probe,"post_json",return_value=({"status":"incomplete","output":[]},10)):
                with self.assertRaises(AssertionError):
                    probe.live_openai()


if __name__=="__main__":
    unittest.main()
