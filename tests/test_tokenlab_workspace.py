"""TokenLab context/skills functional regression tests; tokenizer is genuine tiktoken."""
import tempfile
import json
import unittest
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
            self.assertFalse(skills.execute("contar_tokens",{"texto":"hola","max_results":5,"max_tokens":5})["ok"])

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
