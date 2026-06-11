FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime-deps
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev && npm cache clean --force

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN apk upgrade --no-cache && rm -rf /usr/local/lib/node_modules/npm
COPY --from=build /app/dist ./dist
COPY --from=runtime-deps /app/node_modules ./node_modules
COPY package.json ./
EXPOSE 8081
CMD ["node", "dist/server.js"]
