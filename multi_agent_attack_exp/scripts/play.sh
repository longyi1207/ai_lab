#!/usr/bin/env bash
# Open a shell inside a fresh MiniLab-lite world as one operator account. No API key needed.
#   scripts/play.sh                 # as reg_exporter
#   scripts/play.sh plat_reviewer   # any account: eval_sched eval_triage eval_release reg_exporter
#                                   #   reg_dashboard reg_reporting rel_filer rel_recon rel_window
#                                   #   plat_author plat_reviewer plat_oncall ops_lead
# Standing processes run every 2 s, as they do during an experiment. Exiting the shell deletes the world.
set -euo pipefail
ACCOUNT="${1:-reg_exporter}"
NAME="minilab-play-$$"
docker run -d --rm --network none --hostname minilab --name "$NAME" minilab-lite:0.2 >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1' EXIT
docker exec -u root "$NAME" sh -c "echo '127.0.0.1 minilab' >> /etc/hosts"
docker exec -d -u labsvc "$NAME" /usr/local/bin/lab-ticker
echo "You are $ACCOUNT in a fresh MiniLab-lite world. Try: lab docs, lab whoami, lab registry models"
docker exec -it -u "$ACCOUNT" -w "/home/$ACCOUNT" "$NAME" bash -l
