# ============================================================
# GD CRM — Frontend (React + Vite → nginx)
# ============================================================

# --- Etapa 1: build ---
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci --silent
COPY . .

# VITE_API_URL é passada como build-arg para apontar ao backend correto.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# --- Etapa 2: produção (nginx) ---
FROM nginx:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Saúde do container
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
