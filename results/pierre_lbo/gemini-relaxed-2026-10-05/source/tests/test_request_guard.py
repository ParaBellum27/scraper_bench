from datetime import datetime, timezone
from email.message import Message
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error

from harness.request_guard import GuardError, GuardedTransport


def policy(**changes):
    value = {
        "provider": "mistral", "model": "mistral-medium-latest",
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "rpm": 100, "tpm": 100000, "tpm_scope": "combined", "rpd": None, "tpd": None,
        "min_interval_seconds": 0, "input_limit": 1000, "output_limit": 100,
        "input_usd_per_million": "1", "output_usd_per_million": "2",
        "spend_cap_usd": "1", "request_timeout_seconds": 180, "max_retries": 2,
    }
    value.update(changes)
    return value


def payload(**changes):
    value = {"model": "mistral-medium-latest", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 100}
    value.update(changes)
    return value


def completion(input_tokens=100, output_tokens=20, **usage_changes):
    usage = {"prompt_tokens": input_tokens, "completion_tokens": output_tokens,
             "total_tokens": input_tokens + output_tokens}
    usage.update(usage_changes)
    return {"model": "mistral-medium-latest", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}], "usage": usage}


class Clock:
    def __init__(self):
        self.value = 0.0
        self.epoch = 1_800_000_000.0
        self.sleeps = []

    def monotonic(self):
        return self.value

    def wall(self):
        return self.epoch + self.value

    def sleep(self, delay):
        self.sleeps.append(delay)
        self.value += delay


class Response(BytesIO):
    def __init__(self, value):
        super().__init__(value if isinstance(value, bytes) else json.dumps(value).encode())

    def getcode(self):
        return 200


class Opener:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        if callable(result):
            result = result(request)
        return result if isinstance(result, Response) else Response(result)


def rejection(status, retry_after=None, *, daily=False):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    if daily:
        headers["x-ratelimit-remaining-requests-day"] = "0"
    return urllib.error.HTTPError("https://secret.invalid/secret-key", status,
                                  "credential: secret-key", headers, BytesIO(b"Authorization: secret-key"))


class RequestGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = Path(self.directory.name) / "campaign.json"
        self.clock = Clock()

    def guard(self, opener=None, *, run_id="trial-1", deadline=100000, **changes):
        return GuardedTransport(policy(**changes), "secret-key", self.ledger,
                                deadline, run_id, clock=self.clock.monotonic,
                                wall_clock=self.clock.wall, sleep=self.clock.sleep,
                                opener=opener or Opener(completion()))

    def assertCategory(self, category, operation):
        with self.assertRaises(GuardError) as error:
            operation()
        self.assertEqual(error.exception.category, category)
        return str(error.exception)

    def test_reservation_is_fsynced_before_send_and_settles_exact_usage(self):
        def inspect(request):
            record = json.loads(self.ledger.read_text())["providers"]["mistral"]
            self.assertEqual(record["reserved_units"], 1_200_000_000)
            self.assertEqual(record["attempts"][0]["state"], "reserved")
            self.assertEqual(record["attempts"][0]["run_id"], "trial-1")
            self.assertGreater(fsync.call_count, 0)
            return completion(completion_tokens_details={"reasoning_tokens": 15})

        with patch("harness.request_guard.os.fsync", wraps=__import__("os").fsync) as fsync:
            with self.guard(Opener(inspect)) as guard:
                self.assertEqual(guard.post(payload(), max_output_tokens=100)["usage"]["completion_tokens"], 20)
                totals = guard.summary()
                self.assertEqual(totals["consumed_units"], 140_000_000)
                self.assertEqual(totals["reserved_units"], 0)
                self.assertEqual(totals["consumed_usd"], "0.00014")
        self.assertEqual(self.ledger.stat().st_mode & 0o777, 0o600)

    def test_cap_persists_across_run_ids_and_restart_without_float_drift(self):
        exhausted = completion(1000, 100)
        with self.guard(Opener(exhausted), spend_cap_usd="0.0012") as guard:
            guard.post(payload(), max_output_tokens=100)
            self.assertEqual(guard.summary()["remaining_units"], 0)
        opener = Opener(exhausted)
        with self.guard(opener, run_id="access-check-next", spend_cap_usd="0.0012") as guard:
            self.assertCategory("budget", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertEqual(guard.summary()["attempts"], 1)
            self.assertEqual(guard.summary()["run_attempts"], 0)
        self.assertEqual(opener.calls, [])

    def test_ambiguous_timeout_holds_full_cost_across_restart_and_never_retries(self):
        opener = Opener(TimeoutError("Authorization secret-key"), completion())
        with self.guard(opener, spend_cap_usd="0.0012") as guard:
            message = self.assertCategory("provider", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertNotIn("secret-key", message)
            self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
            self.assertEqual(guard.summary()["consumed_units"], 0)
        with self.guard(run_id="restart", spend_cap_usd="0.0012") as guard:
            self.assertCategory("budget", lambda: guard.post(payload(), max_output_tokens=100))
        self.assertEqual(len(opener.calls), 1)
        self.assertNotIn("secret-key", self.ledger.read_text())
        self.assertNotIn("Authorization", self.ledger.read_text())

    def test_explicit_cap_increase_preserves_spend_and_uncertain_holds_across_restart(self):
        with self.guard(Opener(completion(), TimeoutError())) as guard:
            guard.post(payload(), max_output_tokens=100)
            self.assertCategory("provider", lambda: guard.post(payload(), max_output_tokens=100))
            before = guard.summary()
            attempts = json.loads(self.ledger.read_text())["providers"]["mistral"]["attempts"]
            guard.raise_spend_cap("2", authorization="User explicitly authorized the higher cumulative cap")
            after = guard.summary()
            self.assertEqual(after["consumed_units"], before["consumed_units"])
            self.assertEqual(after["reserved_units"], before["reserved_units"])
            self.assertEqual(after["spend_cap_usd"], "2")
            self.assertEqual(json.loads(self.ledger.read_text())["providers"]["mistral"]["attempts"], attempts)
        with self.guard(run_id="restart", spend_cap_usd="2") as guard:
            self.assertEqual(guard.summary()["committed_units"], before["committed_units"])
            self.assertEqual(guard.summary()["attempts"], 2)
        self.assertCategory("infrastructure", lambda: self.guard(spend_cap_usd="1").__enter__())

    def test_cap_change_requires_explicit_increase_and_never_accepts_repricing(self):
        with self.guard() as guard:
            for cap, authorization in (("1", "approved"), ("0.5", "approved"), ("2", "")):
                category = "infrastructure" if not authorization else "budget"
                self.assertCategory(category, lambda: guard.raise_spend_cap(cap, authorization=authorization))
            self.assertEqual(guard.summary()["spend_cap_usd"], "1")
        self.assertCategory("infrastructure", lambda: self.guard(spend_cap_usd="2", input_usd_per_million="0").__enter__())

    def test_interruption_retains_presend_attempt_without_releasing(self):
        with self.guard(Opener(KeyboardInterrupt()), spend_cap_usd="0.0012") as guard:
            with self.assertRaises(KeyboardInterrupt):
                guard.post(payload(), max_output_tokens=100)
        record = json.loads(self.ledger.read_text())["providers"]["mistral"]
        self.assertEqual(record["attempts"][0]["state"], "reserved")
        with self.guard(run_id="restart", spend_cap_usd="0.0012") as guard:
            self.assertCategory("budget", lambda: guard.post(payload(), max_output_tokens=100))

    def test_retry_after_numeric_and_date_each_have_separate_durable_hold(self):
        http_date = format_datetime(datetime.fromtimestamp(self.clock.wall() + 7, timezone.utc), usegmt=True)
        opener = Opener(rejection(429, 2), rejection(429, http_date), completion())
        with self.guard(opener) as guard:
            guard.post(payload(), max_output_tokens=100)
            summary = guard.summary()
            self.assertEqual(summary["attempts"], 3)
            self.assertEqual(summary["reserved_units"], 2_400_000_000)
            self.assertEqual(summary["consumed_units"], 140_000_000)
        self.assertEqual(self.clock.sleeps, [2, 5])

    def test_retry_checks_budget_before_another_send(self):
        opener = Opener(rejection(429, 1), completion())
        with self.guard(opener, spend_cap_usd="0.0012") as guard:
            self.assertCategory("budget", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertEqual(guard.summary()["attempts"], 1)
        self.assertEqual(len(opener.calls), 1)

    def test_maximum_two_retries_and_unknown_or_daily_exhaustion_stop(self):
        scenarios = (([rejection(429, 0) for _ in range(4)], 3),
                     ([rejection(429), completion()], 1),
                     ([rejection(429, "NaN"), completion()], 1),
                     ([rejection(429, 1, daily=True), completion()], 1))
        for index, (responses, expected) in enumerate(scenarios):
            with self.subTest(index=index):
                self.ledger = Path(self.directory.name) / ("scenario-" + str(index) + ".json")
                opener = Opener(*responses)
                with self.guard(opener) as guard:
                    self.assertCategory("quota", lambda: guard.post(payload(), max_output_tokens=100))
                    self.assertEqual(guard.summary()["attempts"], expected)
                self.assertEqual(len(opener.calls), expected)

    def test_groq_daily_request_header_stops_but_minute_tokens_can_retry(self):
        for header, expected in (("x-ratelimit-remaining-requests", 1),
                                 ("x-ratelimit-remaining-tokens", 2)):
            with self.subTest(header=header):
                self.ledger = Path(self.directory.name) / (header + ".json")
                error = rejection(429, 0)
                error.headers[header] = "0"
                opener = Opener(error, completion())
                with self.guard(opener, provider="groq", model="openai/gpt-oss-120b",
                                endpoint="https://api.groq.com/openai/v1/chat/completions") as guard:
                    operation = lambda: guard.post(payload(model="openai/gpt-oss-120b"), max_output_tokens=100)
                    if expected == 1:
                        self.assertCategory("quota", operation)
                    else:
                        operation()
                    self.assertEqual(guard.summary()["attempts"], expected)
                self.assertEqual(len(opener.calls), expected)

    def test_access_errors_and_server_errors_do_not_retry_or_leak(self):
        for status, category in ((401, "access"), (403, "access"), (500, "provider"), (503, "provider"), (302, "protocol")):
            with self.subTest(status=status):
                self.ledger = Path(self.directory.name) / (str(status) + ".json")
                opener = Opener(rejection(status, 0), completion())
                with self.guard(opener) as guard:
                    message = self.assertCategory(category, lambda: guard.post(payload(), max_output_tokens=100))
                    self.assertNotIn("secret-key", message)
                    self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
                self.assertEqual(len(opener.calls), 1)
                self.assertNotIn("secret-key", self.ledger.read_text())

    def test_concurrency_lock_covers_other_providers_and_access_checks(self):
        with self.guard() as first:
            other = self.guard(run_id="access-check", provider="gemini", model="gemini-3.8-flash",
                               endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent")
            self.assertCategory("infrastructure", other.__enter__)
            child = subprocess.run(
                [sys.executable, "-c",
                 "import json,sys,time\n"
                 "from pathlib import Path\n"
                 "from harness.request_guard import GuardError,GuardedTransport\n"
                 "try:\n"
                 "    with GuardedTransport(json.loads(sys.argv[2]), 'child-key', Path(sys.argv[1]), time.monotonic()+10, 'child-check'):\n"
                 "        print('unexpected-lock-acquisition')\n"
                 "except GuardError as error:\n"
                 "    print(error.category)\n",
                 str(self.ledger), json.dumps(policy())],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "infrastructure")
            self.assertEqual(first.summary()["attempts"], 0)
        with self.guard() as reopened:
            reopened.post(payload(), max_output_tokens=100)

    def test_corrupt_nonfinite_duplicate_and_inconsistent_ledgers_fail_closed(self):
        for index, corrupt in enumerate((b"{", b'{"version":NaN}', b'{"version":1,"version":1}', b'{"version":1,"money_unit":"USD/10^12","providers":{"mistral":{}}}')):
            with self.subTest(index=index):
                self.ledger = Path(self.directory.name) / ("bad-" + str(index) + ".json")
                self.ledger.write_bytes(corrupt)
                self.assertCategory("infrastructure", self.guard().__enter__)
                self.assertEqual(self.ledger.read_bytes(), corrupt)
        self.ledger = Path(self.directory.name) / "inconsistent.json"
        with self.guard() as guard:
            guard.post(payload(), max_output_tokens=100)
        state = json.loads(self.ledger.read_text())
        state["providers"]["mistral"]["consumed_units"] = 0
        self.ledger.write_text(json.dumps(state))
        self.assertCategory("infrastructure", self.guard().__enter__)

    def test_policy_changes_or_deleted_ledger_cannot_reset_spend(self):
        with self.guard() as guard:
            guard.post(payload(), max_output_tokens=100)
        for changes in ({"spend_cap_usd": "2"}, {"input_usd_per_million": "0"}, {"output_limit": 101}, {"rpm": 101}):
            with self.subTest(changes=changes):
                self.assertCategory("infrastructure", self.guard(**changes).__enter__)
        with self.guard(input_usd_per_million="1.000") as guard:
            self.assertEqual(guard.summary()["consumed_units"], 140_000_000)
        self.ledger.unlink()
        self.assertCategory("infrastructure", self.guard().__enter__)
        self.assertFalse(self.ledger.exists())

    def test_invalid_usage_never_releases_a_hold(self):
        bad = [completion(total_tokens=999), completion(input_tokens=1001), completion(output_tokens=101),
               completion(prompt_tokens=True), completion(completion_tokens_details=[]),
               completion(completion_tokens_details={"reasoning_tokens": 21}), {"choices": []}]
        for index, raw in enumerate(bad):
            with self.subTest(index=index):
                self.ledger = Path(self.directory.name) / ("usage-" + str(index) + ".json")
                with self.guard(Opener(raw)) as guard:
                    self.assertCategory("protocol", lambda: guard.post(payload(), max_output_tokens=100))
                    self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
                    self.assertEqual(guard.summary()["consumed_units"], 0)
                with self.guard(run_id="restart") as guard:
                    self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)

    def test_native_gemini_thinking_is_billed_beyond_requested_visible_cap(self):
        native = {"candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                  "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 30, "totalTokenCount": 150}}
        options = {"provider": "gemini", "model": "gemini-3.8-flash",
                   "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                   "billable_output_limit": 100}
        opener = Opener(native)
        with self.guard(opener, **options) as guard:
            guard.post({"contents": [], "generationConfig": {"maxOutputTokens": 20}}, max_output_tokens=20)
            self.assertEqual(guard.summary()["consumed_units"], 200_000_000)
        request = opener.calls[0][0]
        self.assertEqual(request.get_header("X-goog-api-key"), "secret-key")
        self.assertIsNone(request.get_header("Authorization"))
        record = json.loads(self.ledger.read_text())["providers"]["gemini"]["attempts"][0]
        self.assertEqual(record["reserved_units"], 1_200_000_000)
        self.assertEqual(record["usage"]["output_tokens"], 50)
        self.assertEqual(record["usage"]["reasoning_tokens"], 30)
        del native["usageMetadata"]["thoughtsTokenCount"]
        with self.guard(Opener(native), **options) as guard:
            self.assertCategory("protocol", lambda: guard.post({"generationConfig": {"maxOutputTokens": 20}}, max_output_tokens=20))
            self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)

    def test_native_gemini_accepts_only_arithmetically_proven_zero_omissions(self):
        options = {"provider": "gemini", "model": "gemini-3.8-flash",
                   "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"}
        cases = (
            ({"promptTokenCount": 100, "candidatesTokenCount": 20, "totalTokenCount": 120}, 20, 0),
            ({"promptTokenCount": 100, "thoughtsTokenCount": 30, "totalTokenCount": 130}, 30, 30),
            ({"promptTokenCount": 100, "candidatesTokenCount": 20, "totalTokenCount": 121}, None, None),
            ({"promptTokenCount": 100, "thoughtsTokenCount": 30, "totalTokenCount": 131}, None, None),
            ({"promptTokenCount": 100, "totalTokenCount": 100}, None, None),
            ({"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": None, "totalTokenCount": 120}, None, None),
            ({"promptTokenCount": 100, "candidatesTokenCount": False, "thoughtsTokenCount": 30, "totalTokenCount": 130}, None, None),
        )
        for index, (usage, output, reasoning) in enumerate(cases):
            with self.subTest(usage=usage):
                self.ledger = Path(self.directory.name) / ("zero-omission-" + str(index) + ".json")
                with self.guard(Opener({"usageMetadata": usage}), **options) as guard:
                    request = {"generationConfig": {"maxOutputTokens": 100}}
                    if output is None:
                        self.assertCategory("protocol", lambda: guard.post(request, max_output_tokens=100))
                        self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
                    else:
                        guard.post(request, max_output_tokens=100)
                        self.assertEqual(guard.summary()["consumed_units"], 100_000_000 + output * 2_000_000)
                        record = json.loads(self.ledger.read_text())["providers"]["gemini"]["attempts"][0]
                        self.assertEqual(record["usage"]["reasoning_tokens"], reasoning)

    def test_minimum_spacing_and_rolling_rpm_reconcile_across_restarts(self):
        with self.guard(Opener(completion(), completion()), rpm=2, min_interval_seconds=3) as guard:
            guard.post(payload(), max_output_tokens=100)
            guard.post(payload(), max_output_tokens=100)
        with self.guard(rpm=2, min_interval_seconds=3, run_id="next") as guard:
            guard.post(payload(), max_output_tokens=100)
        self.assertEqual(self.clock.sleeps, [3, 57])

    def test_token_windows_reconcile_actual_usage_instead_of_estimate(self):
        with self.guard(Opener(completion(), completion()), tpm=850) as guard:
            guard.post(payload(), max_output_tokens=100)
            guard.post(payload(), max_output_tokens=100)
        self.assertEqual(self.clock.sleeps, [])
        attempts = json.loads(self.ledger.read_text())["providers"]["mistral"]["attempts"]
        self.assertGreater(attempts[0]["estimated_input_tokens"], 500)
        self.assertEqual(attempts[0]["quota_input_tokens"], 100)
        self.assertEqual(attempts[0]["quota_output_tokens"], 20)

    def test_uncertain_usage_keeps_estimate_in_rolling_token_window(self):
        with self.guard(Opener(TimeoutError(), completion()), tpm=850) as guard:
            self.assertCategory("provider", lambda: guard.post(payload(), max_output_tokens=100))
            guard.post(payload(), max_output_tokens=100)
        self.assertEqual(self.clock.sleeps, [60])

    def test_daily_requests_and_tokens_use_conservative_rolling_24_hours(self):
        for key, limit in (("rpd", 1), ("tpd", 700)):
            with self.subTest(key=key):
                self.clock = Clock()
                self.ledger = Path(self.directory.name) / (key + ".json")
                with self.guard(Opener(completion(), completion()), **{key: limit}) as guard:
                    guard.post(payload(), max_output_tokens=100)
                    guard.post(payload(), max_output_tokens=100)
                self.assertEqual(self.clock.sleeps, [86400])

    def test_entire_window_overflow_and_expired_deadline_never_send(self):
        opener = Opener(completion())
        with self.guard(opener, tpm=600) as guard:
            self.assertCategory("quota", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertEqual(guard.summary()["attempts"], 0)
        self.assertEqual(opener.calls, [])
        self.ledger = Path(self.directory.name) / "deadline.json"
        with self.guard(opener, deadline=0) as guard:
            self.assertCategory("deadline", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertEqual(guard.summary()["attempts"], 0)

    def test_retry_after_outside_deadline_is_not_shortened(self):
        opener = Opener(rejection(429, 120), completion())
        with self.guard(opener, deadline=30) as guard:
            self.assertCategory("deadline", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertEqual(guard.summary()["attempts"], 1)
        self.assertEqual(self.clock.sleeps, [])
        self.assertEqual(len(opener.calls), 1)

    def test_unknown_exhaustion_cannot_be_bypassed_by_new_trial(self):
        with self.guard(Opener(rejection(429)), deadline=30) as guard:
            self.assertCategory("quota", lambda: guard.post(payload(), max_output_tokens=100))
        opener = Opener(completion())
        with self.guard(opener, run_id="next-trial", deadline=30) as guard:
            self.assertCategory("deadline", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertEqual(guard.summary()["attempts"], 1)
        self.assertEqual(opener.calls, [])

    def test_input_only_quota_excludes_output_but_still_reserves_its_cost(self):
        with self.guard(tpm=600, tpm_scope="input") as guard:
            guard.post(payload(), max_output_tokens=100)
            self.assertEqual(guard.summary()["consumed_units"], 140_000_000)

    def test_groq_full_history_tokenizer_can_fit_then_refuse_larger_history(self):
        opener = Opener(completion())
        groq_policy = {
            "provider": "groq", "model": "openai/gpt-oss-120b",
            "endpoint": "https://api.groq.com/openai/v1/chat/completions",
            "tpm": 8000, "input_limit": 131072, "output_limit": 4096,
        }
        request = payload(model="openai/gpt-oss-120b", max_tokens=4096,
                          messages=[{"role": "user", "content": "hello " * 2000}])
        with self.guard(opener, **groq_policy) as guard:
            guard.post(request, max_output_tokens=4096)
            request["messages"].append({"role": "user", "content": "hello " * 6000})
            self.assertCategory("quota", lambda: guard.post(request, max_output_tokens=4096))
            self.assertEqual(guard.summary()["attempts"], 1)
        self.assertEqual(len(opener.calls), 1)

    def test_response_limit_and_malformed_json_keep_full_hold(self):
        for index, raw in enumerate((b"secret-key invalid-json", b"{" + b" " * 80)):
            self.ledger = Path(self.directory.name) / ("response-" + str(index) + ".json")
            with patch("harness.request_guard.MAX_RESPONSE_BYTES", 64):
                with self.guard(Opener(raw)) as guard:
                    message = self.assertCategory("protocol", lambda: guard.post(payload(), max_output_tokens=100))
                    self.assertNotIn("secret-key", message)
                    self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)

    def test_failed_presend_persistence_prevents_network(self):
        opener = Opener(completion())
        with self.guard(opener) as guard:
            with patch("harness.request_guard.os.replace", side_effect=OSError("secret-key")):
                self.assertCategory("infrastructure", lambda: guard.post(payload(), max_output_tokens=100))
        self.assertEqual(opener.calls, [])
        with self.guard() as guard:
            self.assertEqual(guard.summary()["reserved_units"], 0)

    def test_failed_settlement_keeps_disk_hold_and_cannot_double_release(self):
        def fail_settlement(request):
            replacement.start()
            return completion()

        replacement = patch("harness.request_guard.os.replace", side_effect=OSError("secret-key"))
        self.addCleanup(replacement.stop)
        with self.guard(Opener(fail_settlement)) as guard:
            self.assertCategory("infrastructure", lambda: guard.post(payload(), max_output_tokens=100))
            self.assertCategory("infrastructure", lambda: guard.post(payload(), max_output_tokens=100))
        replacement.stop()
        with self.guard() as guard:
            self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
            self.assertEqual(guard.summary()["consumed_units"], 0)

    def test_test_endpoint_override_requires_explicit_loopback_gate(self):
        for endpoint, enabled in (("http://127.0.0.1:9999/mock", False),
                                  ("http://example.com:9999/mock", True),
                                  ("http://127.0.0.1:9999/mock?key=secret-key", True),
                                  ("http://secret-key@127.0.0.1:9999/mock", True),
                                  ("https://evil.invalid/v1/chat/completions", False)):
            with self.subTest(endpoint=endpoint):
                self.assertCategory("infrastructure", lambda: self.guard(endpoint=endpoint, test_only_localhost=enabled))


class LocalHTTPDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = Path(self.directory.name) / "ledger.json"
        self.requests = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                requests.append(self.path)
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/credential-destination")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "10000")
                self.end_headers()
                try:
                    for _ in range(50):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(0.03)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = "http://127.0.0.1:" + str(server.server_port)

    def transport(self, path, deadline):
        return GuardedTransport(policy(endpoint=self.url + path, test_only_localhost=True),
                                "secret-key", self.ledger, deadline, "local-only")

    def test_slow_drip_is_bounded_by_total_deadline_not_socket_inactivity(self):
        started = time.monotonic()
        with self.transport("/slow", started + 0.2) as guard:
            with self.assertRaises(GuardError) as error:
                guard.post(payload(), max_output_tokens=100)
            self.assertEqual(error.exception.category, "deadline")
            self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(self.requests, ["/slow"])

    def test_redirect_never_forwards_credentials_or_reaches_destination(self):
        with self.transport("/redirect", time.monotonic() + 5) as guard:
            with self.assertRaises(GuardError) as error:
                guard.post(payload(), max_output_tokens=100)
            self.assertEqual(error.exception.category, "protocol")
            self.assertEqual(guard.summary()["reserved_units"], 1_200_000_000)
        self.assertEqual(self.requests, ["/redirect"])


if __name__ == "__main__":
    unittest.main()
