
import json
import logging
import sys

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any


request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": request_id_context.get(),
        }

        campos_reservados = set(
            logging.makeLogRecord({}).__dict__.keys()
        ) | {"message", "asctime", "event"}

        for chave, valor in record.__dict__.items():
            if chave not in campos_reservados and chave not in evento:
                if isinstance(valor, (str, int, float, bool)) or valor is None:
                    evento[chave] = valor

        if record.exc_info:
            evento["exception"] = self.formatException(record.exc_info)

        return json.dumps(evento, ensure_ascii=False)


def configurar_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.addHandler(handler)
    raiz.setLevel(logging.INFO)


def log_evento(
    logger: logging.Logger,
    nivel: int,
    evento: str,
    **campos: Any,
) -> None:
    logger.log(nivel, evento, extra={"event": evento, **campos})
