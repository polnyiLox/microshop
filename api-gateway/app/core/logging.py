import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure stdout logging for API Gateway."""
    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | %(levelname)s | api-gateway | "
            "%(name)s | %(message)s"
        ),
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
