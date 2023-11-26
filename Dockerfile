FROM python:3.11-alpine

COPY ./dist/nido-0.0.1-py3-none-any.whl /opt/
RUN pip install --no-cache-dir /opt/nido-0.0.1-py3-none-any.whl
RUN apk add --no-cache uwsgi-python3 nginx supervisor

COPY <<EOF /etc/uwsgi/uwsgi.ini
[uwsgi]
plugins = python
module = nido_frontend:create_app()
master = true
processes = %k
uid = uwsgi
socket = /tmp/uwsgi.sock
chmod-socket = 777
vacuum = true
die-on-term = true
EOF

COPY <<EOF /etc/supervisor.d/supervisord.ini
[supervisord]
nodaemon=true

[program:uwsgi]
command = /usr/sbin/uwsgi --ini /etc/uwsgi/uwsgi.ini
stdout_logfile = /dev/stdout
stdout_logfile_maxbytes = 0
stderr_logfile = /dev/stderr
stderr_logfile_maxbytes = 0
startsecs = 0
autorestart = false

[program:nginx]
command = /usr/sbin/nginx
stdout_logfile = /dev/stdout
stdout_logfile_maxbytes = 0
stderr_logfile = /dev/stderr
stderr_logfile_maxbytes = 0
# Graceful stop, see http://nginx.org/en/docs/control.html
stopsignal = QUIT
startsecs = 0
autorestart = false
EOF

COPY <<EOF /etc/nginx/conf.d/no-daemon.conf
daemon off;
error_log stderr info;
EOF

COPY <<EOF /etc/nginx/http.d/default.conf
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    location / {
        uwsgi_pass      unix:///tmp/uwsgi.sock;
        include         uwsgi_params;
    }

    location /static {
        alias /usr/local/lib/python3.11/site-packages/nido_frontend/resources/static;
    }

}
EOF

COPY <<EOF /srv/nido.cfg
DATABASE_URL="sqlite:////srv/nido_db.sqlite3"
SECRET_KEY="mybigsecret"
EOF

ENV NIDO_CONFIG_FILE=/srv/nido.cfg
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

#COPY --from=flyio/litefs:0.5 /usr/local/bin/litefs /usr/local/bin/litefs

ENTRYPOINT ["supervisord", "-c", "/etc/supervisor.d/supervisord.ini"]
