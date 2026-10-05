import json,pathlib,tempfile,sysconfig
from harness.executor import run_solution
with tempfile.TemporaryDirectory(dir='/private/tmp') as public, tempfile.TemporaryDirectory(prefix='audit-extra-',dir=sysconfig.get_path('stdlib')) as injected:
 w=pathlib.Path(public); canary=pathlib.Path(injected).resolve()/'canary';canary.write_text('synthetic-canary')
 source=f"from pathlib import Path\nimport sysconfig\ntry: Path({str(canary)!r}).read_text(); print('readable')\nexcept PermissionError: print('denied')\nprint(bool(sysconfig.get_paths()))\n"
 (w/'solution.py').write_text(source)
 print(json.dumps(run_solution(str(w/'solution.py'))))
