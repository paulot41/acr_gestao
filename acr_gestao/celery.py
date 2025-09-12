import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acr_gestao.settings")

app = Celery("acr_gestao")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
