# pyosys test auxiliaries
#
# forked from jupyosys, stripped MyHDL dependencies
#
# (c) 2020, section5.ch
#

from pyosys import libyosys as ys

from ysdebug import *
import ast

class SynthesisMapper:
	def __init__(self, el_type, is_signed = False):
		self.el_type = el_type
		self.q = None
		self.trunc = False # True when truncation allowed
		self.is_signed = is_signed

def YSignal(x):
	return ys.SigSpec(x.get())

def ConstSignal(x, l = None):
	c = Const(x, l)
	return ys.SigSpec(c.get())

def HighZ(l):
	return ConstSignal(ys.State.Sz, l)

def NEW_ID(name, node, ext):
	return ys.new_id(name, node.lineno, ext)

def OBJ_ID(name, src, ext):
	return ys.IdString("$" + name + "\\" + src + "\\" + ext)

def ID(x):
	return ys.IdString("$" + x)

def PID(x):
	return ys.IdString("\\" + x)


def match(a, b):
	"Match signal lengths"

	la, lb = a.q.size(), b.q.size()

	l = la
	trunc = False

	c = 0
	if la < lb: # and isinstance(node.left.obj, _Signal):
		if a.is_signed and not b.is_signed:
			print("A < B")
			lb += 1
			trunc = True
		l = lb
		tmp = ys.SigSpec(a.q)
		tmp.extend_u0(l, a.is_signed)
		a.q = tmp
	elif la > lb: # and isinstance(node.right.obj, _Signal):
		if b.is_signed and not a.is_signed:
			print("A > B")
			l += 1
			trunc = True

		tmp = ys.SigSpec(b.q)
		tmp.extend_u0(l, b.is_signed)
		b.q = tmp
	else:
		# Nasty one: If signednesses are not equal,
		# we need one more headroom bit to determine
		if a.is_signed != b.is_signed:
			print("A == B, no equal signedness")
			l += 1
			tmp0, tmp1 = a.q, b.q
			tmp0.extend_u0(l, a.is_signed)
			tmp1.extend_u0(l, b.is_signed)
			a.q, b.q = tmp0, tmp1
			trunc = True
	return l, trunc
class Wire:
	"Tight wire wrapper"

	def __init__(self, wire):
		self.wire = wire

	def get(self):
		return self.wire

	def setDirection(self, IN = False, OUT = False):
		self.wire.port_input = IN
		self.wire.port_output = OUT

	def __getattr__(self, name):
		return getattr(self.wire, name)

class Const:
	"Tight yosys Const wrapper"
	def __init__(self, value, bits = None):
		if isinstance(value, int):
			if bits == None:
				l = value.bit_length()
				if value < 0:
					l += 1 # Fixup to compensate python's awareness
				elif l < 1:
					l = 1
				# We might run into overflow issues from the yosys side,
				# create a bit vector then:
				if l == 32:
					bitvector = bitfield(value)
					# print("long val %x[%d]" % (int(value), bits))
					self.const = ys.Const(bitvector)
				else:
					self.const = ys.Const(value, l)
			else:
				self.const = ys.Const(value, bits)
		elif isinstance(value, bool):
			self.const = ys.Const(int(value), 1)
		elif isinstance(value, str):
			self.const = ys.Const(value)
		else:
			raise ValueError("Unsupported Const type `%s`" % type(value))

	def get(self):
		return self.const

	def __getattr__(self, name):
		return getattr(self.const, name)


class Cell:
	"Userdefined or built-in technology cell"
	def __init__(self, cell):
		self.cell = cell

	def setPort(self, name, port):
		if isinstance(port, int):
			port = ConstSignal(port, 32)
		elif isinstance(port, bool):
			port = ConstSignal(int(port), 1)
		self.cell.setPort(PID(name), port)

	def setParam(self, name, c):
		if isinstance(c, int):
			self.cell.setParam(PID(name), Const(c, 32).get())
		else:
			self.cell.setParam(PID(name), Const(c).get())

