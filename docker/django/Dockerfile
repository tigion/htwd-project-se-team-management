# Set base image
#FROM python:3-slim-bookworm
#FROM python:3.11-slim-bookworm
FROM python:3.11-bookworm

# Update package index and install needed ones
# - needed for `pip install python-ldap`
# v1: python:3.11-bookworm:
RUN apt-get update && apt-get --yes install libldap2-dev libsasl2-dev libssl-dev
# v2: python:3.11-slim-bookworm:
#RUN apt-get update && apt-get --yes install libldap2-dev libsasl2-dev libssl-dev libzbar-dev

# Set work directory
WORKDIR /usr/src/app

# Set environment variables
# Prevent Python from writing pyc to Docker containers
ENV PYTHONDONTWRITEBYTECODE 1
# Empty Python buffer
ENV PYTHONUNBUFFERED 1

# Upgrade the Python pip version
RUN pip install --upgrade pip

# Install needed Python packages
COPY ./src/backend/requirements.txt .
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy all files in our project
COPY ./src/backend/ .
