from __future__ import annotations

import inspect
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import orjson
import pandas as pd
import structlog
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

original_stdout = sys.stdout
original_stderr = sys.stderr


class MyTheme(Theme):
    """Custom theme."""

    def __init__(self, **kwargs: dict) -> None:
        styles: dict[str, str] = {
            "log.level.DEBUG": "bold blue",
            "log.level.INFO": "bold green",
            "log.level.WARNING": "bold yellow",
            "log.level.ERROR": "bold red",
            "log.level.CRITICAL": "bold magenta",
            "log.fileline": "blue underline",
        }
        kwargs.setdefault("styles", styles)
        super().__init__(**kwargs)


class StreamToLogger:
    """Redirect writes to a logger instance."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, log_level: int) -> None:
        self.logger = logger
        self.log_level = log_level

    def write(self, message: str) -> None:
        """Write method that logs messages."""
        message = message.strip()
        if message:
            self.logger.log(self.log_level, message)

    def flush(self) -> None:
        """Flush method for compatibility with sys.stdout."""


class CustomBoundLogger(structlog.stdlib.BoundLogger):
    """Custom logger class with additional method to handle dataframes."""

    def df(self, df: pd.DataFrame | np.matrix, **kwargs: dict) -> None:
        """Log a pandas DataFrame with a special format."""
        var_name = None
        frame = inspect.currentframe()
        try:
            outer_frame = frame.f_back
            local_vars = outer_frame.f_locals.items()
            for var, val in local_vars:
                if val is df:
                    var_name = var
                    break
        finally:
            del frame  # Avoid reference cycles

        event = f"Pandas DataFrame: {var_name}\n{df}" if var_name else f"Pandas DataFrame:\n{df}"

        self.info(event, **kwargs)

    def np(self, array: np.ndarray, **kwargs: dict) -> None:
        """Log a NumPy ndarray with a special format."""
        var_name = None
        frame = inspect.currentframe()
        try:
            outer_frame = frame.f_back
            local_vars = outer_frame.f_locals.items()
            for var, val in local_vars:
                if val is array:
                    var_name = var
                    break
        finally:
            del frame  # Avoid reference cycles

        event = f"NumPy Array: {var_name}\n{array}" if var_name else f"NumPy Array:\n{array}"

        self.info(event, **kwargs)

    def exception(
        self,
        event: str | None = None,
        error_hint: str | None = None,
        exit: bool = False,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """Extending the exception method to include an error_hint and exit flag."""
        if error_hint:
            kw["error_hint"] = error_hint
        if exit:
            kw["exit"] = exit
        if not event:
            event = "An exception occurred."
        # Check if an exception is currently being handled
        if "exc_info" not in kw or kw["exc_info"]:
            if sys.exc_info() == (None, None, None):
                kw["exc_info"] = False
            else:
                kw["exc_info"] = True
        # FIXME: This will throw an error if the event is None
        super().exception(event, *args, **kw)


class CustomRichHandler(RichHandler):
    """RichHandler that outputs error_hint after the traceback."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit the log message and exception, then deliver the error_hint as a warning."""
        super().emit(record)
        error_hint = getattr(record, "error_hint", None)
        if error_hint:
            console = self.console
            console.print(f"[bold yellow]Hint:[/bold yellow] {error_hint}")
        sys.exit() if getattr(record, "exit", False) else None


def orjson_dumps(obj: dict, **kwargs: dict) -> str:
    """Custom orjson.dumps wrapper that decodes bytes to string with indentation."""
    return orjson.dumps(obj, option=orjson.OPT_INDENT_2, **kwargs).decode("utf-8")


def configure_logging(
    level: str = "INFO",
    logdir: Path | None = None,
    log_types: list[str] | None = None,
    *,
    console: bool = True,
) -> CustomBoundLogger:
    """Configure logging with structlog and rich."""
    level = level.upper()
    log_types = log_types or []
    console_obj = Console(theme=MyTheme(), file=original_stdout)
    rich_handler = CustomRichHandler(
        console=console_obj,
        rich_tracebacks=True,
        show_level=True,
        show_path=False,
        show_time=False,
    )

    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            timestamper,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs,
        ],
        wrapper_class=CustomBoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []

    if console:
        root_logger.addHandler(rich_handler)

    if log_types:
        logdir = logdir or (Path.cwd() / ".logs")
        logdir.mkdir(parents=True, exist_ok=True)

        current_date = datetime.now(tz=datetime.now().astimezone().tzinfo).strftime("%Y-%m-%d")
        header_message = f"======= RUN DATE: {datetime.now(tz=datetime.now().astimezone().tzinfo).strftime('%Y-%m-%d %H:%M:%S')} =======\n"

        log_paths = {
            "dev": logdir / f"dev_log_{current_date}.log",
            "info": logdir / f"info_{current_date}.log",
            "errors": logdir / f"errors_{current_date}.log",
        }

        file_formatter = logging.Formatter(
            fmt="%(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        )

        if "dev" in log_types:
            dev_handler = logging.FileHandler(log_paths["dev"])
            dev_handler.setLevel(logging.DEBUG)
            dev_handler.setFormatter(file_formatter)
            root_logger.addHandler(dev_handler)
            _write_header(log_paths["dev"], header_message)

        if "info" in log_types:
            info_handler = logging.FileHandler(log_paths["info"])
            info_handler.setLevel(logging.INFO)
            info_handler.addFilter(lambda record: record.levelno == logging.INFO)
            info_handler.setFormatter(file_formatter)
            root_logger.addHandler(info_handler)
            _write_header(log_paths["info"], header_message)

        if "errors" in log_types:
            errors_handler = logging.FileHandler(log_paths["errors"])
            errors_handler.setLevel(logging.ERROR)
            errors_handler.setFormatter(file_formatter)
            root_logger.addHandler(errors_handler)
            _write_header(log_paths["errors"], header_message)

        if "json" in log_types:
            json_path = logdir / f"log_{current_date}.json"
            json_handler = logging.FileHandler(json_path)
            json_handler.setLevel(logging.DEBUG)
            json_formatter = logging.Formatter(fmt="%(message)s")
            json_handler.setFormatter(json_formatter)
            root_logger.addHandler(json_handler)

    sys.stdout = StreamToLogger(structlog.get_logger(), logging.INFO)

    return structlog.get_logger()


def _write_header(log_path: Path, header_message: str) -> None:
    """Write header message to log file."""
    if not log_path.exists() or log_path.stat().st_size == 0:
        with log_path.open("a") as file:
            file.write(header_message)
    else:
        with log_path.open("a") as file:
            file.write("\n\n" + header_message)


if __name__ == "__main__":
    log = configure_logging(
        level="INFO",
        log_types=["dev"],
    )

    # Overriding print as info:
    print("test")
    # logging a named df shows the name of the variable
    test_df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    log.df(test_df)
    # otherwise it's empty
    log.df(pd.DataFrame({"X": [7, 8, 9], "Y": [10, 11, 12]}))

    # same for numpy ndarrays:
    test_matrix = np.array([[1, 2, 3], [4, 5, 6]])
    log.np(test_matrix)
    log.np(np.array([[7, 8, 9], [10, 11, 12]]))

    log.info("This is an info message.")
    log.warning("Warning message.")

    # Deliberate ZeroDivisionError to test exception handling
    try:
        1 / 0  # noqa: B018
    except Exception:
        log.exception(
            # "A division by zero occurred.",
            error_hint="Did you forget to do...",
            exit=True,
        )
    log.warning("This message should not appear.")
