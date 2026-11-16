#!/bin/sh
set -eu
cat > /tmp/s3.json <<JSON
{"identities": [{"name": "sadu-api",
  "credentials": [{"accessKey": "${S3_ACCESS_KEY_ID}", "secretKey": "${S3_SECRET_ACCESS_KEY}"}],
  "actions": ["Read", "Write", "List", "Tagging", "Admin"]}]}
JSON
exec weed server -dir=/data -s3 -s3.port=8333 -s3.config=/tmp/s3.json