class BBInterface:
	"Black box interface"
	def __init__(self, name, module):
		self.sigdict = None
		self.interface = {}
		self.name = name
		self.module = module
		self.main_out = None # XXX Hack

	def getId(self):
		return PID(self.name)

	def toInitData(self, values_list, dbits):
		init_data = ConstSignal(values_list[0], dbits)
		for i in values_list[1:]:
			init_data.append(ConstSignal(i, dbits))

		return init_data

	def getOutputs(self):
		"This is a hack for now, as we support one output per assignment only"
		return [ self.main_out ]


	def addConst(self, val, len = 32):
		if isinstance(val, int):
			return ConstSignal(val, len)
		else:
			return ConstSignal(val)

	def createSignal(self, wire, name):
		l = wire.size()
		sig = myhdl.Signal(intbv()[l:])
		sig._name = name
		self.interface[name] = ( wire, False )
		return sig

	def addPort(self, sigid, out = False):
		m = self.module
		sig = self.sigdict[sigid]

		if sigid in self.interface:
			# print("preassigned wire for '%s'" % sigid)
			sigspec, _ = self.interface[sigid]
		else:
			s = len(sig)
			# self.name + '_' + sig._name
			w = m.addWire(None, s, True)
			sigspec = ys.SigSpec(w.get())
			if out:
				# Fixme: Within assign statements, we can have only
				# one output for now (no record assignments)
				#
				self.main_out = sigspec # Record last assigned output

			self.interface[sigid] = ( sigspec, out )

		otype = OUTPUT if out else INPUT
		m.iomap[sigid] = [otype, sig]
			
		return sigspec

	def __repr__(self):
		a = "{ Inferface: \n"
		for n, i in self.interface.items():
			a += "\t%s : %s \n" % (n, i.as_wire().name.str())
		a += "}\n"

		return a

	def wireup(self, defer = False):	
		"When defer == True, do not connect outputs"
		m = self.module
		for n, i in self.interface.items():

			s, direction = i
			sig = m.findWireByName(n, True)
			# Reversed!
			if direction == 0:
				m.connect(s, sig)
			else:
				if defer:
					pass
				else:
					m.connect(sig, s)


