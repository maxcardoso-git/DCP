FROM nginx:alpine

WORKDIR /usr/share/nginx/html/dcp

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY README.md README.md
COPY docs docs
COPY i18n i18n

EXPOSE 80
