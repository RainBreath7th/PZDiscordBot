#!/bin/sh
set -eu

CONFIG_DIR="${CONFIG_DIR:-/app/config}"
DEFAULTS_DIR="/app/config.defaults"

# If we are not inside the Docker image (local `python -m bot`), skip seeding.
if [ ! -d "$DEFAULTS_DIR" ]; then
  exec "$@"
fi

mkdir -p "$CONFIG_DIR" "$CONFIG_DIR/locales"

seed() {
  src="$1"
  dst="$2"
  if [ ! -f "$dst" ]; then
    echo "[entrypoint] seeding missing $(basename "$dst") from defaults" >&2
    cp "$src" "$dst"
  fi
}

for name in permissions.yaml i18n.yaml limits.yaml; do
  seed "$DEFAULTS_DIR/$name" "$CONFIG_DIR/$name"
done

for loc in zh en jp; do
  seed "$DEFAULTS_DIR/locales/$loc.yaml" "$CONFIG_DIR/locales/$loc.yaml"
done

exec "$@"
