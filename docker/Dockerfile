ARG PYTHON_VERSION_MAJOR=$PYTHON_VERSION_MAJOR
ARG PYTHON_VERSION_MINOR=$PYTHON_VERSION_MINOR
ARG PYTHON_VERSION_PATCH=$PYTHON_VERSION_PATCH

# set base image
FROM --platform=linux/amd64 python:${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}.${PYTHON_VERSION_PATCH}-slim

LABEL "org.opencontainers.image.source"="https://github.com/uberfastman/fantasy-football-metrics-weekly-report"

# update package index list
RUN apt update && \
    apt upgrade && \
    apt install -y git

# set the working directory in the container
WORKDIR /opt/ffmwr

## UNCOMMENT IF USING RUBY SCRIPT FOR CBS AUTHENTICATION!
## update package index list and install ruby
#RUN apt install -y ruby-full
## install httparty gem for ruby
#RUN gem install httparty

# set python environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# copy the Python dependencies file to the working directory
COPY ../requirements.txt .

# install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

## copy the project root contents to the working directory
COPY .. .

RUN chmod +x ./docker/docker-entrypoint.sh

ENTRYPOINT ["./docker/docker-entrypoint.sh"]

# command to run on container start
CMD tail -f /dev/null
