#!/bin/bash
set -e
cd /opt/app

PW="$(grep '^API_KEY=' /opt/app/.env | cut -d= -f2-)"
if [ -z "$PW" ]; then
  echo "API_KEY missing in .env - nothing started"
  exit 1
fi

git pull
docker build -t sribhava .
docker rm -f sribhava dashboard 2>/dev/null || true
docker run -d --name sribhava --restart unless-stopped --env-file /opt/app/.env -p 8000:8000 -v /opt/sribhava-data/tickets.db:/app/tickets.db sribhava
docker run -d --name dashboard --restart unless-stopped -e DASHBOARD_PASSWORD="$PW" -e FIRST_FAST_TICKET=1 -p 8501:8501 -v /opt/sribhava-data/tickets.db:/app/tickets.db sribhava streamlit run sribhava_ui.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
echo DEPLOY_DONE