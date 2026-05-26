# app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY ./main.py ./
COPY ./meteoswiss_utils.py ./
COPY ./requirements.txt ./
COPY ./pollen_levels.csv ./

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python"]
CMD ["main.py"]