# Log capture tests
#
import io
import pytest


design = None
from pyosys import libyosys as ys

from test_wrapper import create_xor

@pytest.yield_fixture(autouse=True, scope='session')
def design_init():
	global design
	d = create_xor()
	design = d.get()
	yield


# Two commands run after another will cause a segfault
CMD_LIST = [ 'ls', 'stat' ]

# This one will complete ok, when called explicitely:
# ```py.test test_logging.py```
#
@pytest.mark.parametrize("cmd", CMD_LIST)
def test_logging(cmd):
	capture = io.StringIO()
	ys.log_to_stream(capture)
	if isinstance(cmd, list):
		for c in cmd:
			ys.run_pass(c, design)
	else:
		ys.run_pass(cmd, design)
	ys.log_pop()

	print(capture.getvalue())
	
# FIXME: Currently, this test throws a segfault on more than one commands
# therefore the test suite can not complete.
CMD_LIST_X = ['ls']
@pytest.mark.parametrize("cmd", CMD_LIST_X)
def test_logging_twice(cmd):
	capture = io.StringIO()
	ys.log_to_stream(capture)
	ys.run_pass(cmd, design)
	ys.log_pop()

	print(capture.getvalue())
	
	capture = io.StringIO()
	ys.log_to_stream(capture)
	ys.run_pass(cmd, design)
	ys.log_pop()

	print(capture.getvalue())

