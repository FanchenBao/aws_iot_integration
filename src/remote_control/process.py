# coding: utf-8

import logging
from src.clients.remote import Remote
from time import sleep

# set up logger
logger = logging.getLogger(__name__)


def remote_control(term_event) -> None:
    """The function to run remote control in a child process.

    :param term_event: Termination event to determine when the child process
        can be terminated.
    :type term_event: Event
    """
    Remote()
    while not term_event.is_set():
        sleep(1)
    logger.info('Remote control terminated')
