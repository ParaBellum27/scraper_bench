"""Loopback-only protocol fixtures; no real provider, account or candidate model."""

from contextlib import redirect_stdout
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evaluator.benchmarks import BENCHMARKS
from evaluator.grader import grade_case
from evaluator.run_grader import run_submission
from harness.direct_campaign import load_policy, public_bundle
from harness.run_benchmark import run_trial


def main():
    repo = Path(__file__).resolve().parents[3]
    config = load_policy()
    public = public_bundle(repo, config)
    source = (repo / "reference/pierre_lbo/reference.py").read_text()
    qualification = json.loads((repo / "results/pierre_lbo/audit-2026-10-05/qualification.json").read_text())
    expected = qualification["cases"][0]["spreadsheet"]
    results = []
    for provider_name in ("groq", "gemini", "mistral"):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(request)
                turn = len(requests)
                if turn in (1, 5):
                    text, call = ("READY" if turn == 1 else "Done"), None
                else:
                    text = ""
                    code, submit = {
                        2: ("import openpyxl; w=openpyxl.load_workbook('pierre_lbo_one.xlsx',read_only=True); print(w.sheetnames); w.close()", False),
                        3: (source, True),
                        4: ("from pathlib import Path; Path('solution.py').write_text('not the submission'); print('inspection')", False),
                    }[turn]
                    call = {"name": "run_solution", "args": {"code": code, "submit": submit}, "id": f"call-{turn}"}
                if provider_name == "gemini":
                    parts = [{"text": text}] if call is None else [{"functionCall": call, "thoughtSignature": f"signature-{turn}"}]
                    response = {"modelVersion": config["targets"][provider_name]["model"],
                        "candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}],
                        "usageMetadata": {"promptTokenCount": 30, "candidatesTokenCount": 20, "thoughtsTokenCount": 5, "totalTokenCount": 55}}
                    if turn >= 3:
                        signatures = [p.get("thoughtSignature") for c in request["contents"] for p in c["parts"] if "functionCall" in p]
                        assert "signature-2" in signatures, request
                else:
                    message = {"role": "assistant", "content": text}
                    if call:
                        message["tool_calls"] = [{"id": call["id"], "type": "function", "function": {"name": call["name"], "arguments": json.dumps(call["args"])}}]
                    response = {"model": config["targets"][provider_name]["model"],
                        "choices": [{"message": message, "finish_reason": "tool_calls" if call else "stop"}],
                        "usage": {"prompt_tokens": 30, "completion_tokens": 25, "total_tokens": 55}}
                data = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="pierre-local-proof-", dir="/private/tmp") as tmp:
                root = Path(tmp)
                policy = deepcopy(config)
                target = policy["targets"][provider_name]
                target.update(endpoint=f"http://127.0.0.1:{server.server_port}/fixture", test_only_localhost=True,
                              rpm=1000, tpm=1000000, tpd=None, min_interval_seconds=0)
                # Only synthetic quotas are enlarged to exercise full lifecycle;
                # production quota feasibility is checked separately, never bypassed.
                (root / ".env").write_text(target["credential_env"] + "=synthetic-local-key\n")
                public_dir = root / "tasks/pierre_lbo"
                public_dir.mkdir(parents=True)
                for name, data in public.items():
                    path = public_dir / name
                    path.parent.mkdir(exist_ok=True)
                    path.write_bytes(data)
                (public_dir / "metadata.json").write_bytes((repo / config["public_metadata"]).read_bytes())
                with redirect_stdout(io.StringIO()):
                    code, directory = run_trial(root, policy, provider_name, access_only=False)
                metadata = json.loads((directory / "metadata.json").read_text())
                assert code == 0 and metadata["status"] == "frozen", metadata
                assert (directory / "solution.py").read_text() == source
                assert metadata["submission_run_call"] == 2 and metadata["run_calls"] == 3, metadata
                actual, error = run_submission(directory / "solution.py", json.loads(public["inputs/base_case.json"]), 5)
                benchmark = BENCHMARKS["pierre_lbo"]
                grade = grade_case("loopback_frozen_reference", actual, expected, error,
                                   scoring_groups=benchmark.scoring_groups,
                                   rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
                assert not grade.execution_error and not grade.missing_fields and not grade.mismatches, grade
                assert isinstance(actual, dict) and len(actual) == 55
                results.append({"provider_protocol": provider_name, "loopback_requests": len(requests),
                    "candidate_model_used": False, "synthetic_quotas_enlarged_for_lifecycle": True,
                    "explicit_submission_preserved": True, "fields_matched_to_spreadsheet": 55,
                    "metadata_status": metadata["status"], "request_accounting": metadata["accounting"],
                    "native_signatures_replayed": provider_name == "gemini"})
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    print(json.dumps({"kind": "synthetic_loopback_infrastructure_proof", "real_provider_requests": 0, "results": results}, indent=2))


if __name__ == "__main__":
    main()
