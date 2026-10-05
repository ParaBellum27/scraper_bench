import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness.direct_campaign import (
    POLICY_PATH, PRIVATE_RELATIVE, claim_trial, digest, load_policy, local_key,
    private_json, public_bundle, readiness,
)


class CampaignTests(unittest.TestCase):
    def test_local_key_never_uses_export_or_interpolates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict("os.environ", {"GEMINI_API_KEY": "exported-secret"}):
                (root / ".env").write_text("GEMINI_API_KEY=local-secret\n")
                self.assertEqual(local_key(root, "GEMINI_API_KEY"), "local-secret")
                (root / ".env").write_text("GEMINI_API_KEY=${GEMINI_API_KEY}\n")
                with self.assertRaises(ValueError):
                    local_key(root, "GEMINI_API_KEY")
                (root / ".env").write_text("")
                with self.assertRaises(ValueError):
                    local_key(root, "GEMINI_API_KEY")

    def test_claim_survives_later_runs_and_counts_failed_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claim_trial(root, "gemini", "first-attempt", 1)
            with self.assertRaises(FileExistsError):
                claim_trial(root, "gemini", "different-run-id", 1)
            self.assertEqual(json.loads((root / "gemini-trial-claim.json").read_text())["run_id"], "first-attempt")
            claim_trial(root, "gemini", "authorized-second-attempt", 2)
            self.assertEqual(json.loads((root / "gemini-trial-claim.json").read_text())["run_id"], "first-attempt")
            self.assertEqual(json.loads((root / "gemini-trial-claim-02.json").read_text())["run_id"], "authorized-second-attempt")
            with self.assertRaises(FileExistsError):
                claim_trial(root, "gemini", "unauthorized-third-attempt", 2)

    def test_key_rotation_requires_new_account_confirmation_and_execution_is_separate(self):
        config = load_policy()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("GEMINI_API_KEY=current-key\n")
            release = {
                "policy_sha256": digest(POLICY_PATH.read_bytes()),
                "access_checks_authorized": True, "candidate_trials_authorized": False,
                "accounts": {"gemini": {"verified": True, "credential_sha256": digest(b"current-key"),
                    "valid_before": "9999-01-01T00:00:00+00:00", "project": "Default Gemini Project"}},
            }
            private_json(root / PRIVATE_RELATIVE / "release.json", release)
            config["price_valid_before"] = "9999-01-01"
            with patch("harness.direct_campaign.public_bundle", return_value={}):
                self.assertTrue(readiness(root, config, "gemini")["ready"])
                self.assertIn("Candidate trials not authorized", readiness(root, config, "gemini", execute=True)["blockers"])
                release.update(candidate_trials_authorized=True, candidate_providers=["groq"])
                private_json(root / PRIVATE_RELATIVE / "release.json", release)
                self.assertIn("Candidate trials not authorized", readiness(root, config, "gemini", execute=True)["blockers"])
                release["candidate_providers"] = ["gemini"]
                private_json(root / PRIVATE_RELATIVE / "release.json", release)
                self.assertTrue(readiness(root, config, "gemini", execute=True)["ready"])
                (root / ".env").write_text("GEMINI_API_KEY=replacement-key\n")
                self.assertIn("Current local key differs from confirmed account key", readiness(root, config, "gemini")["blockers"])

    def test_modified_public_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {"task.md": b"task", "pierre_lbo_one.xlsx": b"workbook", "inputs/base_case.json": b"{}"}
            for name, data in files.items():
                path = root / name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(data)
            (root / "metadata.json").write_text(json.dumps({"public_artifact_sha256": {n: digest(d) for n, d in files.items()}}))
            self.assertEqual(public_bundle(root, {"public_metadata": "metadata.json"}), files)
            (root / "task.md").write_bytes(b"different-task")
            with self.assertRaisesRegex(ValueError, "Frozen public artifact changed"):
                public_bundle(root, {"public_metadata": "metadata.json"})


if __name__ == "__main__":
    unittest.main()
