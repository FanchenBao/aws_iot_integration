# coding: utf-8

import logging
from multiprocessing import Queue
from queue import Empty
from src.logger.logger_config import output_logger_config

# set up root logger for the entire app
logger = logging.getLogger()


def output_process(queue: Queue, term_event) -> None:
    """Output log record from the queue according to the output_logger_config.

    :param queue: Logger queue, passing LogRecord across processes.
    :param term_event: An event to notify when the process shall terminate.
    """
    output_logger_config(logger)
    while not term_event.is_set():
        try:
            record = queue.get(timeout=1)
        except Empty:
            continue
        child_logger = logging.getLogger(record.name)  # get child logger
        # propagate logging to root logger since no child logger has set
        # up any handler.
        child_logger.handle(record)
    logger.info('Logging terminated.')
