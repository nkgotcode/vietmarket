FROM node:22-alpine
WORKDIR /app
COPY deploy/history-api/package.json deploy/history-api/package-lock.json ./
RUN npm ci --omit=dev
COPY deploy/history-api/server.mjs ./server.mjs
ENV PORT=8787
CMD ["node","server.mjs"]
