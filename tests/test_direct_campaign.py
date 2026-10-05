import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness.direct_campaign import (
    POLICY_PATH, PRIVATE_RELATIVE, claim_trial, digest, load_policy, local_key,
    private_json, public_bundle, readiness, select_condition, effective_config_sha256,
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

    def test_condition_profiles_are_isolated_and_change_only_run_call_limit(self):
        config = load_policy()
        config["comparison_conditions"] = {
            "calls12": {"max_run_calls": 12}, "calls24": {"max_run_calls": 24},
        }
        original = deepcopy(config)
        profiles = [select_condition(config, name) for name in ("calls12", "calls24")]
        self.assertEqual(config, original)
        self.assertEqual([p["max_run_calls"] for p in profiles], [12, 24])
        self.assertNotEqual(*(effective_config_sha256(p) for p in profiles))
        for profile in profiles:
            profile.pop("selected_condition")
            profile["max_run_calls"] = config["max_run_calls"]
            self.assertEqual(profile, config)
        profiles[0]["targets"]["gemini"]["model"] = "changed"
        self.assertEqual(config, original)
        self.assertEqual(select_condition(config), config)
        self.assertEqual(
            effective_config_sha256(config),
            effective_config_sha256(dict(reversed(list(config.items())))),
        )

    def test_malformed_condition_profiles_are_rejected_even_without_selection(self):
        for profiles in (
            [], {"other": {"max_run_calls": 12}},
            {"calls12": {"max_steps": 12}},
            {"calls12": {"max_run_calls": 12, "max_steps": 32}},
            {"calls12": None},
            *({"calls12": {"max_run_calls": value}} for value in (0, -1, True, 12.0, "12")),
        ):
            with self.subTest(profiles=profiles):
                config = load_policy()
                config["comparison_conditions"] = profiles
                with self.assertRaises(ValueError):
                    select_condition(config)
        with self.assertRaises(ValueError):
            select_condition({"comparison_conditions": {}}, "calls12")

    def test_private_release_requires_selected_authorized_frozen_condition(self):
        config = load_policy()
        config["price_valid_before"] = "9999-01-01"
        config["comparison_conditions"] = {
            "calls12": {"max_run_calls": 12}, "calls24": {"max_run_calls": 24},
        }
        calls12 = select_condition(config, "calls12")
        calls24 = select_condition(config, "calls24")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = {
                "policy_sha256": digest(POLICY_PATH.read_bytes()),
                "access_checks_authorized": True, "candidate_trials_authorized": True,
                "candidate_providers": ["gemini"], "candidate_conditions": ["calls12"],
                "authorized_condition_sha256": {
                    "calls12": effective_config_sha256(calls12),
                    "calls24": effective_config_sha256(calls24),
                },
                "accounts": {"gemini": {
                    "verified": True, "credential_sha256": digest(b"test-key"),
                    "valid_before": "9999-01-01T00:00:00+00:00",
                    "project": "Default Gemini Project",
                }},
            }
            private_json(root / PRIVATE_RELATIVE / "release.json", release)
            with patch("harness.direct_campaign.local_key", return_value="test-key"), \
                 patch("harness.direct_campaign.public_bundle", return_value={}):
                default = readiness(root, config, "gemini", execute=True)
                self.assertFalse(default["ready"])
                self.assertIn("Candidate condition not authorized", default["blockers"])
                unauthorized = readiness(root, calls24, "gemini", execute=True)
                self.assertIn("Candidate condition not authorized", unauthorized["blockers"])
                approved = readiness(root, calls12, "gemini", execute=True)
                self.assertTrue(approved["ready"])
                self.assertEqual(approved["selected_condition"], "calls12")
                self.assertEqual(approved["effective_config_sha256"],
                                 release["authorized_condition_sha256"]["calls12"])
                self.assertEqual(approved["authorized_condition_sha256"],
                                 release["authorized_condition_sha256"])
                changed = deepcopy(calls12)
                changed["workflow_instruction"] += "\nchanged shared setting"
                mismatch = readiness(root, changed, "gemini", execute=True)
                self.assertFalse(mismatch["ready"])
                self.assertIn("Selected condition is not bound to the effective configuration",
                              mismatch["blockers"])
                # Even an access probe with a named condition uses its frozen shared settings.
                self.assertFalse(readiness(root, changed, "gemini")["ready"])
                forged = deepcopy(calls12)
                forged["max_run_calls"] = 24
                self.assertIn("Effective condition configuration does not match its profile",
                              readiness(root, forged, "gemini", execute=True)["blockers"])
                release.pop("candidate_conditions")
                release.pop("authorized_condition_sha256")
                private_json(root / PRIVATE_RELATIVE / "release.json", release)
                self.assertTrue(readiness(root, config, "gemini", execute=True)["ready"])
                self.assertFalse(readiness(root, calls12, "gemini", execute=True)["ready"])

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
