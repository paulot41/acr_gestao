import contextvars
import json
import logging
from datetime import datetime, timezone

_REQUEST_ID_CTX = contextvars.ContextVar("request_id", default="-")


def set_request_id(request_id: str):
    return _REQUEST_ID_CTX.set(request_id)


def reset_request_id(token) -> None:
    _REQUEST_ID_CTX.reset(token)


def get_request_id() -> str:
    return _REQUEST_ID_CTX.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process": record.process,
            "thread": record.thread,
            "module": record.module,
            "line": record.lineno,
        }

        request_id = getattr(record, "request_id", "-")
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)
