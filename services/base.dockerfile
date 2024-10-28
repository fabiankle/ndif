FROM ubuntu:22.04

# Install base utilities
RUN apt-get update \
    && apt-get install -y build-essential \
    && apt-get install -y wget \
    && apt-get install -y python3-distutils \
    && apt-get install -y python3-pip \
    && apt-get install -y git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# REPLACED REQUIREMENTS ##################################################################

COPY requirements.txt .
RUN pip install uv
RUN uv pip install -r requirements.txt --system


###########################################################################