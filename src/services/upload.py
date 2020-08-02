# coding: utf-8

import logging
from config import settings
from src.aws.aws import AWSIoTMQTTClientWrapper

# set up logger
logger = logging.getLogger(__name__)


class Upload(AWSIoTMQTTClientWrapper):
    """A class to handle data upload to a specified AWS IoT MQTT topic.

    This class inherits from the parent class AWSIoTMQTTClientWrapper.
    """

    def __init__(self):
        """Constructor for UploadService."""
        super().__init__('UPLOAD')
        self._topic: str = settings.upload_topic

    def upload_msg(self, msg: str, custom_topic: str = '') -> None:
        """Send msg to a specified MQTT topic.

        :param msg: The msg to be sent to the MQTT topic. Must be a JSONified
            string.
        :param custom_topic: The MQTT topic to publish. Default to empty
            string, which means self._topic will be used.
        """
        topic: str = self._topic if custom_topic == '' else custom_topic
        self.send(topic, msg)
