FROM python:3.11

RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm nginx \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

COPY . .

RUN cd frontend \
  && npm install \
  && VITE_API_BASE_URL=/api npm run build \
  && mv dist /usr/share/nginx/html

RUN ls -la /usr/share/nginx/html/ && echo "Frontend build OK"

RUN printf '%s\n' \
  'server {' \
  '    listen 80 default_server;' \
  '    server_name _;' \
  '    root /usr/share/nginx/html;' \
  '    index index.html;' \
  '    location / {' \
  '        try_files $uri $uri/ /index.html;' \
  '    }' \
  '    location /api/ {' \
  '        proxy_pass http://localhost:5001;' \
  '        proxy_set_header Host $host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
  '        proxy_set_header X-Forwarded-Proto $scheme;' \
  '    }' \
  '}' > /etc/nginx/sites-available/default

RUN printf '#!/bin/bash\nexport FLASK_DEBUG=0\nnginx && cd /app/backend && uv run python run.py\n' > /start.sh && chmod +x /start.sh

EXPOSE 80 5001

CMD ["/start.sh"]
