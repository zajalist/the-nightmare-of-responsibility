"""A successful mutation envelope must not conceal a failed Blueprint compile."""
from unittest.mock import patch
from held_tool_graphs import Batch

for compile_result in ({'ok':False},{'compiled':False},{'error_count':1},{'error_count':0,'num_errors':1}):
    with patch('held_tool_graphs.call',return_value=dict(ok=True,data=dict(compile=compile_result))):
        try:
            Batch('unused','compile_failure_check').run()
        except AssertionError:
            pass
        else:
            raise AssertionError(('Compile failure accepted',compile_result))
with patch('held_tool_graphs.call',return_value=dict(ok=True,data=dict(compile=dict(ok=True,compiled=True,error_count=0,num_errors=0)))):
    Batch('unused','compile_success_check').run()
print('Batch compile guard passed')
