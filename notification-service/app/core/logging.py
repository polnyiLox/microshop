import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure stdout logging for notification-service."""
    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | %(levelname)s | notification-service | "
            "%(name)s | %(message)s"
        ),
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
