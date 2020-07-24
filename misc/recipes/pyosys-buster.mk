# Configuration setting for pyosys build on debian buster
CONFIG := gcc
ENABLE_DEBUG := 1
ENABLE_LIBYOSYS := 1
ENABLE_PYOSYS := 1
PREFIX=/usr

ABCREV = default

PYTHON_EXECUTABLE = python3

PYTHON_VERSION_TESTCODE := \
	"import sys;t='{v[0]}.{v[1]}'.format(v=list(sys.version_info[:2]));print(t)"

PYTHON_VERSION := \
	$(shell $(PYTHON_EXECUTABLE) -c ""$(PYTHON_VERSION_TESTCODE)"")

PYTHON_CONFIG := $(PYTHON_EXECUTABLE)-config
PYTHON_PREFIX := $(shell $(PYTHON_CONFIG) --prefix)
PYTHON_DESTDIR := $(DESTDIR)/$(PYTHON_PREFIX)/lib/python$(PYTHON_VERSION)/dist-packages
