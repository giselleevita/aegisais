FROM node:20-alpine AS build
WORKDIR /workspace

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json package-lock.json turbo.json ./
COPY apps/web/package.json apps/web/package.json

RUN npm ci

COPY apps/web ./apps/web
RUN npm run build -w @aegisais/web

FROM nginx:1.31-alpine AS runtime
RUN apk upgrade --no-cache
COPY apps/web/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/web/dist /usr/share/nginx/html

EXPOSE 8080
