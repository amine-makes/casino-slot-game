# Frontend Dockerfile
FROM nginx:alpine

# Copy site
COPY frontend/ /usr/share/nginx/html/

# Use our nginx.conf
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
