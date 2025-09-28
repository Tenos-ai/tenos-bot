import sys
import types
import unittest
from unittest.mock import patch


class _MockSelectOption:
    def __init__(self, label: str | None = None, value: str | None = None, default: bool = False):
        self.label = label
        self.value = value
        self.default = default


if 'discord' not in sys.modules:
    sys.modules['discord'] = types.SimpleNamespace(SelectOption=_MockSelectOption)

if 'numpy' not in sys.modules:
    def _mock_arange(start, stop=None, step=1.0):
        if stop is None:
            stop = float(start)
            start = 0.0
        start = float(start)
        stop = float(stop)
        step = float(step)
        values = []
        current = start
        # mimic numpy.arange without including stop when step does not divide evenly
        if step > 0:
            condition = lambda val: val < stop - 1e-9
        else:
            condition = lambda val: val > stop + 1e-9
        while condition(current):
            values.append(current)
            current += step
        return values

    sys.modules['numpy'] = types.SimpleNamespace(arange=_mock_arange)

import settings_manager


class ResolveModelForTypeTests(unittest.TestCase):
    def test_returns_preferred_model_when_present(self):
        settings = {
            'preferred_model_flux': 'Flux: PreferredFlux',
            'selected_model': 'SDXL: OtherModel',
        }
        result = settings_manager.resolve_model_for_type(settings, 'flux')
        self.assertEqual(result, 'Flux: PreferredFlux')

    def test_falls_back_to_selected_model_if_types_match(self):
        settings = {
            'selected_model': 'SDXL: DreamShaper',
        }
        with patch('settings_manager.get_available_models_for_type', return_value=['BackupModel']):
            result = settings_manager.resolve_model_for_type(settings, 'sdxl')
        self.assertEqual(result, 'SDXL: DreamShaper')

    def test_uses_available_models_when_no_preference_stored(self):
        settings = {
            'selected_model': 'Flux: BaseModel',
        }
        with patch('settings_manager.get_available_models_for_type', return_value=['PrimarySDXL', 'Other']):
            result = settings_manager.resolve_model_for_type(settings, 'sdxl')
        self.assertEqual(result, 'SDXL: PrimarySDXL')

    def test_returns_none_when_no_models_available(self):
        settings = {}
        with patch('settings_manager.get_available_models_for_type', return_value=[]):
            result = settings_manager.resolve_model_for_type(settings, 'sdxl')
        self.assertIsNone(result)

    def test_resolves_qwen_model_from_available_list(self):
        settings = {}
        with patch('settings_manager.get_available_models_for_type', return_value=['QwenLocal.ckpt']):
            result = settings_manager.resolve_model_for_type(settings, 'qwen')
        self.assertEqual(result, 'Qwen: QwenLocal.ckpt')


if __name__ == '__main__':
    unittest.main()
