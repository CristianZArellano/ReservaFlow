# restart-python.sh - Para cambios en código
docker compose restart web celery celery-beat

# migrate.sh - Para cambios en modelos
docker compose exec web uv run python manage.py makemigrations
docker compose exec web uv run python manage.py migrate
