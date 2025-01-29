FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

ENV CHROMEDRIVER_VERSION=113.0.5672.63
# ENV CHROMEDRIVER_VERSION=120.0.6099.10900

# Google Chrome
# =============
RUN apt-get update && \
    apt-get -y install --no-install-recommends gnupg2 wget ca-certificates unzip

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | \
    apt-key add -

# RUN echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/chrome.list
# RUN apt-get update && \
#     apt-get -y install --no-install-recommends google-chrome-stable \
#         xvfb xauth x11-utils

RUN wget -q https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin && \
    rm /tmp/chromedriver.zip

RUN wget -q 'https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F1121461%2Fchrome-linux.zip?generation=1679615958002864&alt=media' -O /tmp/chrome_113.zip && \
    unzip /tmp/chrome_113.zip -d /usr/local/bin && \
    rm /tmp/chrome_113.zip && \
    mv /usr/local/bin/chrome-linux /usr/local/bin/chrome

# Python
# ==========
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3.10-venv

#mpstat
# ==========
RUN apt-get install && apt-get install -y sysstat

RUN apt-get update && apt-get install -y xvfb

RUN apt-get install -y libnss3-dev libgdk-pixbuf2.0-dev libgtk-3-dev libxss-dev libasound2-dev libasound2 default-jre

ADD requirements.txt /tmp/
RUN pip3 install -U -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

RUN useradd -ms /bin/bash seluser
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

ADD extensions/ \
    /home/seluser/measure/extensions

RUN wget -q 'https://github.com/lightbody/browsermob-proxy/releases/download/browsermob-proxy-2.1.4/browsermob-proxy-2.1.4-bin.zip' -O /tmp/browsermob-proxy.zip && \
    unzip /tmp/browsermob-proxy.zip -d /home/seluser/measure && \
    rm /tmp/browsermob-proxy.zip

RUN chmod +x /home/seluser/measure/browsermob-proxy-2.1.4/bin/browsermob-proxy

ADD cpu.py \
    stats.py \
    /home/seluser/measure/

ADD test.py \
    /home/seluser/measure/

ADD web.py \
    /home/seluser/measure/

ADD filterlists/ \
    /home/seluser/measure/filterlists
    
RUN apt-get install -y --no-install-recommends xvfb xserver-xephyr tigervnc-standalone-server x11-utils gnumeric

COPY entrypoint.sh /home/seluser/measure/
RUN chmod +x /home/seluser/measure/entrypoint.sh

# Open necessary ports
EXPOSE 8080 8081

RUN chown seluser:seluser -R /home/seluser/measure

USER seluser

WORKDIR /home/seluser/measure

ENTRYPOINT ["/home/seluser/measure/entrypoint.sh"]
