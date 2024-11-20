import functools
import pika
import ssl
import threading
import random
from logger import LOGGER
from pika.exchange_type import ExchangeType
import seal
import pickle
import base64


class Device(threading.Thread):
    PUBLISH_INTERVAL = 30
    CONNECTION_ATTEMPTS = 3
    HEARTBEAT = 3600
    HOST = "rabbit-fog.iot-he.com"
    PORT = 5671
    VIRTUAL_HOST = "/"
    EXCHANGE = "rabbit-fog"
    EXCHANGE_TYPE = ExchangeType.topic

    def __init__(self, ca_cert, device_cert, device_key,
                 device_id, device_sn, seal_pub_key, seal_params, routing_key):

        super().__init__()
        self._connection = None
        self._channel = None

        self._deliveries = None
        self._acked = None
        self._nacked = None
        self._message_number = None

        self._stopping = False
        self._queue = None

        self._device_id = device_id
        self._device_sn = device_sn

        self._ca_cert = ca_cert
        self._device_cert = device_cert
        self._device_key = device_key
        self._routing_key = routing_key

        self._seal_params = seal.EncryptionParameters(seal.scheme_type.bfv)
        self._seal_params.load(seal_params)
        self._seal_context = seal.SEALContext(self._seal_params)

        self._seal_pub_key = seal.PublicKey()
        self._seal_pub_key.load(self._seal_context, seal_pub_key)

    def connect(self):
        LOGGER.info('Connecting to %s', self.HOST)

        ssl_context = self.setup_ssl_context()

        credentials = pika.PlainCredentials('rabbit', 'rabbit')

        ssl_options = pika.SSLOptions(ssl_context, self.HOST)

        conn_params = pika.ConnectionParameters(host=self.HOST, port=self.PORT, virtual_host=self.VIRTUAL_HOST,
                                                ssl_options=ssl_options, credentials=credentials,
                                                connection_attempts=self.CONNECTION_ATTEMPTS,
                                                heartbeat=self.HEARTBEAT)
        return pika.SelectConnection(
            parameters=conn_params,
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def setup_ssl_context(self):
        context = ssl.create_default_context(cafile=self._ca_cert)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(self._device_cert, self._device_key)

        return context

    def on_connection_open(self, _unused_connection):
        LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        LOGGER.error('Connection open failed, reopening in 5 seconds: %s', err)
        self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reopening in 5 seconds: %s',
                           reason)
            self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def open_channel(self):
        LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        LOGGER.warning('Channel %i was closed: %s', channel, reason)
        self._channel = None
        if not self._stopping:
            self._connection.close()

    def setup_exchange(self, exchange_name):
        LOGGER.info('Declaring exchange %s', exchange_name)
        # Note: using functools.partial is not required, it is demonstrating
        # how arbitrary data can be passed to the callback when it is called
        cb = functools.partial(self.on_exchange_declareok,
                               userdata=exchange_name)
        self._channel.exchange_declare(exchange=exchange_name,
                                       exchange_type=self.EXCHANGE_TYPE,
                                       callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        LOGGER.info('Exchange declared: %s', userdata)
        self.start_publishing()

    def start_publishing(self):
        LOGGER.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        LOGGER.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        ack_multiple = method_frame.method.multiple
        delivery_tag = method_frame.method.delivery_tag

        LOGGER.info('Received %s for delivery tag: %i (multiple: %s)',
                    confirmation_type, delivery_tag, ack_multiple)

        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1

        del self._deliveries[delivery_tag]

        if ack_multiple:
            for tmp_tag in list(self._deliveries.keys()):
                if tmp_tag <= delivery_tag:
                    self._acked += 1
                    del self._deliveries[tmp_tag]
        LOGGER.info(
            'Published %i messages, %i have yet to be confirmed, '
            '%i were acked and %i were nacked', self._message_number,
            len(self._deliveries), self._acked, self._nacked)

    def schedule_next_message(self):
        LOGGER.info('Scheduling next message for %0.1f seconds',
                    self.PUBLISH_INTERVAL)
        self._connection.ioloop.call_later(self.PUBLISH_INTERVAL,
                                           self.publish_message)

    def publish_message(self):
        if self._channel is None or not self._channel.is_open:
            return

        hdrs = {"device_id": self._device_id, "device_sn": self._device_sn}
        properties = pika.BasicProperties(app_id=self._device_id,
                                          content_type='text/plain',
                                          headers=hdrs)

        message = random.randint(1, 100)
        encrypted_msg = self.encrypt_message(message)
        pickled_msg = pickle.dumps(encrypted_msg)
        b64_pickled_msg = base64.b64encode(pickled_msg).decode('utf-8')

        self._channel.basic_publish(exchange=self.EXCHANGE, routing_key=self._routing_key,
                                    body=b64_pickled_msg,
                                    properties=properties)
        self._message_number += 1
        self._deliveries[self._message_number] = True
        LOGGER.info('### Published message # %i from %s: %s',
                    self._message_number, self._device_id, message)
        self.schedule_next_message()

    def encrypt_message(self, message):
        encryptor = seal.Encryptor(self._seal_context, self._seal_pub_key)
        plain_msg = seal.Plaintext(hex(message)[2:])
        encrypted_msg = encryptor.encrypt(plain_msg)

        return encrypted_msg.to_string()

    def run(self):
        while not self._stopping:
            self._connection = None
            self._deliveries = {}
            self._acked = 0
            self._nacked = 0
            self._message_number = 0

            try:
                self._connection = self.connect()
                self._connection.ioloop.start()
            except KeyboardInterrupt:
                self.stop()
                if (self._connection is not None and
                        not self._connection.is_closed):
                    self._connection.ioloop.start()

        LOGGER.info('Stopped')

    def stop(self):
        LOGGER.info('Stopping')
        self._stopping = True
        self.close_channel()
        self.close_connection()

    def close_channel(self):
        if self._channel is not None:
            LOGGER.info('Closing the channel')
            self._channel.close()

    def close_connection(self):
        if self._connection is not None:
            LOGGER.info('Closing connection')
            self._connection.close()
