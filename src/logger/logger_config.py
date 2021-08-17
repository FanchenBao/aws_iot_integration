# coding: utf-8

import logging
from config import settings
from logging.handlers import QueueHandler, TimedRotatingFileHandler


def output_logger_config(output_logger) -> None:
    """Configure the logger that handles the logging output.

    This logger is the ONLY truth of logging output for the entire app. No
    matter where the logging activity happens, the log record will be passed
    through a queue to this logger for output.

    :param output_logger: The output logger.
    """
    # root handlers
    file_handler = TimedRotatingFileHandler(
        'app.log', when='midnight', backupCount=6,
    )
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    output_logger.addHandler(file_handler)
    output_logger.addHandler(console_handler)
    if settings.debug:
        output_logger.setLevel(logging.DEBUG)
    else:
        output_logger.setLevel(logging.INFO)


def queue_logger_config(queue_logger, queue) -> None:
    """Configure a logger that communicates to the output logger via a queue.

    This is the ONLY queue logger in the app, living in the main entry
    script. This logger accepts all the log record from anywhere in the app,
    including log record from the main and other processes, and then pass them
    to a queue. The log record will eventually end up in the output_logger for
    output.

    :param queue_logger: A logger for passing all log record to the
        output_logger via a queue.
    :param queue: Logger queue, passing LogRecord across processes.
    """
    queue_handler = QueueHandler(queue)
    queue_logger.addHandler(queue_handler)
    if settings.debug:
        queue_logger.setLevel(logging.DEBUG)
    else:
        queue_logger.setLevel(logging.INFO)
