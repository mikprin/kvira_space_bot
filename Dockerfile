FROM python:3.12-slim

LABEL name="Kvira space bot" \
      version="1.0" \
      maintainer="Mikhail Solovyanov <" \
      description="This is the Dockerfile for the Kvira space bot."

WORKDIR /

RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/* &&\
    apt-get clean
# Copy the requirements.txt file to the container before copying the rest of the code
COPY requirements.txt /requirements.txt

RUN pip3 install -r requirements.txt

COPY kvira_space_bot_src /kvira_space_bot_src

CMD ["python3", "-m" "kvira_space_bot_src"]