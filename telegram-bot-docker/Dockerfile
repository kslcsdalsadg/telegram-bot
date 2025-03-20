FROM python:3.13

RUN mkdir /app
WORKDIR /app

RUN apt update && apt upgrade -y
RUN pip3 install --upgrade pip

# Telegram bot requirements

RUN pip3 install python-telegram-bot python-telegram-bot[callback-data]
RUN pip3 install paho-mqtt
RUN pip3 install docker
RUN pip3 install PyYAML==5.3.1   # Fijamos la versión de PyYAML, que es importada por docker-compose ya que en las versiones siguientes de PyYAML hay un deprecated que aún no se ha corregido en la versión 1.29.2 de docker-compose.
RUN pip3 install docker-compose
RUN pip3 install english-words

RUN apt install -y wakeonlan

# Tapo cameras requirements

RUN pip3 install pytapo certifi==2022.5.18.1 charset-normalizer==2.0.12 idna==3.3 pycryptodome==3.14.1 requests==2.27.1 rtp==0.0.3 urllib3==1.26.9 python-kasa>=0.10.2
RUN apt install -y iputils-ping

ENTRYPOINT [ "python", "/app/bot.py" ]
