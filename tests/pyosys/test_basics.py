# Basic pyosys functionality test
#
# Crucial tests to get the pyosys API up

from auxiliaries import ID, PID


def create_minimum_design(name):
	"Creates a minimum XOR wrapper module"
	from pyosys import libyosys as ys
	_S = ys.SigSpec
	d = ys.Design()
	m = d.addModule(ID(name))
	a = m.addWire(PID("a"), 1)
	b = m.addWire(PID("b"), 1)
	q = m.addWire(PID("q"), 1)
	cell = m.addXor(ID("XOR"), _S(a), _S(b), _S(q))
	return d, m

def test_import():
	from pyosys import libyosys as ys

def test_design_module():
	"""Make sure a module can be renamed and is found in the
modules_ member list"""
	from pyosys import libyosys as ys
	design, unit = create_minimum_design("bla_private")
	identifier = PID("toplevel_public")
	design.rename(unit, identifier)
	new_unit_ref = design.modules_[identifier]
	ref_identifier_str = 'Module "\\toplevel_public"'
	if repr(new_unit_ref) != ref_identifier_str:
		raise ValueError("Module with id '%s': string repr mismatch" % \
			identifier.str())

def test_changes():
	from pyosys import libyosys as ys
	reference = \
		['AttrObject', 'CaseRule', 'Cell', 'CellType', 'CellTypes',
	'Const', 'ConstEval', 'ConstFlags', 'CppMonitor', 'CppPass',
	'Design', 'GetSize', 'IdString', 'Initializer', 'Memory', 'Module',
	'Monitor', 'Pass', 'Process', 'Selection', 'SigBit', 'SigChunk',
	'SigMap', 'SigSpec', 'State', 'SwitchRule', 'SyncRule', 'SyncType',
	'Wire', 'Yosys', '__doc__', '__file__', '__loader__', '__name__',
	'__package__', '__spec__', '_hidden', 'ceil_log2',
	'check_file_exists', 'const_add', 'const_and', 'const_div',
	'const_divfloor', 'const_eq', 'const_eqx', 'const_ge', 'const_gt',
	'const_le', 'const_logic_and', 'const_logic_not',
	'const_logic_or', 'const_lt', 'const_mod', 'const_modfloor',
	'const_mul', 'const_ne', 'const_neg', 'const_nex', 'const_not',
	'const_or', 'const_pos', 'const_pow', 'const_reduce_and',
	'const_reduce_bool', 'const_reduce_or', 'const_reduce_xnor',
	'const_reduce_xor', 'const_shift', 'const_shiftx', 'const_shl',
	'const_shr', 'const_sshl', 'const_sshr', 'const_sub',
	'const_xnor', 'const_xor', 'escape_filename_spaces',
	'escape_id', 'glob_filename', 'is_absolute_path', 'load_plugin',
	'log', 'log_assert_worker', 'log_backtrace', 'log_cell',
	'log_check_expected', 'log_dump_args_worker',
	'log_dump_val_worker', 'log_experimental', 'log_file_info',
	'log_file_warning', 'log_flush', 'log_header', 'log_module',
	'log_pop', 'log_push', 'log_reset_stack', 'log_spacer',
	'log_suppressed', 'log_to_stream', 'log_warning',
	'log_warning_noprefix', 'log_wire', 'make_temp_dir',
	'make_temp_file', 'memhasher', 'memhasher_do', 'memhasher_off',
	'memhasher_on', 'new_id', 'next_token', 'patmatch',
	'proc_program_prefix', 'proc_self_dirname', 'proc_share_dirname',
	'remove_directory', 'rewrite_filename', 'run_backend',
	'run_frontend', 'run_pass', 'shell', 'split_tokens', 'stringf',
	'unescape_id', 'yosys_banner', 'yosys_setup', 'yosys_shutdown',
	'ys_debug']

	for i, e in enumerate(reference):
		d = dir(ys)
		if not e in d:
			print(d)
			raise ValueError("libyosys API has changed: missing: %s " % (e))

