import json
import logging
import sys


LOGGER = logging.getLogger("spica_advisor")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        event = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        if hasattr(record, "payload"):
            event["payload"] = record.payload
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(asctime)s %(levelname)s %(message)s")

    def format(self, record):
        text = super().format(record)
        if hasattr(record, "payload"):
            text += "\n" + json.dumps(record.payload, indent=2, default=str)
        return text


def configure_logging(debug, log_file, log_format):
    handler = (
        logging.FileHandler(log_file, encoding="utf-8")
        if log_file
        else logging.StreamHandler(sys.stdout)
    )
    handler.setFormatter(
        JsonFormatter()
        if log_format == "json"
        else TextFormatter()
    )
    LOGGER.handlers.clear()
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if debug else logging.INFO)
    LOGGER.propagate = False
