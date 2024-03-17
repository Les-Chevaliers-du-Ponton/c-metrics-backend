# python manage.py makemigrations
# python manage.py migrate

# docker build -t cmetrics-backend .

# docker run -p 8000:8000 --name cmetrics-api cmetrics-backend
# add -it for debugging

# docker stop cmetrics-api
docker start cmetrics-api


# daphne -p 8001 cmetrics.backend.asgi:application
# FOR PROD