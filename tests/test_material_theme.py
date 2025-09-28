import unittest

from material_gui.theme import build_stylesheet


class ThemeBuilderTests(unittest.TestCase):
    def test_builds_named_palette(self):
        sheet = build_stylesheet(
            mode="dark",
            palette_key="oceanic",
            custom_primary="#2563EB",
            custom_surface="#0F172A",
            custom_text="#F1F5F9",
        )
        self.assertIn("#0F172A", sheet)
        self.assertIn("#38BDF8", sheet)

    def test_builds_custom_palette(self):
        sheet = build_stylesheet(
            mode="light",
            palette_key="custom",
            custom_primary="ff0000",
            custom_surface="#fefefe",
            custom_text="#101010",
        )
        self.assertIn("#FF0000", sheet)
        self.assertIn("background: #FEFEFE", sheet)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
