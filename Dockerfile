FROM python:3

WORKDIR /usr/src/app

RUN apt-get update \
    &&  apt-get install -y --no-install-recommends libsndfile1-dev libgl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 6400/tcp
CMD ["python", "retrobbs.py"]
