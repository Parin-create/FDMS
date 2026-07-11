# syntax=docker/dockerfile:1
# Multi-stage build: compile the SPA, then serve static assets via nginx.

FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies using the lockfile-aware install for reproducibility.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# --- Runtime image -----------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
