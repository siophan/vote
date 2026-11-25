#!/usr/bin/env bash
# Put the reverse proxy from deploy/nginx-vote.jh8.ai.conf into the BT panel's site config and
# reload nginx. Run on the server after deploy.sh has synced deploy/:
#   ssh ubuntu@18.162.184.136 sudo bash /www/wwwroot/vote/app/deploy/patch-nginx.sh
# First run: backs up the panel's file, removes its two static-file regex blocks and inserts the
# block before access_log. Later runs replace the block between the marker lines. Safe to re-run.
set -euo pipefail
CONF=/www/server/panel/vhost/nginx/html_vote.jh8.ai.conf
SNIPPET=$(dirname "$0")/nginx-vote.jh8.ai.conf
NGINX=/www/server/nginx/sbin/nginx

mkdir -p /root/vote-nginx-backup
[ -f /root/vote-nginx-backup/html_vote.jh8.ai.conf.orig ] || cp "$CONF" /root/vote-nginx-backup/html_vote.jh8.ai.conf.orig
cp "$CONF" /root/vote-nginx-backup/html_vote.jh8.ai.conf.prev

python3 - "$CONF" "$SNIPPET" <<'PY'
import re, sys
conf_path, snippet_path = sys.argv[1], sys.argv[2]
lines = open(snippet_path).read().splitlines()
start, end = lines.index("#VOTE-API-START"), lines.index("#VOTE-API-END")
block = "".join(("    " + l if l.strip() else "") + "\n" for l in lines[start:end + 1])
conf = open(conf_path).read()
marker = re.compile(r"^ *#VOTE-API-START\b.*?^ *#VOTE-API-END\b[^\n]*\n", re.S | re.M)
if marker.search(conf):
    conf = marker.sub(lambda m: block, conf, count=1)
else:
    for pat in (r"^    location ~ \.\*\\\.\(gif\|jpg\|jpeg\|png\|bmp\|swf\)\$\n    \{.*?\n    \}\n\n?",
                r"^    location ~ \.\*\\\.\(js\|css\)\?\$\n    \{.*?\n    \}\n\n?"):
        conf = re.sub(pat, "", conf, count=1, flags=re.S | re.M)
    anchor = "    access_log  /www/wwwlogs/vote.jh8.ai.log;"
    assert anchor in conf, "access_log anchor not found"
    conf = conf.replace(anchor, block + anchor, 1)
open(conf_path, "w").write(conf)
PY

if "$NGINX" -t >/dev/null 2>&1; then
  "$NGINX" -s reload
  echo "nginx reloaded"
else
  cp /root/vote-nginx-backup/html_vote.jh8.ai.conf.prev "$CONF"
  "$NGINX" -t || true
  echo "nginx -t failed; restored the previous config" >&2
  exit 1
fi
