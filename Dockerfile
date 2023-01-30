FROM python:slim-buster

WORKDIR /app

COPY ./requirements.txt .

RUN apt update
RUN apt upgrade -y
RUN yes | apt install curl
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./ .

EXPOSE 5000
EXPOSE 5555
EXPOSE 5556
EXPOSE 8883
ENV HOST=0.0.0.0
CMD [ "python", "-u", "./main.py"]
