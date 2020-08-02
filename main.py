# coding: utf-8

import logging
from src.services.upload import Upload
from time import sleep

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)


def main():
    """Main entry to the program."""
    upload = Upload()
    while True:
        upload.upload_msg('foo')
        sleep(1)


if __name__ == '__main__':
    main()
