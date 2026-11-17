FROM node:22-alpine AS builder
WORKDIR /web
COPY web/package.json web/package-lock.json /web/
RUN npm ci --no-audit --no-fund
COPY web/ /web/
RUN npm run build

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /web/dist/ /usr/share/nginx/html/
EXPOSE 80
