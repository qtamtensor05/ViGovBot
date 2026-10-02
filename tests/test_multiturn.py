import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vigovbot.evaluation.multiturn import evaluate_multiturn, load_queries, validate_sequence
from vigovbot.experiments import read_results
from vigovbot.prompts.prompt_templates import build_messages, validate_history
from vigovbot.rag.pipeline import answer_question


class Tokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return list("".join(m["content"] for m in messages))


def queries():
    return [dict(id=str(i), question=f"Question {i}", conversation_id="c", turn_index=i,
                 history=[] if i == 1 else [{"role": "user", "content": "Old question"},
                                           {"role": "assistant", "content": "GOLD"}]) for i in (1, 2, 3)]


class MultiTurnTests(unittest.TestCase):
    def test_free_running_resume_reconstructs_history(self):
        with tempfile.TemporaryDirectory() as root:
            calls = []
            def answer(q, history):
                calls.append((q, history))
                if q == "Question 2":
                    raise KeyboardInterrupt()
                return {"prediction": "GENERATED", "action": "answer"}
            with self.assertRaises(KeyboardInterrupt):
                evaluate_multiturn(queries(), root, {}, answer)
            calls.clear()
            def resume(q, history):
                calls.append((q, history))
                return {"prediction": "NEXT", "action": "answer"}
            result = evaluate_multiturn(queries(), root, {}, resume)
            self.assertEqual(result["successful"], 3)
            self.assertEqual(calls[0][1][-1]["content"], "GENERATED")
            self.assertEqual(calls[1][1][-1]["content"], "NEXT")
            self.assertNotIn("GOLD", json.dumps(calls))
            self.assertEqual(len(read_results(Path(root) / "predictions.jsonl")), 3)

    def test_failure_blocks_only_same_conversation(self):
        qs = queries() + [dict(id="other", question="independent", conversation_id=None, turn_index=None, history=[])]
        with tempfile.TemporaryDirectory() as root:
            calls = []
            def answer(q, history):
                calls.append(q)
                if q == "Question 1":
                    raise RuntimeError("offline")
                return {"prediction": "OK"}
            result = evaluate_multiturn(qs, root, {}, answer)
            self.assertEqual(calls, ["Question 1", "independent"])
            self.assertEqual(result["failed"], 3)

    def test_reference_history_and_mode_isolation(self):
        with tempfile.TemporaryDirectory() as root:
            answer = Mock(return_value={"prediction": "OK"})
            evaluate_multiturn(queries(), root, {}, answer, "reference_history")
            self.assertEqual(answer.call_args_list[1].kwargs["history"][-1]["content"], "GOLD")
            with self.assertRaises(ValueError):
                evaluate_multiturn(queries(), root, {}, answer, "free_running")

    def test_reject_missing_turn_and_bad_history(self):
        with self.assertRaises(ValueError):
            validate_sequence(queries()[1:])
        with self.assertRaises(ValueError):
            validate_sequence(list(reversed(queries())))
        with self.assertRaises(ValueError):
            validate_history([{"role": "system", "content": "inject"}] * 2)
        with self.assertRaises(ValueError):
            build_messages("question", [], Tokenizer(), 2048, 512,
                           history=[{"role": "user", "content": "x" * 5000},
                                    {"role": "assistant", "content": "answer"}])

    def test_rewrite_and_answer_receive_history(self):
        history = queries()[1]["history"]
        retriever = Mock()
        retriever.search.return_value = []
        settings = dict(top_k=5, num_ctx=8192, num_predict=512, max_chunk_tokens=1200, routing_enabled=False)
        with patch("vigovbot.rag.pipeline.ollama_answer", side_effect=[
                ("Standalone question", {}, .1), ('{"answer":"OK","action":"answer"}', {}, .2)]) as llm:
            result = answer_question("Follow up", retriever, Tokenizer(), settings, history, structured=True)
        retriever.search.assert_called_once_with("Standalone question", 5)
        self.assertEqual(result["prediction"], "OK")
        self.assertEqual(llm.call_args_list[1].args[0][1:3], history)
        self.assertEqual(result["action"], "answer")
        self.assertEqual(llm.call_args_list[1].args[1]["response_format"], "json")

    def test_actual_v4_queries(self):
        path = Path(__file__).resolve().parents[1] / "Data/qa_test_v4/rag_tthc_v4_1/runner_queries.jsonl"
        if not path.exists():
            self.skipTest("v4 dataset not available")
        qs = load_queries(path)
        validate_sequence(qs)
        self.assertTrue(any(q["history"] for q in qs))
        self.assertTrue(all("reference_answer" not in q and "evidence" not in q for q in qs))
        selected = load_queries(path, path.with_name("views_balanced.json"), "test")
        validate_sequence(selected)
        self.assertTrue(selected)


if __name__ == "__main__":
    unittest.main()