class Module:
	"Yosys module wrapper"

	EX_COND, EX_FIRST, EX_SAME, EX_CARRY, EX_TWICE, EX_TRUNC = range(6)

	_unopmap = {
		ast.USub	 :	 ys.Module.addNeg,
		ast.Invert	 :	 ys.Module.addNot,
		ast.Not		 :	 ys.Module.addNot,
	}

	_binopmap = {
		ast.Add		 : ( ys.Module.addAdd,	 EX_CARRY ),
		ast.Sub		 : ( ys.Module.addSub,	 EX_SAME ),
		ast.Mult	 : ( ys.Module.addMul,	 EX_TWICE ),
		ast.Div		 : ( ys.Module.addDiv,	 EX_SAME ),
		ast.Mod		 : ( ys.Module.addMod,	 EX_TRUNC ),
		ast.Pow		 : ( ys.Module.addPow,	 EX_SAME ),
		ast.LShift	 : ( ys.Module.addSshl,	 EX_FIRST ),
		ast.RShift	 : ( ys.Module.addSshr,	 EX_FIRST ),
		ast.BitOr	 : ( ys.Module.addOr,	 EX_SAME ),
		ast.BitAnd	 : ( ys.Module.addAnd,	 EX_SAME ),
		ast.BitXor	 : ( ys.Module.addXor,	 EX_SAME ),
		ast.FloorDiv : ( ys.Module.addDiv,	 EX_SAME ),
		ast.UAdd	 : ( ys.Module.addAdd,	 EX_SAME ),
		ast.USub	 : ( ys.Module.addSub,	 EX_SAME ),
		ast.Eq		 : ( ys.Module.addEq,	 EX_COND ),
		ast.Gt		 : ( ys.Module.addGt,	 EX_COND ),
		ast.GtE		 : ( ys.Module.addGe,	 EX_COND ),
		ast.Lt		 : ( ys.Module.addLt,	 EX_COND ),
		ast.LtE		 : ( ys.Module.addLe,	 EX_COND ),
		ast.NotEq	 : ( ys.Module.addNe,	 EX_COND ),
		ast.And		 : ( ys.Module.addAnd,	 EX_SAME ),
		ast.Or		 : ( ys.Module.addOr,	 EX_SAME )
	}

	_boolopmap = {
		ast.And		 : ys.Module.addReduceAnd,
		ast.Or		 : ys.Module.addReduceOr,
		ast.Not		 : ys.Module.addNot
	}

	def __init__(self, m, implementation, design):
		self.module = m
		self.wires = {} # Local module wires
		self.cache_mem = {}
		self.variables = {}
		self.wireid = {}
		self.parent_signals = {}
		self.memories = {}
		self.arrays = {}
		self.inferred_memories = {}  # Maybe temporary: Track inferred memories
		self.iomap = {}
		self.guard = {}
		self.implementation = implementation
		self.array_limit = 1024
		self.parent_design = design

		def dummy(a, col = None):
			pass

		if not ENABLE_DEBUG:
			self.debugmsg = dummy

		self._namespace = \
			[ self.memories, self.arrays, self.wires, self.parent_signals ]

	def warning(self, msg, col = REDBG):
		print(col + "WARNING:" + msg + OFF)
	
	def debugmsg(self, msg, col = REDBG):
		print(col + msg + OFF)
	
	def __getattr__(self, name):
		return getattr(self.module, name)

	def apply_compare(self, node, a, b):
		op = node.ops[0]

		# Have to sort out cases:

		l, _ = match(a, b)

		if a.is_signed or b.is_signed:
			is_signed = True
		else:
			is_signed = False

		sm = SynthesisMapper(SM_BOOL)
		sm.q = self.addSignal(None, 1)
		name = NEW_ID(__name__, node, "cmp")

		if a.q.size() != b.q.size():
			raise AssertionError

		f = self._binopmap[type(op)][0]
		f(self.module, name, a.q, b.q, sm.q, is_signed)
		return sm

	def apply_binop(self, node, a, b):

		f, ext = self._binopmap[type(node.op)]

		if a.is_signed or b.is_signed:
			is_signed = True
		else:
			is_signed = False

		sm = SynthesisMapper(SM_WIRE, is_signed)

		if ext == self.EX_COND:
			l = 1
		elif ext == self.EX_FIRST:
			l = a.q.size()
			trunc = False
		elif ext == self.EX_TWICE:
			l, trunc = match(a, b)
			l *= 2
		elif ext == self.EX_SAME:
			l, trunc = match(a, b)
		elif ext == self.EX_TRUNC:
			l = b.q.size()
			trunc = True
		elif ext == self.EX_CARRY:
			l, trunc = match(a, b)
			if not trunc:
				l += 1
			trunc = True


		sm.trunc = trunc

		# print("Add wire with name %s, size %d" % (name, l))
		sm.q = self.addSignal(None, l)
		name = NEW_ID(__name__, node, "binop_%s" % ("s" if is_signed else "u"))

		f(self.module, name, a.q, b.q, sm.q, is_signed)

		return sm

	def apply_unop(self, name, op, a, q):
		self._unopmap[type(op)](self.module, name, a, q)

	def connect(self, dst, src):
		if dst.size() != src.size():
			self.debugmsg("CONNECT: Size mismatch: %d != %d" % (src.size(), dst.size()))
			if src.is_wire():
				srcname = src.as_wire().name
			else:
				srcname = "[MAYBE CONST]"
			raise ValueError("Signals '%s' and '%s' don't have the same size" % \
				(dst.as_wire().name, srcname))
		return self.module.connect(dst, src)

	def guard_name(self, name, which):
		if name in self.guard:
			raise KeyError("%s already used : %s" % (name, repr(self.guard[name])))
		self.guard[name] = which

	def addWire(self, name, n, public=False):
		# print(type(name))
		if isinstance(name, str):
			# print("not a IDstring name")
			if public:
				name = PID(name)
			else:
				name = ID(name)
		elif not name:
			name = ys.new_id(__name__, lineno(), "")

		frame = inspect.currentframe()
		info = inspect.getouterframes(frame)[2] 
		source = "%s:%d" % (info[1], info[2])

		self.guard_name(name, source)

		return Wire(self.module.addWire(name, n))

	def addSignal(self, name, n, public = False):
		w = self.addWire(name, n, public)
		w.port_input = False
		w.port_output = False
		return ys.SigSpec(w.get())

	def addMux(self, *args):
		name = args[0]
		self.guard_name(name, True)
		return self.module.addMux(*args)

	def addCell(self, name, celltype, builtin = False):
		if builtin:
			ct = PID(celltype)
		else:
			ct = ID(celltype)
		if isinstance(name, str):
			identifier = ID(name)
		else:
			identifier = name
		return Cell(self.module.addCell(identifier, ct))

	def addSimpleCell(self, name, which, in_a, in_b, out_y):
		c = self.addCell(name, which)
		c.setPort("A", in_a)
		c.setPort("B", in_b)
		c.setPort("Y", out_y)

	def getCorrespondingWire(self, sig):
		if not sig._id:
			if sig.read or sig.driven:
				raise ValueError("Can not have None as ID for %s::`%s`.\n"	% (self.name, sig._name) + \
				"Possibly, a class signal member is unused in this hierarchy level\n" + \
				"You may have to explicitely set the ID in the top level wrapper to use\n" + \
				"this signal in synthesis or use a BulkSignal class in the interface.")
			else:
				identifier = "unused::%s" % sig._name
				self.warning("Adding stub for unused signal '%s'" % sig._name)
				w = self.addSignal(identifier, len(sig), False)
				return w
		else:
			identifier = self.wireid[sig._id]
			w = self.findWireByName(identifier)
			if not w:
				raise KeyError("Wire `%s` not found" % identifier)
			return w

	def findWire(self, sig, reserved = False):
		# TODO: Simplify, once elegant handling found
			
		# We've got a purely local signal
		identifier = sig._name
		if not reserved:
			return self.findWireByName(identifier)
		else:
			print(REDBG + \
				"UNDEFINED/UNUSED wire, localname: %s, origin: %s" % (a._name, a._id) + OFF)
			raise KeyError("Local signal not found")

		return elem

	def findWireByName(self, identifier, throw_exception = False):
		if identifier in self.memories:
			elem = self.memories[identifier]
		elif identifier in self.arrays:
			elem = self.arrays[identifier]
		elif identifier in self.wires:
			elem = self.wires[identifier]
		elif identifier in self.variables:
			elem = self.variables[identifier]
		elif throw_exception:
			raise KeyError("Wire '%s' not found" % identifier)
		else:
			elem = None

		return elem

	def iomap_set_porttype(self, n, sig, otype):
		self.iomap[n] = [otype, sig]

	def iomap_set_output(self, n, sig, is_out):
		otype = OUTPUT if is_out else INPUT
		self.iomap[n] = [otype, sig]
	
	def signal_output_type(self, name):
		return self.iomap[name]

	def collectAliases(self, sig, name):
		"Collect alias signals from Shadow signal"
		shadow_sig = self.addSignal('alias_' + name, 0)
		self.debugmsg("COLLECT SHADOWS FOR '%s'" % name, col = GREEN)
		self.wireid[sig._id] = name
		for a in reversed(sig._args):
			if isinstance(a, _Signal):
				identifier = a._id
				elem = self.getCorrespondingWire(a)

			elif isinstance(a, (intbv, bool)):
				elem = ConstSignal(a)
			else:
				raise ValueError("Unsupported alias argument in ConcatSignal")

			shadow_sig.append(elem)
		self.wires[name] = shadow_sig

	def dump_wires(self):
		print(REDBG + "=== WIRE DUMP ===" + OFF)
		for n, i in self.wireid.items():
			w = self.wires[i]
			if w.is_wire():
				t = w.as_wire()
				pi, po = t.port_input, t.port_output

				print("WIRE '%s' : \t<%s> IN: %s OUT: %s" % (n, i, pi, po))
			else:
				print("CONST '%s' : \t<%s>" % (n, i))
		print(REDBG + "=================" + OFF)
	
	def _gather_io(self, instance, args, l):
		sigs = instance.sigdict

		def sig_otype(iomap, arg, name, inputs, outputs):

			if isinstance(arg, _Signal):
				if not name in iomap:
					if isinstance(arg, _TristateSignal):
						otype = INOUT
					elif name in inputs:
						if name in outputs:
							otype = INOUT
						else:
							otype = INPUT
					elif name in outputs:
						otype = OUTPUT
					else:
						self.debugmsg("Undetermined I/O state of %s" % name)
						otype = HIGHZ
					iomap[name] = [otype, arg]
				else:
					self.debugmsg("I/O inherited: %s" % name)

			elif hasattr(arg, '__dict__'):
				for mn, member in arg.__dict__.items():
					identifier = "%s_%s" % (name, mn)
					sig_otype(iomap, member, identifier, inputs, outputs)

		inputs, outputs = instance.get_io()

		for i, a in enumerate(args):
			name, param = a
			if not name in self.iomap:
				if name in sigs:
					sig = sigs[name]
					sig_otype(self.iomap, sig, name, inputs, outputs)
				elif i < l:
					arg = instance.obj.args[i]
					sig_otype(self.iomap, arg, name, inputs, outputs)
			else:
				self.debugmsg("GATHER_IO: skip %s" % name)

	def collectMemories(self, instance):
		for m in instance.memdict.items():
			print("SIGNAL ARRAY '%s'" % m[0])
			self.memories[m[0]] = ( m[1] )

	def addMemory(self, name):
		mem = ys.Memory()
		identifier = PID(name)
		mem.name = identifier
		self.cache_mem[identifier] = mem

		return mem

	def finish(self, fixup = True):
		m = self.module
		# Fix up for I/O sanity after redefinition:
		# print(REDBG + "FIXUP PORTS FOR %s" % m.name + OFF)
		if fixup:
			m.fixup_ports()
		m.memories = self.cache_mem
		m.avail_parameters = self.avail_parameters


