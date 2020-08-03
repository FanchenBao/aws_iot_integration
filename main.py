# coding: utf-8

import json
import logging
from config import settings
from multiprocessing import Queue
from src.child_processes.child_processes import ChildProcesses
from src.errors.network_connection_error import NoInternetError
from src.logger.logger_config import queue_logger_config
from src.logger.ouput import output_process
from src.services.upload import Upload
from src.vehicle_detector.detect_vehicle import detect_vehicle
from time import time
from typing import Dict

# setup root logger for main
logger = logging.getLogger()


def run_session(upload: Upload, data_q: Queue) -> None:
    """Run a sensor session.

    This session creates a payload, and uploads it to AWS IoT. The duration of
    the session is determined by the total number of times data are uploaded,
    which is a param specified in the settings.

    :param upload: An Upload service instance to upload data to AWS IoT.
    :type upload: Upload
    :param data_q: The queue that connects the sensor process to the main
        process.
    :type data_q: Queue
    """
    iteration: int = 0
    while iteration < settings.total_iterations:
        payload: Dict = {
            'timestamp': int(time() * 1000),  # epoch milisecond
            'cur_vehicle_count': data_q.get(),  # block get
        }
        logger.info(
            f'Publishing data to topic {settings.upload_topic}...',
        )
        try:
            upload.upload_msg(json.dumps(payload))
        except (NoInternetError, Exception):
            logger.exception('Publish data failed.')
        iteration += 1


def main() -> None:
    """Main entry to the program."""
    cp: ChildProcesses = ChildProcesses()
    data_q: Queue = Queue()
    logger_q: Queue = Queue()

    # For output loggers
    cp.create_and_start('output_logger', output_process, logger_q)
    # For passing log from everywhere in the program to the logging output.
    queue_logger_config(logger, logger_q)

    cp.create_and_start('detect_vehicle', detect_vehicle, data_q)
    run_session(Upload(), data_q)
    logger.info('Program ended')

    cp.terminate('detect_vehicle')
    cp.terminate('output_logger')


if __name__ == '__main__':
    main()
