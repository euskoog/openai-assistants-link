import logging
import colorlog

# Create a color formatter
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)s:  %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
    secondary_log_colors={},
    style="%",
)  # Create a console handler and set the formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)


def setup_logging_config():
    """
    Function that returns basic config for logging
    """
    return logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        handlers=[console_handler],
        force=True,
    )
