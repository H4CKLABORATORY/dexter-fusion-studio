"""TokenLab context/skills functional regression tests; tokenizer is genuine tiktoken."""
import tempfile
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from fusion.tokenlab_context import GestorContexto, deduplicate, prioritize, cosine
from fusion.tokenlab_skills import RegistroSkills

class TokenLabFullTests(unittest.TestCase):
    def test_three_layers_permanent_and_checkpoint(self):
        c=GestorContexto("Regla inmutable: conservar Dexter.",2048)
        before=c.add("user","Primer mensaje")
        self.assertEqual(before["memoria_permanente"],"Regla inmutable: conservar Dexter.")
        c.add("assistant","Respuesta")
        state=c.export()
        new=GestorContexto("Regla inmutable: conservar Dexter.",2048)
        new.restore(state)
        self.assertEqual(new.export()["ventana_volatil"],state["ventana_volatil"])
        with self.assertRaises(ValueError):
            GestorContexto("Regla distinta",2048).restore(state)

    def test_overflow_atomic_without_real_summarizer(self):
        c=GestorContexto("Permanente",512,reserva_respuesta=64)
        old=c.export()
        with self.assertRaises((RuntimeError,ValueError)):
            c.add("user","A"*20000)
        self.assertEqual(c.export(),old)

    def test_sha256_and_semantic_dedup_fact_guards(self):
        fragments=["Ganancia 10.","Ganancia 10.","Ganancia 11.","No autorizar","Autorizar"]
        vectors=[[1,0],[1,0],[1,0],[0,1],[0,1]]
        self.assertEqual(deduplicate(fragments,vectors),["Ganancia 10.","Ganancia 11.","No autorizar","Autorizar"])
        self.assertEqual(deduplicate(fragments),["Ganancia 10.","Ganancia 11.","No autorizar","Autorizar"])
        self.assertAlmostEqual(cosine([1,0],[1,0]),1)

    def test_priority_weights_and_budget(self):
        candidates=[
          {"text":"reciente","embedding":[1,0],"recency":1.0,"importance":0.0},
          {"text":"importante","embedding":[0,1],"recency":0.0,"importance":1.0}
        ]
        result=prioritize(candidates,[1,0],256)
        self.assertEqual(result["selected"][0]["text"],"reciente")
        self.assertLessEqual(result["total_tokens"],result["budget"])

    def test_four_skills_return_json_even_on_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,"module.py").write_text("def fusion():\n    return 2\n",encoding="utf-8")
            skills=RegistroSkills(tmp)
            self.assertEqual(len(skills.specifications()),4)
            def call(name,**params):
                return json.loads(skills.execute_json(name,{"max_results":5,"max_tokens":1024,**params}))
            self.assertTrue(call("buscar_repositorio",query="fusion")["ok"])
            self.assertTrue(call("contar_tokens",texto="Hola")["ok"])
            self.assertTrue(call("comparar_prompts",a="Hola",b="Hola mundo")["ok"])
            self.assertFalse(call("resumir",texto="Hola")["ok"])
            invalid=skills.execute("contar_tokens",{"texto":"hola","max_results":5,"max_tokens":5})
            self.assertFalse(invalid["ok"])
            self.assertEqual(invalid["error"]["code"],"ValueError")
            self.assertIn("Límites inválidos",invalid["error"]["message"])

    def test_model_change_invalidates_skill_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg=RegistroSkills(tmp,model="gpt-4o")
            params={"texto":"hola","max_results":5,"max_tokens":512}
            def fake_tokens(text,model):
                return 20 if text.startswith("{") else (3 if model=="gpt-4o" else 5)
            with patch("fusion.tokenlab_skills.tokens",side_effect=fake_tokens):
                self.assertEqual(reg.execute("contar_tokens",params)["data"]["tokens"],3)
                reg.model="gpt-4.1"
                self.assertEqual(reg.execute("contar_tokens",params)["data"]["tokens"],5)
                self.assertEqual(len(reg.cache),2)

    def test_local_ollama_adapter_rejects_redirecting_url_userinfo(self):
        import os
        from fusion.tokenlab_ollama import _url
        for bad in ("http://127.0.0.1:11434@evil.example",
                    "http://evil.example:11434",
                    "https://127.0.0.1:11434",
                    "http://localhost:11434/api",
                    "http://user:pass@localhost:11434"):
            with self.subTest(url=bad):
                with patch.dict(os.environ, {"OLLAMA_URL":bad}):
                    with self.assertRaises(ValueError):
                        _url()
        with patch.dict(os.environ, {"OLLAMA_URL":"http://127.0.0.1:11434"}):
            self.assertEqual(_url(),"http://127.0.0.1:11434")

    def test_search_finds_markdown_and_javascript_but_skips_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,"guide.md").write_text("TOKENLAB_NEEDLE in docs",encoding="utf-8")
            Path(tmp,"main.js").write_text("const x = 'TOKENLAB_NEEDLE';",encoding="utf-8")
            ignored=Path(tmp,"node_modules")
            ignored.mkdir()
            Path(ignored,"ignored.js").write_text("TOKENLAB_NEEDLE",encoding="utf-8")
            reg=RegistroSkills(tmp)
            result=reg.execute("buscar_repositorio",
                {"query":"TOKENLAB_NEEDLE","max_results":12,"max_tokens":512})
            self.assertTrue(result["ok"],result)
            paths={r["path"] for r in result["data"]["matches"]}
            self.assertEqual(paths,{"guide.md","main.js"})
            self.assertEqual(result["data"]["scanned_files"],2)

