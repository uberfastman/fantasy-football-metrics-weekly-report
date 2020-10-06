# set base image
FROM python:3.8-slim

LABEL "org.opencontainers.image.source"="https://github.com/uberfastman/fantasy-football-metrics-weekly-report-app"

# set the working directory in the container
WORKDIR /app/api

# update package index list and install ruby
RUN apt-get update && \
    apt-get install -y vim && \
    apt-get clean

## UNCOMMENT IF USING RUBY SCRIPT FOR CBS AUTHENTICATION!
#RUN apt-get update && \
#    apt-get install -y ruby-full && \
#    apt-get clean
## install httparty gem for ruby
#RUN gem install httparty

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

ENV PYTHONPATH "/app:${PYTHONPATH}"
ENV PYTHONPATH "/app/api:${PYTHONPATH}"

# TODO: only copy code into image once GitHub Container Registry is working with docker-compose
## copy the content of the app directory to the working directory
#COPY . .

# command to run on container start
CMD tail -f /dev/null
