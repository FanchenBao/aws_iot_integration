# coding: utf-8

from random import randint

from multiprocessing import Queue
from time import sleep


def detect_vehicle(data_q: Queue, term_event) -> None:
    """A function mocking the feature of a vehicle detector.

    This function simulates a vehicle-detecting process that will be running
    in a separate process and can push the current number of vehicles it has
    detected to a data queue. The data queue is connected to the main
    process, where the data will be uploaded to AWS IoT.

    :param data_q: A queue connecting the process running detect_vehicle to the
        main process to pass data.
    :type data_q: Queue
    :param term_event: An event to determine whether this process shall be
        terminated.
    :type term_event: multiprocessing.Event
    """
    num_vehicles: int = 0
    while not term_event.is_set():
        num_vehicles += 1
        data_q.put(num_vehicles)
        sleep(randint(1, 5))
