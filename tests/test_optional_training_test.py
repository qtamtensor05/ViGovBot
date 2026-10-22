import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.dependencies import skip_missing_dependency

try:
    from vigovbot.training.config import load_config
    from vigovbot.training.data import dataset_paths
    from vigovbot.training.schema import Splits
    from vigovbot.training.train import _prepare_training_data
    from vigovbot.training.control_cli import validate_launch
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class OptionalTestSplitTests(unittest.TestCase):
    def test_evaluator_rejects_unconfigured_test_before_loading_model(self):
        from vigovbot.training.evaluate import evaluate
        config = load_config('configs/training/experiments/golden_sft.yaml')
        with patch('vigovbot.training.evaluate.load_config', return_value=config), \
             patch('vigovbot.training.evaluate.load_model') as model:
            with self.assertRaisesRegex(ValueError, "Split 'test' is not configured"):
                evaluate('unused', split='test')
            model.assert_not_called()

    def test_profiles_and_omitted_test(self):
        golden = load_config('configs/training/experiments/golden_sft.yaml')
        self.assertEqual(set(dataset_paths(golden)), {'train', 'validation'})
        self.assertIn('golden_dataset_sft', str(dataset_paths(golden)['train']))
        legacy = load_config('configs/training/base.yaml')
        self.assertEqual(set(dataset_paths(legacy)), {'train', 'validation', 'test'})
        splits = Splits(train='train.jsonl', validation='val.jsonl')
        self.assertIsNone(splits.test)
        self.assertNotIn('test', splits.model_dump(exclude_unset=True))

    def test_prepare_and_launch_two_or_three_splits(self):
        for with_test in (False, True):
            with self.subTest(with_test=with_test), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                names = ['train', 'validation'] + (['test'] if with_test else [])
                paths = {}
                for name in names:
                    paths[name] = root / f'{name}.jsonl'
                    paths[name].write_text(json.dumps({'id': name, 'messages': [
                        {'role': 'user', 'content': 'question'},
                        {'role': 'assistant', 'content': 'answer'}]}) + '\n', encoding='utf-8')
                config = load_config('configs/training/experiments/golden_sft.yaml')
                config.data.output_dir = str(root / 'runs')
                with patch('vigovbot.training.train.dataset_paths', return_value=paths):
                    train, val, hashes, run, _, _ = _prepare_training_data(config, None, 'fixture')
                self.assertEqual((len(train), len(val)), (1, 1))
                self.assertEqual(set(hashes), set(names))
                report = json.loads((run / 'dataset_report.json').read_text(encoding='utf-8'))
                self.assertEqual(set(report['splits']), set(names))
                environment = {'cuda_available': True, 'gpu': 'fixture',
                               'cuda_version': 'fixture', 'vram_bytes': 1}
                with patch('vigovbot.training.control_cli.load_config', return_value=config), \
                     patch('vigovbot.training.control_cli.dataset_paths', return_value=paths), \
                     patch('vigovbot.training.control_cli.inspect_environment', return_value=environment):
                    launch = validate_launch('fixture')
                self.assertEqual(launch['dataset_hashes'], hashes)

    def test_missing_configured_test_still_fails(self):
        config = load_config('configs/training/base.yaml')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.jsonl'
            with patch('vigovbot.training.train.dataset_paths', return_value={
                    'train': path, 'validation': path, 'test': path}), \
                 patch('vigovbot.training.train.read_jsonl', side_effect=[[], [], FileNotFoundError('test')]):
                with self.assertRaises(FileNotFoundError):
                    _prepare_training_data(config, None, None)

    def test_two_split_resume_preserves_hash_contract(self):
        import yaml
        from vigovbot.training.checkpoints import validate_resume_checkpoint
        config = load_config('configs/training/experiments/golden_sft.yaml')
        hashes = {'train': 'abc', 'validation': 'def'}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            checkpoint = root / 'checkpoints' / 'checkpoint-1'
            checkpoint.mkdir(parents=True)
            for name in ('optimizer.pt', 'scheduler.pt', 'rng_state.pth', 'adapter_model.safetensors'):
                (checkpoint / name).write_bytes(b'fixture')
            (checkpoint / 'trainer_state.json').write_text(
                json.dumps({'global_step': 1, 'stateful_callbacks': {}}), encoding='utf-8')
            (root / 'config.yaml').write_text(yaml.safe_dump(config.snapshot()), encoding='utf-8')
            (root / 'environment.json').write_text(json.dumps({'dataset_hashes': hashes}), encoding='utf-8')
            self.assertEqual(validate_resume_checkpoint(checkpoint, config, hashes), checkpoint)
            for changed in ({**hashes, 'train': 'changed'}, {**hashes, 'test': 'legacy'}):
                with self.assertRaisesRegex(ValueError, 'Dataset hashes'):
                    validate_resume_checkpoint(checkpoint, config, changed)
