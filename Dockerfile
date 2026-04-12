FROM python:3.11

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl nodejs npm nginx \
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

COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh && nginx -t

EXPOSE 80 5001

CMD ["/start.sh"]
