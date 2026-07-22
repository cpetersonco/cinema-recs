#!/bin/bash
set -e

PUID="${PUID:-99}"
PGID="${PGID:-100}"

if ! getent group "$PGID" >/dev/null 2>&1; then
    groupadd -g "$PGID" cinema_recs
fi
GROUP_NAME="$(getent group "$PGID" | cut -d: -f1)"

if ! getent passwd "$PUID" >/dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" -M -s /usr/sbin/nologin cinema_recs
fi
USER_NAME="$(getent passwd "$PUID" | cut -d: -f1)"

mkdir -p "${CINEMA_RECS_DATA_DIR:-/data}"
chown -R "$PUID:$PGID" "${CINEMA_RECS_DATA_DIR:-/data}"

exec gosu "$USER_NAME":"$GROUP_NAME" "$@"
