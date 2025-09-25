#!/bin/sh
set -e

cd /app/esa-chat-ui

# If node_modules is missing or empty (because of bind mount), hydrate it from the image stash
if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  echo "Hydrating node_modules from image stash..."
  cp -a /opt/node_modules ./node_modules
fi

exec "$@"