class Design:
	"Simple design wrapper"
	def __init__(self, name="top"):
		self.design = ys.Design()
		self.name = name
		self.modules = {}
		self.mapper = None

	def map(self, **kwargs):
		if not self.mapper:
			raise SystemError("No mapper defined")

		# Call the mapper 'method':
		self.mapper.map(self, **kwargs)

	def get(self):
		return self.design

	def addModule(self, name, implementation, public = False):
		print(GREEN + "Adding module with name:"  + OFF, name)
		if public:
			n = PID(name)
		else:
			n = ID(name)
		m = self.design.addModule(n)
		m = Module(m, implementation, self)
		self.modules[name] = m
		return m

	def set_top_module(self, top, private = False):
		key = create_key(top.obj)
		pre = "$" if private else "\\"
		ys.run_pass("hierarchy -top %s%s" % (pre, key), self.design)

	def top_module(self):
		return Module(self.design.top_module(), None, self)

	def run(self, cmd, silent = True):
		"Careful. This function can exit without warning"
		if not silent:
			print("Note: Capturing currently broken")
#		capture = io.StringIO()
#		ys.log_to_stream(capture)
		if isinstance(cmd, list):
			for c in cmd:
				ys.run_pass(c, self.design)
		else:
			ys.run_pass(cmd, self.design)
