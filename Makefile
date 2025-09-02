.PHONY: dev migrate super collect up logs shell test check
dev: ; python manage.py runserver
migrate: ; python manage.py makemigrations && python manage.py migrate
super: ; python manage.py createsuperuser
collect: ; python manage.py collectstatic --noinput
up: ; docker compose up -d --build
logs: ; docker compose logs -f --tail=120
shell: ; python manage.py shell
test: ; pytest -q || true
check: ; python manage.py check --fail-level WARNING && python -m pip check
