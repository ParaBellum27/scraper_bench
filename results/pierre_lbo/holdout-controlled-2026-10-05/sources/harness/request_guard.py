"""Fail-closed, campaign-wide accounting for direct provider requests.

The private ledger and its sibling .lock file must be shared by *every* access
check and trial in a campaign. Monetary holds use hard model context limits,
never the quota estimator. Quota estimates are explicitly approximate: neither
the UTF-8 estimate nor Groq's local tokenizer guarantees avoidance of provider
or organization-level 429s. No prompt truncation or hidden retry is performed.
"""

from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, localcontext
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import tempfile
import threading
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


MONEY_SCALE = 10**12
MONEY_UNIT = "USD/10^12"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_LEDGER_BYTES = 128 * 1024 * 1024
_ENDPOINTS = {
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
}
_LOCK_MARKER = b"request-guard-ledger-v1\n"


class GuardError(RuntimeError):
    """An intentionally sanitized failure with a stable machine category."""

    def __init__(self, category: str, message: str):
        self.category = category
        super().__init__(message)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _finite(value):
    return (type(value) is int and value >= 0) or (type(value) is float and math.isfinite(value) and value >= 0)


def _decimal(value):
    try:
        number = Decimal(str(value))
        exponent = number.as_tuple().exponent
        if not number.is_finite() or number < 0 or len(number.as_tuple().digits) > 30 or not isinstance(exponent, int) or abs(exponent) > 30:
            raise ValueError
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise GuardError("infrastructure", "Invalid monetary policy value") from None


def _decimal_text(value):
    return format(value, "f")


def _usd(units):
    with localcontext() as ctx:
        ctx.prec = 80
        return _decimal_text(Decimal(units) / MONEY_SCALE)


