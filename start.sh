#!/bin/bash
export FLASK_DEBUG=0
nginx -t && nginx && sleep 2 && cd /app/backend && uv run python run.py