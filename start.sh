#! /bin/bash
if [ -z "$(ls -A /data)" ]; then
    cp -R data/* /data
    cp config.ini.sample /data/config.ini
fi
python3 retrobbs.py -b /data/