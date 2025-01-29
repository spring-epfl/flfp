FROM --platform=linux/amd64 debian:stable

RUN export DEBIAN_FRONTEND="noninteractive" && \
apt-get update && \
apt-get upgrade -y && \
apt-get autoremove -y && \
apt-get install --no-install-recommends -y \
apt-utils \
build-essential \
git \
libdbus-glib-1-2 \
libffi-dev \
libgtk-3-0 \
libx11-xcb1 \
libxt6 \
nodejs \
npm \
pkgconf \
python3-dev \
python3-pip \
wget \
xvfb \
tmux \
&& \
apt-get clean -y


COPY miniconda.sha256 /

ENV CONDA_DIR=/opt/conda

RUN cd / && \
wget https://repo.anaconda.com/miniconda/Miniconda3-py39_24.11.1-0-Linux-x86_64.sh && \
sha256sum -c miniconda.sha256 && \
bash Miniconda3-py39_24.11.1-0-Linux-x86_64.sh -b -p /opt/conda

ENV PATH=$CONDA_DIR/bin:$PATH

RUN conda config --set always_yes yes --set changeps1 no && \
conda update -q conda && \
conda info -a

COPY environment.yml /environment.yml

RUN cd / && \
conda env create -f environment.yml

# activate conda in .bashrc
RUN echo "source /opt/conda/etc/profile.d/conda.sh\nconda activate flfpenv" >> ~/.bashrc
SHELL ["conda", "run", "-n", "flfpenv", "/bin/bash", "-c"]

# add source code

RUN mkdir /flfp

COPY conf /flfp/conf
COPY scripts /flfp/scripts
COPY src /flfp/src
COPY tests /flfp/tests
COPY .env /flfp/.env

WORKDIR /flfp

# install local packages as root
RUN bash scripts/manage/manage.sh lib install

# also install the node Aglint package to prevent in-script errors
RUN npm --prefix src/filterlist_parser/filterlist_parser/aglint-util install

ENTRYPOINT ["/bin/bash"]