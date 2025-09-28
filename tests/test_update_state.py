import json
import os
import tempfile
import unittest

from utils.update_state import UpdateState


class UpdateStateTests(unittest.TestCase):
    def test_load_defaults_when_missing(self):
        state = UpdateState.load(base_dir=tempfile.mkdtemp())
        self.assertIsNone(state.last_successful_tag)
        self.assertIsNone(state.pending_tag)

    def test_mark_pending_and_success_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = UpdateState.load(base_dir=tmp)
            state.mark_pending("v1.2.3", base_dir=tmp)
            with open(os.path.join(tmp, "update_state.json"), "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(payload["pending_tag"], "v1.2.3")
            self.assertIsNone(payload["last_successful_tag"])

            state = UpdateState.load(base_dir=tmp)
            state.mark_success("v1.2.3", base_dir=tmp)
            state = UpdateState.load(base_dir=tmp)
            self.assertEqual(state.last_successful_tag, "v1.2.3")
            self.assertIsNone(state.pending_tag)


if __name__ == "__main__":
    unittest.main()
