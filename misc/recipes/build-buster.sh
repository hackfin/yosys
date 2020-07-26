# Runner to build pyosys docker container
#
# e.g. drag into Docker playground and execute: `sh build-buster.sh`
git clone https://github.com/hackfin/yosys.git -b pytest
cd yosys && docker build -t pyosys . && echo DONE building.
docker images pyosys
echo Running tests
docker run -it --rm pyosys /home/pyosys/src/tests/pyosys/run-test.sh
