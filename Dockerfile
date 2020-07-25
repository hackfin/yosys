# Buster slim gcc-8 docker file to build yosys

# two stage variant for reduced image result

# builder stage:
FROM debian:buster-slim AS builder

RUN apt-get update --allow-releaseinfo-change ; \
 	apt-get install -y --no-install-recommends \
	sudo make g++ \
	libboost-dev libboost-filesystem-dev libboost-thread-dev \
 	libboost-program-options-dev libboost-python-dev \
	libboost-iostreams-dev \
	bison flex tcl-dev libreadline6-dev libffi-dev \
 	python3-dev \
 	pkg-config git

RUN apt-get install -y \
    ca-certificates


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
	make -f ../src/Makefile && sudo make -f ../src/Makefile install && \
	make -f ../src/Makefile clean

# Runner stage:

FROM debian:buster-slim AS runner
RUN apt-get update --allow-releaseinfo-change ; \
 	apt-get install -y --no-install-recommends \
	sudo \
 	iverilog gawk \
	libpython3.7 \
	libboost-python1.67 libboost-system1.67 libboost-filesystem1.67 \
	tcl python3-pytest && \
    apt-get -y remove libgcc-8-dev && \
    apt-get autoclean && \
	apt-get clean && \
	apt-get -y autoremove && \
	rm -rf /var/lib/apt/lists

RUN useradd -u 1000 -g 100 -m -s /bin/bash pyosys && \
	adduser pyosys sudo && \
	echo "pyosys ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/pyosys-nopw

ENV HOME /home/pyosys

COPY . $HOME/src

RUN chown -R pyosys /home/pyosys/src

COPY --from=builder /usr/bin/yosys* /usr/bin/
COPY --from=builder /usr/lib/python3.7/dist-packages/pyosys \
	/usr/lib/python3.7/dist-packages/pyosys
COPY --from=builder /usr/share/yosys /usr/share/yosys

USER pyosys
