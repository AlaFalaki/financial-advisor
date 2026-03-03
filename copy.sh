#!/bin/bash

ZIP_FILE="/tmp/financial-advisor.zip"
REMOTE_USER="ubuntu"
REMOTE_HOST="34.234.60.211"
REMOTE_DIR="~"
SSH_KEY="~/.ssh/financial-advisor.pem"

rm -f "$ZIP_FILE"

cd ~/financial-advisor && zip -r "$ZIP_FILE" .

scp -i "$SSH_KEY" "$ZIP_FILE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/financial-advisor.zip"