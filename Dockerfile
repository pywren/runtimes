from amazonlinux

RUN yum install -y tar gzip wget gcc awscli zlib zlib-devel openssl-devel libffi-devel

WORKDIR /usr/src
RUN wget https://www.python.org/ftp/python/3.7.11/Python-3.7.11.tgz
RUN tar xzf Python-3.7.11.tgz
WORKDIR /usr/src/Python-3.7.11
RUN ./configure --enable-optimizations
RUN make install
RUN rm /usr/src/Python-3.7.11.tgz

#ENV CONDA_DIR /opt/conda

#RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
#    /bin/bash ~/miniconda.sh -b -p /opt/conda

#ENV PATH=$CONDA_DIR/bin:$PATH
RUN python3.7 -m pip install --upgrade pip
RUN python3.7 -m pip install boto3 cloudpickle pyaml glob2

COPY *.py /var/runtimes/

