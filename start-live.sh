#!/usr/bin/env bash
# Starts server + quick tunnel, writes tunnel URL into live_url.txt, rebuilds & pushes Pages so the button points at it.
cd "$(dirname "$0")"
pkill -f yt-dashboard/server.py; pkill -f "cloudflared tunnel --url http://127.0.0.1:8787"; sleep 1
nohup python3 "$PWD/server.py" > server.log 2>&1 &
nohup /home/box/bin/cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8787 > tunnel.log 2>&1 &
for i in $(seq 30); do U=$(rg -a -o 'https://[a-z0-9-]+\.trycloudflare\.com' -m1 tunnel.log) && [ -n "$U" ] && break; sleep 2; done
echo "$U" > live_url.txt; echo "tunnel: $U"; ./refresh.sh