try:
    from PySide6.QtWidgets import QApplication
    from fusion.tokenlab_dialog import TokenLabDialog
except ImportError:
    QApplication=None

@unittest.skipIf(QApplication is None,"Qt tested in dedicated runner")
class FullQtSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_workspace_visible(self):
        dialog=TokenLabDialog()
        try:
            self.assertEqual(dialog.workspace.tabs.count(),4)
            dialog.workspace.new_context()
            dialog.workspace.message.setPlainText("Hola")
            dialog.workspace.add_message()
            self.assertIn("Hola",dialog.workspace.volatile.toPlainText())
            dialog.workspace.dup_lines.setPlainText("Doble\nDoble\nÚnico")
            dialog.workspace.run_dedup()
            self.assertEqual(dialog.workspace.dup_result.toPlainText().splitlines(),["Doble","Único"])
        finally:dialog.close()
    def test_session_switch_and_restore_are_safe_during_compaction(self):
        dialog=TokenLabDialog()
        try:
            ui=dialog.workspace
            ui.new_context()
            manager=ui.manager
            saved=manager.export()
            ui.storage=type("Storage",(),{"load":lambda self,task:saved})()
            ui.compactor.pending={"ventana_volatil":[{"role":"user","content":"active"}]}
            ui.permanent.setPlainText("Nueva regla")
            ui.new_context()
            self.assertIs(ui.manager,manager)
            ui.restore_context()
            self.assertIs(ui.manager,manager)
            self.assertEqual(manager.memoria_permanente,saved["memoria_permanente"])
            ui.compactor.pending=None
            ui.restore_context()
            self.assertEqual(ui.permanent.toPlainText(),saved["memoria_permanente"])
            self.assertEqual(ui.manager.export()["ventana_volatil"],saved["ventana_volatil"])
        finally:
            ui.compactor.pending=None
            dialog.close()

    def test_each_skill_ui_starts_with_valid_schema(self):
        dialog=TokenLabDialog()
        try:
            ui=dialog.workspace
            expected={
                "buscar_repositorio":{"query","max_results","max_tokens"},
                "resumir":{"texto","max_results","max_tokens"},
                "contar_tokens":{"texto","max_results","max_tokens"},
                "comparar_prompts":{"a","b","max_results","max_tokens"}
            }
            for name,keys in expected.items():
                ui.skill_select.setCurrentText(name)
                data=json.loads(ui.skill_args.toPlainText())
                self.assertEqual(set(data),keys)
                self.assertGreaterEqual(data["max_tokens"],64)
        finally:
            dialog.close()

    def test_bad_checkpoint_never_replaces_live_session(self):
        dialog=TokenLabDialog()
        try:
            ui=dialog.workspace
            ui.new_context()
            original=ui.manager
            original_text=ui.permanent.toPlainText()
            ui.storage=type("InvalidStorage",(),{"load":lambda self,task:{"memoria_permanente":"Otra regla","resumen_sesion":"oops","ventana_volatil":[{"role":"tool","content":3}]}})()
            ui.restore_context()
            self.assertIs(ui.manager,original)
            self.assertEqual(ui.permanent.toPlainText(),original_text)
            self.assertIn("ERROR",ui.mem_info.text())
        finally:
            dialog.close()
