FROM node:22-alpine AS build

WORKDIR /app/src/fe

COPY src/fe/package.json src/fe/package-lock.json ./
RUN npm ci

COPY src/fe/ ./

# Allow overriding the API URL at build time (empty = same origin via nginx proxy)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Build the production bundle (output in dist/)
RUN npm run build

# --- Serve with a lightweight static server ---
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/src/fe/dist /usr/share/nginx/html

# SPA fallback: serve index.html for all routes (react-router)
COPY src/fe/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
