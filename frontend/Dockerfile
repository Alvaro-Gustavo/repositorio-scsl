# ============================================================
# Repositorio SCSL - frontend
# Etapa 1: compila Vue con Node. Etapa 2: sirve los archivos con Nginx.
# El resultado no necesita Internet para funcionar.
# ============================================================
FROM node:22-alpine AS compilacion
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# simulado = datos de demostracion; real = usa el backend (/api)
ARG VITE_API_MODO=simulado
ENV VITE_API_MODO=$VITE_API_MODO VITE_API_URL=/api
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=compilacion /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1/salud || exit 1
