FROM python:3.10

RUN mkdir /app
WORKDIR /app

RUN apt update && apt upgrade -y
RUN pip install --upgrade pip

# Telegram requirements

RUN pip install python-telegram-bot python-telegram-bot[callback-data] paho-mqtt docker docker-compose

# Tapo requirements

RUN git clone https://github.com/JurajNyiri/pytapo.git /tmp/pytapo
RUN mv /tmp/pytapo/pytapo /app
RUN pip install certifi==2022.5.18.1 charset-normalizer==2.0.12 idna==3.3 pycryptodome==3.14.1 requests==2.27.1 rtp==0.0.3 urllib3==1.26.9
RUN apt install -y iputils-ping

ENTRYPOINT [ "python", "/app/bot.py" ]

