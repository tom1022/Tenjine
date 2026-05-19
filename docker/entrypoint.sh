#!/bin/bash
set -e

if [ ! -f /app/config/config.yml ]; then
    echo "config.yml が見つかりません。Docker デフォルト設定をコピーします..."
    cp /app/config/config.docker.yml /app/config/config.yml
fi

exec "$@"
