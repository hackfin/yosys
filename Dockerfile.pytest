# Buster slim gcc-8 docker file to build yosys
FROM debian:buster-slim

RUN apt-get update --allow-releaseinfo-change ; \
	apt-get install -y \
	zlib1g-dev pkg-config \
	git python3-dev \
	libboost-dev libboost-filesystem-dev libboost-thread-dev \
	libboost-program-options-dev libboost-python-dev libboost-iostreams-dev \
	bison flex tcl-dev libreadline6-dev libffi-dev \
	python3-pytest \
	iverilog gawk \
	sudo

RUN useradd -u 1000 -g 100 -m -s /bin/bash pyosys && \
	adduser pyosys sudo && \
	echo "pyosys ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/pyosys-nopw

ENV HOME /home/pyosys

COPY . $HOME/src

RUN chown -R pyosys /home/pyosys/src

USER pyosys
RUN cd $HOME && mkdir build && cd build && \
	ln -s ../src/misc . && \
	cp misc/recipes/pyosys-buster.mk Makefile.conf && \
	make -f ../src/Makefile && sudo make -f ../src/Makefile install
# Clean up build:
RUN rm -fr $HOME/build
