"""Exercise browser routing labels/history helpers without a running server."""
from tests.dependencies import skip_missing_dependency  # noqa: F401

from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is needed to verify browser JavaScript")
class WebUITests(unittest.TestCase):
    def test_stream_keeps_context_per_model_and_reset_clears_both(self):
        import json
        path = Path(__file__).resolve().parents[1] / "src/vigovbot/server/static/index.html"
        script = path.read_text(encoding="utf-8").split("<script>", 1)[1].split("</script>", 1)[0]
        helpers = script[script.index("function modeLabel"):script.index("function addAnswers")]
        reset = script[script.index("function resetConversation"):script.index("document.querySelector('#new-chat')")]
        javascript = """
const vm=require('node:vm'),assert=require('node:assert/strict');
const code=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const histories={a:[],b:[]},retrievalContexts={a:null,b:{source_code:'b'}},clarificationContexts={a:null,b:{kind:'procedure'}};
const element=()=>({append(){},textContent:''});
const card={body:element(),el:element()};
const chat={replaceChildren(){this.cleared=true},scrollHeight:0},input={focus(){}},button={disabled:false};
vm.runInNewContext(code.helpers+code.reset+`
applyStreamEvent({type:'model_result',result:{model_id:'a',answer:'A',retrieval_context:{source_code:'a'},clarification_context:{kind:'section'}}},{a:card},'Q');
assert.equal(retrievalContexts.a.source_code,'a');
assert.equal(retrievalContexts.b.source_code,'b');
assert.equal(clarificationContexts.a.kind,'section');assert.equal(clarificationContexts.b.kind,'procedure');assert.equal(histories.a.length,2);assert.equal(histories.b.length,0);
applyStreamEvent({type:'model_result',result:{model_id:'a',answer:'Clarify'}},{a:card},'Q2');
assert.equal(retrievalContexts.a,null);assert.equal(clarificationContexts.a,null);
button.disabled=true;resetConversation();assert.equal(histories.a.length,4);
button.disabled=false;resetConversation();
assert.equal(histories.a.length,0);assert.equal(histories.b.length,0);
assert.equal(retrievalContexts.a,null);assert.equal(clarificationContexts.a,null);assert.equal(retrievalContexts.b,null);assert.equal(clarificationContexts.b,null);assert.ok(chat.cleared);
`,{assert,histories,retrievalContexts,clarificationContexts,card,chat,input,button,document:{createElement:element}});
"""
        result = subprocess.run([shutil.which("node"), "-e", javascript],
                                input=json.dumps({"helpers": helpers, "reset": reset}),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_syntax_and_fallback_history(self):
        path = Path(__file__).resolve().parents[1] / "src/vigovbot/server/static/index.html"
        script = path.read_text(encoding="utf-8").split("<script>", 1)[1].split("</script>", 1)[0]
        helpers = script[script.index("function modeLabel"):script.index("function addAnswers")]
        javascript = """
const vm=require('node:vm'),assert=require('node:assert/strict');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
new vm.Script(input.script);
vm.runInNewContext(input.helpers+`
assert.equal(modeLabel('base'),'không truy hồi');
assert.equal(modeLabel('rag'),'có truy hồi');
assert.match(modeLabel('qlora'),/QLoRA/);
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
assert.equal(contextMeta({faiss_rank:1,source_code:'1.116222',section_type:'metadata_identity',faiss_score:0.25},0),'Hạng 1 · Mã 1.116222 · Mục metadata_identity · FAISS 0.2500');
`,{assert});
"""
        import json
        result = subprocess.run([shutil.which("node"), "-e", javascript],
                                input=json.dumps({"script": script, "helpers": helpers}),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
