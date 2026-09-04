try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except (ImportError, Exception):
    celery_app = None
    __all__ = ()
