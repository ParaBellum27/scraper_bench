import asyncio, json, os, pathlib, tempfile, sys
from harness.executor import run_solution
from harness.submission import freeze_submission
from evaluator.run_grader import run_submission
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
 with tempfile.TemporaryDirectory(dir='/private/tmp') as root, tempfile.NamedTemporaryFile(prefix='audit-canary-', dir=sys.prefix) as runtime_canary:
  root=pathlib.Path(root); workspace=root/'public'; workspace.mkdir(); private=root/'private'; private.mkdir()
  (workspace/'inputs').mkdir(); (workspace/'inputs/base_case.json').write_text('{"value":42}')
  canary=private/'canary.py'; canary.write_text("VALUE='synthetic-canary'\n")
  (workspace/'escape').symlink_to(canary); (workspace/'.env').write_text('AUDIT_TOKEN=synthetic-canary')
  os.environ['AUDIT_TOKEN']='synthetic-canary'; os.environ['PYTHONPATH']=str(private)
  with canary.open('rb') as fd:
   os.set_inheritable(fd.fileno(),True)
   source=f"""import json, os, socket, subprocess, sys, importlib.util, openpyxl
from pathlib import Path
out={{'env': 'AUDIT_TOKEN' not in os.environ, 'pythonpath': 'PYTHONPATH' not in os.environ, 'openpyxl': bool(openpyxl.__version__)}}
def denied(label, action):
 try: action(); out[label]=False
 except PermissionError: out[label]=True
for label,path in [('absolute',{str(canary)!r}),('symlink','escape'),('dotenv','.env'),('runtime',{runtime_canary.name!r})]:
 denied(label,lambda p=path:Path(p).read_bytes())
def private_import():
 spec=importlib.util.spec_from_file_location('canary',{str(canary)!r}); spec.loader.exec_module(importlib.util.module_from_spec(spec))
denied('import',private_import)
denied('fork',os.fork)
denied('subprocess',lambda:subprocess.run([sys.executable,'-c','print(1)']))
denied('network',lambda:socket.socket().connect(('127.0.0.1',9)))
try:os.read({fd.fileno()},100);out['fd']=False
except OSError:out['fd']=True
print(json.dumps(out))
"""
   (workspace/'solution.py').write_text(source)
   sandbox=run_solution(str(workspace/'solution.py'))
  assert sandbox['exit_code']==0,sandbox
  assert all(json.loads(sandbox['stdout']).values()),sandbox
  params=StdioServerParameters(command=sys.executable,args=[str(pathlib.Path('harness/mcp_server.py').resolve()),'--workspace',str(workspace),'--run-dir',str(private),'--max-run-calls','4'])
  submitted="from pathlib import Path\nPath('solution.py').write_text('mutated')\nprint(42)\n"
  async with stdio_client(params) as streams:
   async with ClientSession(*streams) as session:
    await session.initialize(); tools=await session.list_tools()
    schema=tools.tools[0].inputSchema
    results=[]
    for code,submit in [('print(1)',False),(submitted,True),('print(3)',False)]:
     r=await session.call_tool('run_solution',{'code':code,'submit':submit})
     assert not r.isError,r
     results.append(json.loads(r.content[0].text))
  metadata=freeze_submission(private)
  assert (private/'solution.py').read_text()==submitted
  assert metadata['submission_run_call']==2 and metadata['run_calls']==3
  # Same boundary applies during evaluation, where only source and stdin exist.
  grade_source=private/'grade-probe.py'
  grade_source.write_text(f"import json, os\nfrom pathlib import Path\nout={{'files':sorted(p.name for p in Path('.').iterdir()),'env':'AUDIT_TOKEN' not in os.environ}}\ntry:Path({str(canary)!r}).read_bytes();out['private']=False\nexcept PermissionError:out['private']=True\nprint(json.dumps(out))\n")
  grading,error=run_submission(grade_source,{},5)
  assert error is None and grading=={'files':['solution.py'],'env':True,'private':True},(grading,error)
  print(json.dumps({'sandbox':sandbox,'mcp_schema':schema,'mcp_results':results,'frozen':metadata,'grading':grading},indent=2))
asyncio.run(main())