def _fingerprint(policy):
    encoded = json.dumps(policy, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Nonfinite JSON")


def _json(data):
    return json.loads(data, object_pairs_hook=_object, parse_constant=_reject_constant)


class GuardedTransport:
    def __init__(self, policy: dict, api_key: str, ledger_path: Path, deadline: float,
                 run_id: str, *, clock=time.monotonic, wall_clock=time.time,
                 sleep=time.sleep, opener=None):
        self.policy = self._policy(policy)
        if not isinstance(api_key, str) or not api_key or "\n" in api_key or "\r" in api_key:
            raise GuardError("access", "A valid provider credential is required")
        if not isinstance(run_id, str) or not run_id or len(run_id) > 200 or any(ord(c) < 32 for c in run_id) or api_key in run_id:
            raise GuardError("infrastructure", "Invalid run identifier")
        if not _finite(deadline):
            raise GuardError("deadline", "Invalid request deadline")
        self._api_key = api_key
        self.ledger_path = Path(ledger_path)
        self.deadline = deadline
        self.run_id = run_id
        self._clock, self._wall_clock, self._sleep = clock, wall_clock, sleep
        # Suppress ambient proxies as well as redirects: credentials go only to
        # the pinned HTTPS authority (or explicit loopback-only smoke server).
        self._opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        self._lock_fd = None
        self._state: dict[str, Any] | None = None
        self._poisoned = False
        self._encoder = None
        with localcontext() as ctx:
            ctx.prec = 80
            self._cap = int((Decimal(self.policy["spend_cap_usd"]) * MONEY_SCALE).to_integral_value(rounding=ROUND_FLOOR))

    @staticmethod
    def _policy(source) -> dict[str, Any]:
        try:
            p = {key: source[key] for key in (
                "provider", "model", "endpoint", "rpm", "tpm", "tpm_scope", "rpd", "tpd",
                "min_interval_seconds", "input_limit", "output_limit", "input_usd_per_million",
                "output_usd_per_million", "spend_cap_usd",
            )}
            p["request_timeout_seconds"] = source.get("request_timeout_seconds", 180)
            p["max_retries"] = source.get("max_retries", 2)
            p["billable_output_limit"] = source.get("billable_output_limit")
            p["test_only_localhost"] = source.get("test_only_localhost", False)
            if p["provider"] not in _ENDPOINTS or not isinstance(p["model"], str) or not p["model"]:
                raise ValueError
            if any(not _integer(p[key], 1) for key in ("rpm", "tpm", "input_limit", "output_limit")):
                raise ValueError
            if any(p[key] is not None and not _integer(p[key], 1) for key in ("rpd", "tpd")):
                raise ValueError
            if not _finite(p["min_interval_seconds"]) or not _finite(p["request_timeout_seconds"]) or not p["request_timeout_seconds"]:
                raise ValueError
            if not _integer(p["max_retries"]) or p["max_retries"] > 2 or p["tpm_scope"] not in ("combined", "input"):
                raise ValueError
            if p["billable_output_limit"] is not None and (not _integer(p["billable_output_limit"], 1) or p["billable_output_limit"] > p["output_limit"]):
                raise ValueError
            if type(p["test_only_localhost"]) is not bool:
                raise ValueError
            endpoint = urllib.parse.urlsplit(p["endpoint"])
            if p["test_only_localhost"]:
                if endpoint.scheme != "http" or endpoint.hostname not in ("localhost", "127.0.0.1", "::1") or not endpoint.port:
                    raise ValueError
                if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                    raise ValueError
            elif p["endpoint"] != _ENDPOINTS[p["provider"]]:
                raise ValueError
            for key in ("input_usd_per_million", "output_usd_per_million", "spend_cap_usd"):
                # Canonical numeric values make textual 1.0 versus 1 harmless,
                # but any actual price/cap change changes the fingerprint.
                value = _decimal(p[key])
                p[key] = format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")
                p[key] = p[key] or "0"
            p["quota_estimator"] = "o200k_harmony-full-json+512" if p["provider"] == "groq" else "ceil(utf8-full-json-bytes/3)+512"
            return p
        except (KeyError, ValueError, TypeError, AttributeError):
            raise GuardError("infrastructure", "Invalid or unapproved request policy") from None

    def __enter__(self):
        if self._lock_fd is not None or self._poisoned:
            raise GuardError("infrastructure", "Transport cannot be reopened")
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = self.ledger_path.with_name(self.ledger_path.name + ".lock")
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self._lock_fd = fd
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise GuardError("infrastructure", "Invalid campaign lock")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise GuardError("infrastructure", "Another campaign process holds the request lock") from None
            marker = os.read(fd, len(_LOCK_MARKER) + 1)
            if marker not in (b"", _LOCK_MARKER):
                raise GuardError("infrastructure", "Corrupt campaign lock marker")
            if not self.ledger_path.exists():
                if marker:
                    raise GuardError("infrastructure", "Campaign ledger is missing; refusing to reset spend")
                os.write(fd, _LOCK_MARKER)
                os.fsync(fd)
                self._state = {"version": 1, "money_unit": MONEY_UNIT, "providers": {}}
                self._save(self._state)
            else:
                self._state = self._load()
                self._validate_state(self._state)
                if not marker:
                    os.write(fd, _LOCK_MARKER)
                    os.fsync(fd)
            provider = self.policy["provider"]
            record = self._state["providers"].get(provider)
            if record is not None and record["fingerprint"] != _fingerprint(self.policy):
                raise GuardError("infrastructure", "Campaign policy changed; refusing to reset or reprice spend")
            if record is None:
                state = deepcopy(self._active_state())
                state["providers"][provider] = {
                    "fingerprint": _fingerprint(self.policy), "policy": self.policy,
                    "spend_cap_units": self._cap, "consumed_units": 0, "reserved_units": 0,
                    "not_before": 0, "attempts": [],
                }
                self._save(state)
            return self
        except GuardError:
            self.__exit__(None, None, None)
            raise
        except (OSError, ValueError, TypeError):
            self.__exit__(None, None, None)
            raise GuardError("infrastructure", "Cannot initialize private request ledger") from None

    def __exit__(self, exc_type, exc, tb):
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def _load(self) -> dict[str, Any]:
        try:
            fd = os.open(self.ledger_path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_LEDGER_BYTES:
                    raise ValueError
                state = _json(stream.read(MAX_LEDGER_BYTES + 1))
                if not isinstance(state, dict):
                    raise ValueError
                return state
        except (OSError, ValueError, TypeError, UnicodeError):
            raise GuardError("infrastructure", "Corrupt or unreadable request ledger") from None

    @staticmethod
    def _validate_state(state):
        try:
            if not isinstance(state, dict) or state["version"] != 1 or state["money_unit"] != MONEY_UNIT or not isinstance(state["providers"], dict):
                raise ValueError
            for provider, record in state["providers"].items():
                policy = GuardedTransport._policy(record["policy"])
                if provider != policy["provider"] or record["policy"] != policy or record["fingerprint"] != _fingerprint(policy):
                    raise ValueError
                for name in ("spend_cap_units", "consumed_units", "reserved_units"):
                    if not _integer(record[name]):
                        raise ValueError
                with localcontext() as ctx:
                    ctx.prec = 80
                    cap = int((Decimal(policy["spend_cap_usd"]) * MONEY_SCALE).to_integral_value(rounding=ROUND_FLOOR))
                if cap != record["spend_cap_units"] or not _finite(record["not_before"]) or not isinstance(record["attempts"], list):
                    raise ValueError
                consumed = reserved = 0
                last = 0
                for index, attempt in enumerate(record["attempts"], 1):
                    if attempt["id"] != index or not isinstance(attempt["run_id"], str) or not attempt["run_id"]:
                        raise ValueError
                    if not _finite(attempt["started_at"]) or attempt["started_at"] < last:
                        raise ValueError
                    last = attempt["started_at"]
                    for name in ("reserved_units", "charged_units", "estimated_input_tokens", "quota_input_tokens", "quota_output_tokens", "requested_output_tokens", "billable_output_tokens"):
                        if not _integer(attempt[name]):
                            raise ValueError
                    if attempt["estimator"] != policy["quota_estimator"] or not attempt["requested_output_tokens"] or attempt["requested_output_tokens"] > attempt["billable_output_tokens"] or attempt["billable_output_tokens"] > policy["output_limit"]:
                        raise ValueError
                    if attempt["billable_output_tokens"] != (policy["billable_output_limit"] or attempt["requested_output_tokens"]):
                        raise ValueError
                    expected_hold = GuardedTransport._cost(policy, policy["input_limit"], attempt["billable_output_tokens"])
                    if attempt["reserved_units"] != expected_hold or attempt["charged_units"] > expected_hold:
                        raise ValueError
                    if attempt["state"] == "settled":
                        usage = attempt["usage"]
                        if any(not _integer(usage[key]) for key in ("input_tokens", "output_tokens", "reasoning_tokens")):
                            raise ValueError
                        if usage["input_tokens"] > policy["input_limit"] or usage["output_tokens"] > attempt["billable_output_tokens"] or usage["reasoning_tokens"] > usage["output_tokens"]:
                            raise ValueError
                        if attempt["charged_units"] != GuardedTransport._cost(policy, usage["input_tokens"], usage["output_tokens"]):
                            raise ValueError
                        if (attempt["quota_input_tokens"], attempt["quota_output_tokens"]) != (usage["input_tokens"], usage["output_tokens"]):
                            raise ValueError
                        consumed += attempt["charged_units"]
                    elif attempt["state"] in ("reserved", "uncertain"):
                        if attempt["charged_units"] != expected_hold or attempt["quota_input_tokens"] != attempt["estimated_input_tokens"] or attempt["quota_output_tokens"] != attempt["billable_output_tokens"]:
                            raise ValueError
                        reserved += expected_hold
                    else:
                        raise ValueError
                if (consumed, reserved) != (record["consumed_units"], record["reserved_units"]) or consumed + reserved > cap:
                    raise ValueError
        except (KeyError, ValueError, TypeError, AttributeError, GuardError):
            raise GuardError("infrastructure", "Corrupt or inconsistent request ledger") from None

    def _save(self, state: dict[str, Any]):
        temp = None
        try:
            data = json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            if len(data) > MAX_LEDGER_BYTES:
                raise ValueError
            fd, temp = tempfile.mkstemp(prefix="." + self.ledger_path.name + ".", dir=self.ledger_path.parent)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.ledger_path)
            temp = None
            directory = os.open(self.ledger_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            self._state = state
        except (OSError, ValueError, TypeError):
            self._poisoned = True
            raise GuardError("infrastructure", "Cannot durably persist request accounting") from None
        finally:
            if temp is not None:
                try:
                    os.unlink(temp)
                except OSError:
                    pass

    @staticmethod
    def _cost(policy, input_tokens, output_tokens):
        with localcontext() as ctx:
            ctx.prec = 80
            amount = (Decimal(policy["input_usd_per_million"]) * input_tokens + Decimal(policy["output_usd_per_million"]) * output_tokens) * (MONEY_SCALE // 1_000_000)
            return int(amount.to_integral_value(rounding=ROUND_CEILING))

    def _active_state(self) -> dict[str, Any]:
        if self._lock_fd is None or self._state is None or self._poisoned:
            raise GuardError("infrastructure", "An active healthy campaign lock is required")
        return self._state

    def _record(self) -> dict[str, Any]:
        return self._active_state()["providers"][self.policy["provider"]]

    def raise_spend_cap(self, new_cap_usd, *, authorization: str):
        """Explicit host-only cap increase; never reprice or release old holds."""
        record = self._record()
        if (not isinstance(authorization, str) or not authorization.strip()
                or len(authorization) > 1000 or self._api_key in authorization):
            raise GuardError("infrastructure", "A non-secret authorization is required for a cap increase")
        cap = _decimal(new_cap_usd)
        with localcontext() as ctx:
            ctx.prec = 80
            units = int((cap * MONEY_SCALE).to_integral_value(rounding=ROUND_FLOOR))
        if units <= self._cap:
            raise GuardError("budget", "A cap increase must strictly exceed the existing cap")
        policy = self._policy({**self.policy, "spend_cap_usd": _decimal_text(cap)})
        state = deepcopy(self._active_state())
        updated = state["providers"][self.policy["provider"]]
        updated.setdefault("cap_increases", []).append({
            "old_cap_units": record["spend_cap_units"], "new_cap_units": units,
            "authorized_at": self._wall_clock(), "authorization": authorization,
            "run_id": self.run_id,
        })
        updated.update(policy=policy, fingerprint=_fingerprint(policy), spend_cap_units=units)
        self._validate_state(state)
        self._save(state)
        self.policy, self._cap = policy, units

    def summary(self):
        record = self._record()
        consumed, reserved, cap = record["consumed_units"], record["reserved_units"], record["spend_cap_units"]
        result = {"provider": self.policy["provider"], "money_unit": MONEY_UNIT,
                  "attempts": len(record["attempts"]),
                  "run_attempts": sum(item["run_id"] == self.run_id for item in record["attempts"])}
        for name, value in (("consumed", consumed), ("reserved", reserved), ("committed", consumed + reserved), ("spend_cap", cap), ("remaining", cap - consumed - reserved)):
            result[name + "_units"] = value
            result[name + "_usd"] = _usd(value)
        return result

    def _check_deadline(self):
        remaining = self.deadline - self._clock()
        if not math.isfinite(remaining) or remaining <= 0:
            raise GuardError("deadline", "Campaign request deadline reached")
        return remaining

    def _estimate(self, payload, encoded):
        if self.policy["provider"] == "groq":
            try:
                if self._encoder is None:
                    import tiktoken
                    self._encoder = tiktoken.get_encoding("o200k_harmony")
                return len(self._encoder.encode(encoded.decode("utf-8"), disallowed_special=())) + 512
            except Exception:
                raise GuardError("infrastructure", "Groq quota tokenizer is unavailable") from None
        return (len(encoded) + 2) // 3 + 512

    def _rate_wait(self, estimated_input, output_tokens):
        p = self.policy
        quota_tokens = estimated_input + (output_tokens if p["tpm_scope"] == "combined" else 0)
        if quota_tokens > p["tpm"] or (p["tpd"] is not None and quota_tokens > p["tpd"]):
            raise GuardError("quota", "Request estimate exceeds an entire quota window; no truncation performed")
        while True:
            self._check_deadline()
            record = self._record()
            now = self._wall_clock()
            if not _finite(now) or (record["attempts"] and record["attempts"][-1]["started_at"] > now):
                raise GuardError("infrastructure", "Wall clock moved backwards; refusing quota reset")
            wake = max(now, record["not_before"])
            if record["attempts"]:
                wake = max(wake, record["attempts"][-1]["started_at"] + p["min_interval_seconds"])
            for window, request_limit, token_limit in ((60, p["rpm"], p["tpm"]), (86400, p["rpd"], p["tpd"])):
                active = [a for a in record["attempts"] if a["started_at"] + window > now]
                request_count = len(active)
                token_count = sum(a["quota_input_tokens"] + (a["quota_output_tokens"] if p["tpm_scope"] == "combined" else 0) for a in active)
                for attempt in active:
                    if (request_limit is None or request_count + 1 <= request_limit) and (token_limit is None or token_count + quota_tokens <= token_limit):
                        break
                    wake = max(wake, attempt["started_at"] + window)
                    request_count -= 1
                    token_count -= attempt["quota_input_tokens"] + (attempt["quota_output_tokens"] if p["tpm_scope"] == "combined" else 0)
            delay = wake - now
            if delay <= 0:
                return now
            if delay >= self._check_deadline():
                raise GuardError("deadline", "Required quota or Retry-After wait exceeds campaign deadline")
            self._sleep(delay)

    def _reserve(self, estimated_input, requested_output, billable_output):
        hold = self._cost(self.policy, self.policy["input_limit"], billable_output)
        record = self._record()
        if record["consumed_units"] + record["reserved_units"] + hold > self._cap:
            raise GuardError("budget", "Provider spend cap cannot cover the hard maximum request cost")
        now = self._rate_wait(estimated_input, billable_output)
        self._check_deadline()
        state = deepcopy(self._active_state())
        record = state["providers"][self.policy["provider"]]
        attempt = {"id": len(record["attempts"]) + 1, "run_id": self.run_id,
                   "started_at": now, "state": "reserved", "reserved_units": hold, "charged_units": hold,
                   "estimated_input_tokens": estimated_input, "estimator": self.policy["quota_estimator"],
                   "quota_input_tokens": estimated_input, "quota_output_tokens": billable_output,
                   "requested_output_tokens": requested_output, "billable_output_tokens": billable_output}
        record["attempts"].append(attempt)
        record["reserved_units"] += hold
        self._save(state)  # Durable *before* opener or any request bytes.
        return attempt["id"]

    def _uncertain(self, attempt_id, category, status=None, not_before=None):
        state = deepcopy(self._active_state())
        record = state["providers"][self.policy["provider"]]
        attempt = record["attempts"][attempt_id - 1]
        if attempt["state"] != "reserved":
            raise GuardError("infrastructure", "Request accounting cannot be reconciled twice")
        attempt["state"] = "uncertain"
        attempt["error_category"] = category
        if status is not None:
            attempt["http_status"] = status
        if not_before is not None:
            record["not_before"] = max(record["not_before"], not_before)
        self._save(state)

    def _usage(self, raw, billable_output):
        try:
            if self.policy["provider"] == "gemini":
                usage = raw["usageMetadata"]
                input_tokens = usage["promptTokenCount"]
                if "candidatesTokenCount" not in usage and "thoughtsTokenCount" not in usage:
                    raise ValueError
                # ProtoJSON omits zero-valued scalars. An omission is safe only
                # when the explicit total and the other explicit component
                # prove that the omitted count is zero; never infer a positive
                # missing count from the difference.
                visible = usage.get("candidatesTokenCount", 0)
                reasoning = usage.get("thoughtsTokenCount", 0)
                total = usage["totalTokenCount"]
                if any(not _integer(v) for v in (input_tokens, visible, reasoning, total)) or total != input_tokens + visible + reasoning:
                    raise ValueError
                output_tokens = visible + reasoning
            else:
                usage = raw["usage"]
                input_tokens, output_tokens, total = usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"]
                details = usage.get("completion_tokens_details")
                if details is None:
                    details = {}
                if not isinstance(details, dict):
                    raise ValueError
                reasoning = details.get("reasoning_tokens", 0)
                if any(not _integer(v) for v in (input_tokens, output_tokens, total, reasoning)) or total != input_tokens + output_tokens or reasoning > output_tokens:
                    raise ValueError
            if input_tokens > self.policy["input_limit"] or output_tokens > billable_output:
                raise ValueError
            return {"input_tokens": input_tokens, "output_tokens": output_tokens, "reasoning_tokens": reasoning}
        except (KeyError, ValueError, TypeError, AttributeError):
            raise GuardError("protocol", "Missing, inconsistent, or out-of-reservation provider usage; full hold retained") from None

    def _settle(self, attempt_id, usage):
        state = deepcopy(self._active_state())
        record = state["providers"][self.policy["provider"]]
        attempt = record["attempts"][attempt_id - 1]
        actual = self._cost(self.policy, usage["input_tokens"], usage["output_tokens"])
        if attempt["state"] != "reserved" or actual > attempt["reserved_units"]:
            raise GuardError("protocol", "Provider usage exceeds its monetary reservation")
        attempt.update(state="settled", charged_units=actual, usage=usage,
                       quota_input_tokens=usage["input_tokens"], quota_output_tokens=usage["output_tokens"])
        record["reserved_units"] -= attempt["reserved_units"]
        record["consumed_units"] += actual
        self._save(state)

    @contextmanager
    def _network_deadline(self):
        if threading.current_thread() is not threading.main_thread() or not hasattr(signal, "setitimer"):
            raise GuardError("infrastructure", "Bounded provider I/O requires POSIX main-thread deadline support")
        remaining = self._check_deadline()
        old_handler = signal.getsignal(signal.SIGALRM)
        old_delay, old_interval = signal.getitimer(signal.ITIMER_REAL)
        timeout = min(remaining, self.policy["request_timeout_seconds"])
        category = "deadline" if remaining <= self.policy["request_timeout_seconds"] else "provider"
        if old_delay > 0 and old_delay <= timeout:
            timeout, category = old_delay, "deadline"
        started = time.monotonic()

        def expire(signum, frame):
            raise GuardError(category, "Provider request exceeded its bounded deadline; full hold retained")

        signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, timeout)
        try:
            yield timeout
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
            if old_delay > 0:
                elapsed = time.monotonic() - started
                signal.setitimer(signal.ITIMER_REAL, max(old_delay - elapsed, 0.000001), old_interval)

    def _request(self, encoded):
        header = "x-goog-api-key" if self.policy["provider"] == "gemini" else "Authorization"
        credential = self._api_key if self.policy["provider"] == "gemini" else "Bearer " + self._api_key
        request = urllib.request.Request(self.policy["endpoint"], data=encoded,
                                         headers={header: credential, "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        with self._network_deadline() as timeout:
            with self._opener.open(request, timeout=timeout) as response:
                status = response.getcode()
                if status != 200:
                    raise GuardError("protocol", "Unexpected successful provider status")
                # One alarm bounds open plus the *entire* body read, including a
                # server that sends a byte just before every socket timeout.
                data = response.read(MAX_RESPONSE_BYTES + 1)
                self._check_deadline()
                if len(data) > MAX_RESPONSE_BYTES:
                    raise GuardError("protocol", "Provider response exceeds the bounded byte limit")
                try:
                    raw = _json(data)
                    if not isinstance(raw, dict):
                        raise ValueError
                    return raw
                except (ValueError, TypeError, UnicodeError):
                    raise GuardError("protocol", "Provider returned invalid response JSON") from None

    def _retry_after(self, headers):
        value = headers.get("Retry-After") if headers else None
        if not isinstance(value, str) or len(value) > 200:
            return None
        try:
            seconds = float(value)
            if not math.isfinite(seconds) or seconds < 0:
                return None
            return self._wall_clock() + seconds
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    return None
                return max(self._wall_clock(), date.timestamp())
            except (ValueError, TypeError, OverflowError):
                return None

    def post(self, payload: dict, *, max_output_tokens: int) -> dict:
        self._record()
        self._check_deadline()
        if not _integer(max_output_tokens, 1) or max_output_tokens > self.policy["output_limit"] or not isinstance(payload, dict):
            raise GuardError("protocol", "Request exceeds the approved output limit")
        billable_output = self.policy["billable_output_limit"] or max_output_tokens
        if billable_output < max_output_tokens:
            raise GuardError("protocol", "Billable output reservation is smaller than the requested cap")
        try:
            if self.policy["provider"] == "gemini":
                config = payload["generationConfig"]
                if config["maxOutputTokens"] != max_output_tokens or config.get("candidateCount", 1) != 1:
                    raise ValueError
            elif payload["model"] != self.policy["model"] or payload.get("max_completion_tokens", payload.get("max_tokens")) != max_output_tokens or payload.get("n", 1) != 1 or payload.get("stream", False) is not False:
                raise ValueError
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (KeyError, ValueError, TypeError, UnicodeError):
            raise GuardError("protocol", "Payload does not match the approved model and output cap") from None
        estimated_input = self._estimate(payload, encoded)
        for retry in range(self.policy["max_retries"] + 1):
            attempt_id = self._reserve(estimated_input, max_output_tokens, billable_output)
            try:
                raw = self._request(encoded)
                usage = self._usage(raw, billable_output)
                self._check_deadline()
            except urllib.error.HTTPError as error:
                status = error.code
                retry_at = self._retry_after(error.headers) if status == 429 else None
                daily_headers = ["x-ratelimit-remaining-requests-day", "x-ratelimit-remaining-tokens-day"]
                # Groq's unsuffixed request header is RPD; its token header is
                # TPM and must not be mistaken for daily exhaustion.
                if self.policy["provider"] == "groq":
                    daily_headers.append("x-ratelimit-remaining-requests")
                daily_exhausted = any(error.headers.get(key) == "0" for key in daily_headers) if error.headers else False
                error.close()  # Never read or log an untrusted error body/key echo.
                category = "quota" if status == 429 else "access" if status in (401, 403) else "protocol" if 300 <= status < 400 else "provider"
                cooldown = retry_at
                if status == 429 and (daily_exhausted or retry_at is None):
                    # Unknown exhaustion must not be bypassed by changing run
                    # IDs or restarting access checks. Do not guess a short wait.
                    cooldown = max(retry_at or 0, self._wall_clock() + 86400)
                self._uncertain(attempt_id, category, status, cooldown)
                if status == 429 and not daily_exhausted and retry_at is not None and retry < self.policy["max_retries"]:
                    continue  # Next reservation rechecks cap, quotas, and deadline.
                raise GuardError(category, "Provider rejected the request (HTTP " + str(status) + "); full hold retained") from None
            except GuardError as error:
                self._uncertain(attempt_id, error.category)
                raise
            except Exception:
                self._uncertain(attempt_id, "provider")
                raise GuardError("provider", "Provider request failed ambiguously; full hold retained and no retry attempted") from None
            # BaseException/process death deliberately leaves the fsynced reserved
            # attempt intact. Settlement never runs from a finally clause.
            self._settle(attempt_id, usage)
            return raw
        raise GuardError("quota", "Provider retry allowance exhausted")
