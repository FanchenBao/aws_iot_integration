# coding: utf-8

import json
import logging
from config import settings
from multiprocessing import Event, Process, Queue
from src.errors.network_connection_error import NoInternetError
from src.services.upload import Upload
from src.vehicle_detector.detect_vehicle import detect_vehicle
from time import time
from typing import Dict

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)


def main() -> None:
    """Main entry to the program."""
    upload: Upload = Upload()  # data upload to AWS IoT
    data_q: Queue[int] = Queue()
    term_event = Event()
    detector_process: Process = Process(
        target=detect_vehicle,
        args=(data_q, term_event),
    )
    detector_process.start()
    iteration: int = 0
    while iteration < settings.total_iterations:
        payload: Dict = {
            'timestamp': int(time() * 1000),  # epoch milisecond
            'cur_vehicle_count': data_q.get(),  # block get
        }
        logger.info(
            f'Publishing data {payload} to topic {settings.upload_topic}...',
        )
        try:
            upload.upload_msg(json.dumps(payload))
        except (NoInternetError, Exception):
            logger.exception('Publish data failed.')
        iteration += 1
    term_event.set()  # gracefully terminate detector_process
    detector_process.join()
    logger.info('Program ended')


if __name__ == '__main__':
    main()
