FROM python:3.10

RUN mkdir /app
WORKDIR /app

RUN apt update && apt upgrade -y
RUN pip install --upgrade pip

# Telegram bot requirements

RUN pip install python-telegram-bot python-telegram-bot[callback-data] 
RUN pip install paho-mqtt 
RUN pip install docker
RUN pip install PyYAML==5.3.1   # Fijamos la versión de PyYAML, que es importada por docker-compose ya que en las versiones siguientes de PyYAML hay un deprecated que aún no se ha corregido en la versión 1.29.2 de docker-compose.
RUN pip install docker-compose

RUN apt install wakeonlan

# Tapo cameras requirements

RUN git clone https://github.com/JurajNyiri/pytapo.git /tmp/pytapo
RUN mv /tmp/pytapo/pytapo /app
RUN pip install certifi==2022.5.18.1 charset-normalizer==2.0.12 idna==3.3 pycryptodome==3.14.1 requests==2.27.1 rtp==0.0.3 urllib3==1.26.9
RUN apt install -y iputils-ping

ENTRYPOINT [ "python", "/app/bot.py" ]

