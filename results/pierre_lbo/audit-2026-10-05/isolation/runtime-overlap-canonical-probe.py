import importlib.util, json, pathlib, tempfile, sysconfig
from harness.submission import SubmissionSession
from harness.executor import run_solution
package=pathlib.Path(next(iter(importlib.util.find_spec('openpyxl').submodule_search_locations)))
with tempfile.TemporaryDirectory(dir='/private/tmp') as public, tempfile.TemporaryDirectory(prefix='audit-private-',dir=package) as private, tempfile.TemporaryDirectory(prefix='audit-extra-',dir=sysconfig.get_path('stdlib')) as injected:
 w=pathlib.Path(public); p=pathlib.Path(private); extra=pathlib.Path(injected).resolve()/'canary'; extra.write_text('synthetic-canary')
 source=f"from pathlib import Path\nprint(Path({str(p/'step-01.py')!r}).read_text() == Path('solution.py').read_text())\nprint(Path({str(extra)!r}).read_text() == 'synthetic-canary')\n"
 try:
  session=SubmissionSession(w,p,'{}',1,5)
  result=session.execute(source,submit=True)
 except ValueError as exc:result={'rejected':str(exc)}
 print(json.dumps(result))
