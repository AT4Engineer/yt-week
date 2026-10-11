#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 build.py "$@"
git add index.html build.py refresh.sh server.py start-live.sh live_url.txt .gitignore 2>/dev/null; git add index.html build.py refresh.sh server.py start-live.sh .gitignore; [ -f live_url.txt ] && git add live_url.txt
git -c user.name=AT4Engineer -c user.email=AT4Engineer@users.noreply.github.com commit -qm "refresh $(date +%F)" || true
git push -q
