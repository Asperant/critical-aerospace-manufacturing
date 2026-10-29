FROM node:24.15.0-alpine AS build
WORKDIR /app
COPY services/command-center-web/package.json services/command-center-web/package-lock.json ./
RUN npm ci
COPY services/operations-bff/contracts /operations-bff/contracts
COPY services/command-center-web ./
RUN npm run build

FROM nginx:1.29.1-alpine
COPY services/command-center-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
