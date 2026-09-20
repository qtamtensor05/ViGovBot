import json
import ast
import tempfile
import unittest
from pathlib import Path
import yaml

from src.configuration import load_configuration, PROJECT_ROOT
from src.ingestion.parse import parse_pdf_to_hybrid_data


class ConfigurationTests(unittest.TestCase):
    def test_custom_configuration_controls_output_chunking_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for source, dest in [('config.yaml', 'config.yaml'), ('src/ingestion/config.yaml', 'ingestion.yaml'), ('src/chunking/config.yaml', 'chunking.yaml')]:
                data = yaml.safe_load((PROJECT_ROOT / source).read_text(encoding='utf-8'))
                if dest == 'config.yaml':
                    data['modules'] = {'ingestion': 'ingestion.yaml', 'chunking': 'chunking.yaml'}
                    data['output'] = 'results'
                elif dest == 'ingestion.yaml':
                    data['reports_dir'] = 'audit'
                else:
                    data.update(target_chars=350, max_chars=500, overlap_chars=50)
                (base / dest).write_text(yaml.safe_dump(data), encoding='utf-8')
            config = base / 'config.yaml'
            root, _, _ = load_configuration(config)
            self.assertEqual(root.output, base / 'results')
            pdf = base / '1.000005.pdf'
            pdf.write_bytes(b'%PDF-1.4')
            output, _ = parse_pdf_to_hybrid_data(pdf, config_path=config,
                markdown_converter=lambda _: '# Thủ tục mẫu\nMã: 1.000005\n' + 'Nội dung dài cần xử lý. ' * 200)
            chunks = json.loads(output.read_text(encoding='utf-8'))
            self.assertTrue(all(len(c['text_content']) <= 500 for c in chunks))
            self.assertTrue((base / 'results/audit/1.000005.json').is_file())

    def test_notebook_cells_compile(self):
        notebook = json.loads((PROJECT_ROOT / 'ipynb/main.ipynb').read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                code = ''.join(cell['source'])
                if not code.lstrip().startswith('%'):
                    ast.parse(code)
