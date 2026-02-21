FROM archlinux:latest

WORKDIR /usr/src/app

RUN pacman -Syu --noconfirm \
    && pacman -S --noconfirm libsndfile libarchive ffmpeg python3 python-pip which git \
    && rm -rf /var/cache/pacman/pkg/*

COPY ./bin/archlinux/* /usr/local/bin
COPY requirements.txt ./

# Activate the virtual environment and install dependencies
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 6400/tcp
VOLUME /data

CMD ["bash", "start.sh"]