#		ys.log_pop()
#
#		if not silent:
#			print(capture.getvalue())
#		else:
#			return capture.getvalue()
		

	def display_rtl(self, selection = "", fmt = None, full = False):
		"Display first stage RTL"
		design = self.design
		print("Display...")
		# ys.run_pass("ls", design)
		#
		sel = selection
		if fmt:
			fmt = "-format " + fmt
			if full:
				sel = "*"
		else:
			fmt = ""
		ys.run_pass("show %s -prefix %s %s" % (fmt, self.name, sel), design)

	def display_dir(self):
		ys.run_pass("ls", self.design)

	def write_ilang(self, name = "top"):
		ys.run_pass("write_ilang %s_mapped.il" % name, self.design)

	def import_verilog(self, filename, library = False):
		if library:
			libflag = '-lib'
		else:
			libflag = ''

		ys.run_pass("read_verilog %s %s" % (libflag, filename), self.design)

	def finalize(self, name = None):
		"Finalize design so that it is visible"
		design = self.design
		m = design.top_module()

		if name == None:
			name = self.name

		design.rename(m, PID(name))

	def write_verilog(self, name, rename_default = False, rename_signals = True):
		"Write verilog"
		ys.run_pass("ls; check")
		ys.run_pass("hierarchy -check")
		if name == None:
			name = "uut"
		design = self.design
		m = design.top_module()
		if rename_default:
			design.rename(m, ys.IdString("\\" + name))
		if rename_signals:
			ys.run_pass("write_verilog %s_mapped.v" % name, design)
		else:
			# Can cause failures in cosim: TODO investigate
			ys.run_pass("write_verilog -norename %s_mapped.v" % name, design)


	def test_synth(self):
		design = self.design
		ys.run_pass("memory_collect", design)
		# We don't test on that level yet
		# ys.run_pass("techmap -map techmap/lutrams_map.v", design)
		# ys.run_pass("techmap -map ecp5/brams_map.v", design)
		# ys.run_pass("techmap -map ecp5/cells_map.v", design)
		ys.run_pass("write_ilang %s_mapped.il" % self.name, design)
		ys.run_pass("hierarchy -check", design)

