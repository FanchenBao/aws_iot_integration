# coding: utf-8

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient

import logging
from config import ROOT_DIR, settings
from pathlib import Path
from src.errors.network_connection_error import NoInternetError

# set up logger
logger = logging.getLogger(__name__)


class AWSIoTMQTTClientWrapper(object):
    """A wrapper class to create a fully configured AWSIoTMQTTClient."""

    def __init__(self, client_type: str):
        """Constructor.

        Create and configure a MQTT client. But the client is NOT connected.

        :param client_type:     Only two types allowed: "UPLOAD" or "REMOTE"
        """
        if client_type not in {'UPLOAD', 'REMOTE'}:
            logger.error(f'Type: {client_type} is NOT supported')
            return  # wrong type, exit immediately
        self.thing_name = f'{settings.sensor_name}_{client_type}'

        self.myShadowClient = AWSIoTMQTTShadowClient(self.thing_name)
        self.myShadowClient.configureEndpoint(
            settings.endpoint,
            settings.port,
        )
        path: Path = ROOT_DIR.joinpath('credentials')
        self.myShadowClient.configureCredentials(
            path.joinpath(settings.root_ca),
            path.joinpath(settings.private_key[client_type]),
            path.joinpath(settings.cert_file[client_type]),
        )
        # AWSIoTMQTTClient connection configuration
        # for configureAutoReconnectBackoffTime
        self._base: int = 1
        self._max: int = 32
        self._stable: int = 20
        self.myShadowClient.configureAutoReconnectBackoffTime(
            self._base, self._max, self._stable,
        )
        # for configureConnectDisconnectTimeout
        self._conn_disconn: int = 10
        self.myShadowClient.configureConnectDisconnectTimeout(
            self._conn_disconn,
        )
        # for configureMQTTOperationTimeout
        self._mqtt_op = 5
        self.myShadowClient.configureMQTTOperationTimeout(self._mqtt_op)

        # set up callbacks for online and offline situation
        self.myShadowClient.onOnline = self._my_online_callback
        self.myShadowClient.onOffline = self._my_offline_callback

        # obtain an instance of regular MQTT client
        self.myAWSIoTMQTTClient = self.myShadowClient.getMQTTConnection()

        # flags
        self._online = False

    def connect(self) -> None:
        """Connect MQTT client."""
        if not self._online:
            logger.info(f'Connecting {self.thing_name} to MQTT client...')
            self.myShadowClient.connect()

    def disconnect(self) -> None:
        """Disconnect MQTT client."""
        if self._online:
            logger.info(f'Disconnecting {self.thing_name} from MQTT client.')
            self.myShadowClient.disconnect()

    def send(self, topic: str, msg: str) -> bool:
        """A wrapper function for MQTT publish.

        It provides its own error message and explicitly checks whether the
        client is online.

        :param topic: Topic to be published on.
        :type topic: str
        :param msg: Message to be published.
        :type msg: str
        :raises NoInternetError: Publish message failed due to No Internet
            connection.
        :return: True if message has been sent to paho, the underlying package
            that handles message transmission over MQTT, else False. Note that
            the return value does NOT suggest if the message has been actually
            published to the topic.
        :rtype: bool
        """
        self.connect()
        if self._online:
            return self.myAWSIoTMQTTClient.publish(topic, msg, 1)
        raise NoInternetError(
            f'Cannot publish to topic {topic} due to NO Internet connection.',
        )

    # Callbacks
    def _my_online_callback(self) -> None:
        logger.info(f'{self.thing_name} ONLINE.')
        self._online = True

    def _my_offline_callback(self) -> None:
        logger.info(f'{self.thing_name} OFFLINE.')
        self._online = False
