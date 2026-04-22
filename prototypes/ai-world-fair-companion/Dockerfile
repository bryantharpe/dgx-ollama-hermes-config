FROM node:20-alpine

WORKDIR /app

RUN mkdir -p src/frontend/vendor src/frontend/css src/frontend/images src/frontend/assets src/backend

COPY src/frontend/vendor/qrcode.min.js /app/src/frontend/vendor/
COPY src/frontend/css/style.css /app/src/frontend/css/
COPY src/frontend/js/*.js /app/src/frontend/js/
COPY src/frontend/images/ /app/src/frontend/images/
COPY src/frontend/assets/ /app/src/frontend/assets/
COPY index.html /app/
COPY src/backend/*.js /app/src/backend/

RUN chmod -R 755 /app

EXPOSE 8000

CMD ["node", "/app/src/backend/server.js"]
