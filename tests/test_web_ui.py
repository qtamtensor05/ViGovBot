"""Exercise browser routing labels/history helpers without a running server."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is needed to verify browser JavaScript")
class WebUITests(unittest.TestCase):
    def test_script_syntax_and_fallback_history(self):
        path = Path(__file__).resolve().parents[1] / "src/vigovbot/server/static/index.html"
        script = path.read_text(encoding="utf-8").split("<script>", 1)[1].split("</script>", 1)[0]
        helpers = script[script.index("function routingStatus"):script.index("function addAnswers")]
        javascript = """
const vm=require('node:vm'),assert=require('node:assert/strict');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
new vm.Script(input.script);
vm.runInNewContext(input.helpers+`
const fallback={answer:'Bạn vui lòng nêu rõ thủ tục và nội dung cần tra cứu?',
  routing_diagnostics:{fallback_reason:'invalid_routing_after_retry',routing_attempts:2}};
assert.match(routingStatus(fallback.routing_diagnostics),/Lỗi định dạng phân loại sau 2 lần/);
assert.notEqual(historyAnswer(fallback),fallback.answer);
assert.match(historyAnswer(fallback),/chưa được giải đáp/);
const clarify={answer:'Bạn muốn hỏi thủ tục nào?',routing_diagnostics:{decision_reason:'ambiguous_question',routing_attempts:1}};
assert.match(routingStatus(clarify.routing_diagnostics),/Cần làm rõ câu hỏi/);
assert.equal(historyAnswer(clarify),clarify.answer);
assert.equal(routingStatus(undefined),'');
assert.equal(historyAnswer({answer:'Trả lời base'}),'Trả lời base');
`,{assert});
"""
        import json
        result = subprocess.run([shutil.which("node"), "-e", javascript],
                                input=json.dumps({"script": script, "helpers": helpers}),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
