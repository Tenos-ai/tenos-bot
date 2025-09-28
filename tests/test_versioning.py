"""Unit tests for utils.versioning helpers."""

import unittest

from utils.versioning import normalise_tag, is_remote_version_newer


class NormaliseTagTests(unittest.TestCase):
    def test_none_or_empty_returns_none(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                self.assertIsNone(normalise_tag(value))

    def test_strips_prefixes_and_v(self):
        self.assertEqual(normalise_tag("release-v1.2.3"), "1.2.3")
        self.assertEqual(normalise_tag("V2.0.0"), "2.0.0")

    def test_handles_mixed_separators(self):
        self.assertEqual(normalise_tag("release-2025_07-30"), "2025.07.30")

    def test_falls_back_to_digits_when_available(self):
        self.assertEqual(normalise_tag("release-qwen-image-v0.3beta"), "0.3")

    def test_returns_original_when_no_digits(self):
        self.assertEqual(normalise_tag("nightly"), "nightly")


class IsRemoteVersionNewerTests(unittest.TestCase):
    def test_remote_missing_returns_false(self):
        self.assertFalse(is_remote_version_newer(None, "1.2.3"))

    def test_current_missing_treats_remote_as_newer(self):
        self.assertTrue(is_remote_version_newer("v1.0.0", None))

    def test_detects_newer_semver(self):
        self.assertTrue(is_remote_version_newer("release-v1.4.0", "1.3.9"))

    def test_identical_versions_not_newer(self):
        self.assertFalse(is_remote_version_newer("v1.2.3", "1.2.3"))

    def test_pre_release_not_newer_than_release(self):
        self.assertFalse(is_remote_version_newer("v2.0.0-rc1", "2.0.0"))

    def test_remote_with_additional_components(self):
        self.assertTrue(is_remote_version_newer("release-2025.07.31", "v2025.07.30"))

    def test_non_numeric_fallbacks_to_string_compare(self):
        # 'alpha' < 'beta', so remote should not be considered newer
        self.assertFalse(is_remote_version_newer("alpha", "beta"))


if __name__ == "__main__":
    unittest.main()
