#!/bin/bash
# Simple health-check script
URL=${1:-"http://localhost:8080/health/"}

if curl -fsS "$URL" > /dev/null; then
  echo "$(date): serviço saudável"
else
  echo "$(date): falha no health-check"
  exit 1
fi
