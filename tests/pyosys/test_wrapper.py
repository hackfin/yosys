# Python convenience class wrapper test

import pytest

from auxiliaries import *

def create_xor():
	d = Design()
	m = d.addModule("top", "gna")
	a = m.addWire("a", 1, True)
	b = m.addWire("b", 1, True)
	q = m.addWire("q", 1, True)
	m.finish()
	cell = m.addXor(ID("XOR"), YSignal(a), YSignal(b), YSignal(q))
	return d

def test_design():
	d = create_xor()
