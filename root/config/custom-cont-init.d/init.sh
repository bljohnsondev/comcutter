#!/usr/bin/with-contenv bash

if [ ! -d "/data" ] || [ ! -d "/data/config" ] || [ ! -d "/data/logs" ]; then
  echo "Initialization: creating /data"

  mkdir -p /data/config
  mkdir -p /data/logs

  if [ ! -f "/data/config/comskip.ini" ]; then
    echo "Initialization: copying default comskip.ini"
    cp /defaults/comskip.ini /data/config/comskip.ini
  fi

  if [ ! -f "/data/config/config.yml" ]; then
    echo "Initialization: copying default config.yml"
    cp /defaults/config.yml /data/config/config.yml
  fi

  chown -R abc:abc /data
fi

