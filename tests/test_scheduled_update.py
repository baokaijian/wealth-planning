import subprocess
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scheduled_update import restore_if_only_metadata_changed, run_with_retry


class ScheduledUpdateTests(unittest.TestCase):
    def test_retries_a_failed_network_step_until_success(self):
        runner = Mock(side_effect=[
            subprocess.CompletedProcess(["update"], 1),
            subprocess.CompletedProcess(["update"], 1),
            subprocess.CompletedProcess(["update"], 0),
        ])
        sleeper = Mock()

        run_with_retry(["update"], attempts=3, base_delay=2, runner=runner, sleeper=sleeper)

        self.assertEqual(runner.call_count, 3)
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [2, 4])

    def test_raises_after_all_attempts_fail(self):
        runner = Mock(return_value=subprocess.CompletedProcess(["update"], 1))

        with self.assertRaises(subprocess.CalledProcessError):
            run_with_retry(["update"], attempts=2, base_delay=0, runner=runner, sleeper=Mock())

    def test_rejects_invalid_attempt_count(self):
        with self.assertRaises(ValueError):
            run_with_retry(["update"], attempts=0, runner=Mock(), sleeper=Mock())

    def test_restores_file_when_only_generated_timestamp_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            before = {"data": {"price": 1.0}, "quality": {"generated_at": "old", "alerts": []}}
            after = {"data": {"price": 1.0}, "quality": {"generated_at": "new", "alerts": []}}
            original_text = json.dumps(before, ensure_ascii=False, indent=2) + "\n"
            path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            restored = restore_if_only_metadata_changed(path, original_text, ("quality", "generated_at"))

            self.assertTrue(restored)
            self.assertEqual(path.read_text(encoding="utf-8"), original_text)

    def test_keeps_file_when_market_data_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            before = {"data": {"price": 1.0}, "quality": {"generated_at": "old"}}
            after = {"data": {"price": 1.1}, "quality": {"generated_at": "new"}}
            original_text = json.dumps(before)
            updated_text = json.dumps(after)
            path.write_text(updated_text, encoding="utf-8")

            restored = restore_if_only_metadata_changed(path, original_text, ("quality", "generated_at"))

            self.assertFalse(restored)
            self.assertEqual(path.read_text(encoding="utf-8"), updated_text)


if __name__ == "__main__":
    unittest.main()
