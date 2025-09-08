#!/bin/bash
set -e
if [ -z "$1" ]; then
  echo "No GOOGLE_SVC_JSON provided"
  exit 0
fi
echo "$1" | base64 --decode > /tmp/google_svc.json
chmod 600 /tmp/google_svc.json
echo "Google service account JSON written to /tmp/google_svc.json"
