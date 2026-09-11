import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure one stdout log format for the whole catalog service."""
    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | %(levelname)s | catalog-service | "
            "%(name)s | %(message)s"
        ),
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
