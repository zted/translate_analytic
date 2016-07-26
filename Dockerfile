FROM centos:7
ENV thrift_version=0.9.3 concrete_version=master
MAINTAINER Ted <tedz.cs@gmail.com>

WORKDIR /tmp

RUN yum update -y && \
    yum install epel-release -y && \
    yum install -y git libtool make boost zlib-devel gcc-c++ byacc flex python-devel wget java-1.8.0-openjdk-devel protobuf-compiler maven patch which python-pip numpy python-bottle python-flask python-django && \
    yum clean all -y

RUN git clone https://github.com/apache/thrift.git && \
    cd thrift && \
    git checkout ${thrift_version} && \
    ./bootstrap.sh && \
    ./configure --prefix=/home/dockeruser/local --without-python --without-java && \
    make && \
    make install && \
    export PATH=${PATH}:/home/dockeruser/local/bin && \
    cd lib/py && \
    python setup.py install --user

RUN git clone https://github.com/hltcoe/concrete.git && \
    git clone https://github.com/hltcoe/concrete-python.git && \
    cd concrete-python && git checkout d90fd27a2720eebd2e07157206e2b40bb4f2132e && cd .. && \
    export PATH=${PATH}:/home/dockeruser/local/bin && \
    cd concrete-python && \
    ./build.bash --raw && \
    ./reinstall.bash

COPY analytic/keyword_translator.py /opt/scripts/
COPY data /opt/data

CMD cd /opt/scripts && \
    python keyword_translator.py -dictionary /opt/data/lex.en-zh