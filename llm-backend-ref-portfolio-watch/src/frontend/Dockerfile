# Frontend Container — Nginx phục vụ SPA & reverse proxy API
FROM nginx:alpine

# Copy toàn bộ mã nguồn frontend vào thư mục phục vụ web của Nginx
COPY . /usr/share/nginx/html

# Copy file cấu hình Nginx reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
