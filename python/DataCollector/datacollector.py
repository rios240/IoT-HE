import functools
import time
import pika
from logger import LOGGER
import ssl
from pika.exchange_type import ExchangeType
import seal
import pickle
import base64


class DataCollector(object):
    EXCHANGE = 'rabbit-fog'
    EXCHANGE_TYPE = ExchangeType.topic
    QUEUE = "device-processed"
    HOST = "rabbit-fog.iot-he.com"
    PORT = 5671
    VIRTUAL_HOST = "/"

    def __init__(self, ca_cert, node_cert, node_key, seal_priv_key, seal_params, routing_keys):
        self.should_reconnect = False
        self.was_consuming = False

        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None

        self._ca_cert = ca_cert
        self._node_cert = node_cert
        self._node_key = node_key
        self._routing_keys = routing_keys

        self._consuming = False
        self._prefetch_count = 1

        self._seal_params = seal.EncryptionParameters(seal.scheme_type.bfv)
        self._seal_params.load(seal_params)
        self._seal_context = seal.SEALContext(self._seal_params)

        self._seal_secret_key = seal.SecretKey()
        self._seal_secret_key.load(self._seal_context, seal_priv_key)

    def connect(self):
        LOGGER.info('Connecting to %s', self.HOST)

        ssl_context = self.setup_ssl_context()

        credentials = pika.PlainCredentials('rabbit', 'rabbit')

        ssl_options = pika.SSLOptions(ssl_context, self.HOST)

        conn_params = pika.ConnectionParameters(host=self.HOST, port=self.PORT, virtual_host=self.VIRTUAL_HOST,
                                                credentials=credentials, ssl_options=ssl_options)

        return pika.SelectConnection(
            parameters=conn_params,
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def setup_ssl_context(self):
        context = ssl.create_default_context(cafile=self._ca_cert)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(self._node_cert, self._node_key)

        return context

    def close_connection(self):
        self._consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            LOGGER.info('Connection is closing or already closed')
        else:
            LOGGER.info('Closing connection')
            self._connection.close()

    def on_connection_open(self, _unused_connection):
        LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        LOGGER.error('Connection open failed: %s', err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reconnect necessary: %s', reason)
            self.reconnect()

    def reconnect(self):
        self.should_reconnect = True
        self.stop()

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
        self.close_connection()

    def setup_exchange(self, exchange_name):
        LOGGER.info('Declaring exchange: %s', exchange_name)
        cb = functools.partial(
            self.on_exchange_declareok, userdata=exchange_name)
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=self.EXCHANGE_TYPE,
            callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        LOGGER.info('Exchange declared: %s', userdata)
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        LOGGER.info('Declaring queue %s', queue_name)
        cb = functools.partial(self.on_queue_declareok, userdata=queue_name)
        self._channel.queue_declare(queue=queue_name, callback=cb)

    def on_queue_declareok(self, _unused_frame, userdata):
        queue_name = userdata
        LOGGER.info('Binding %s to %s with %s', self.EXCHANGE, queue_name,
                    self._routing_keys)

        cb = functools.partial(self.on_bindok, userdata=queue_name)
        for key in self._routing_keys:
            self._channel.queue_bind(
                queue_name,
                self.EXCHANGE,
                routing_key=key,
                callback=cb)

    def on_bindok(self, _unused_frame, userdata):
        LOGGER.info('Queue bound: %s', userdata)
        self.set_qos()

    def set_qos(self):
        self._channel.basic_qos(
            prefetch_count=self._prefetch_count, callback=self.on_basic_qos_ok)

    def on_basic_qos_ok(self, _unused_frame):
        LOGGER.info('QOS set to: %d', self._prefetch_count)
        self.start_consuming()

    def start_consuming(self):
        LOGGER.info('Issuing Node related RPC commands')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            self.QUEUE, self.on_message)
        self.was_consuming = True
        self._consuming = True

    def add_on_cancel_callback(self):
        LOGGER.info('Adding Node cancellation callback')
        self._channel.add_on_cancel_callback(self.on_node_cancelled)

    def on_node_cancelled(self, method_frame):
        LOGGER.info('Node was cancelled remotely, shutting down: %r',
                    method_frame)
        self._channel.close()

    def on_message(self, _unused_channel, basic_deliver, properties, body):

        pickled_msg = base64.b64decode(body)
        unpickled_msg = pickle.loads(pickled_msg)

        cipher_msg = self._seal_context.from_cipher_str(unpickled_msg)

        result = self.decrypt_message(cipher_msg)

        LOGGER.info('### Received message # %s from %s: %d',
                    basic_deliver.delivery_tag, properties.app_id, int(result, 16))
        self.acknowledge_message(basic_deliver.delivery_tag)

    def decrypt_message(self, cipher_msg):
        decryptor = seal.Decryptor(self._seal_context, self._seal_secret_key)

        decrypted_result = decryptor.decrypt(cipher_msg)

        return decrypted_result.to_string()

    def acknowledge_message(self, delivery_tag):
        LOGGER.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        if self._channel:
            LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            cb = functools.partial(
                self.on_cancelok, userdata=self._consumer_tag)
            self._channel.basic_cancel(self._consumer_tag, cb)

    def on_cancelok(self, _unused_frame, userdata):
        self._consuming = False
        LOGGER.info(
            'RabbitMQ acknowledged the cancellation of the node: %s',
            userdata)
        self.close_channel()

    def close_channel(self):
        LOGGER.info('Closing the channel')
        self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        if not self._closing:
            self._closing = True
            LOGGER.info('Stopping')
            if self._consuming:
                self.stop_consuming()
                self._connection.ioloop.start()
            else:
                self._connection.ioloop.stop()
            LOGGER.info('Stopped')


class ReconnectingDataCollector(object):
    def __init__(self, ca_cert, node_cert, node_key, seal_priv_key, seal_params, routing_keys):
        super().__init__()
        self._reconnect_delay = 0
        self._ca_cert = ca_cert
        self._node_cert = node_cert
        self._node_key = node_key
        self._seal_priv_key = seal_priv_key
        self._seal_params = seal_params
        self._routing_keys = routing_keys
        self._node = DataCollector(ca_cert=self._ca_cert, node_cert=self._node_cert, node_key=self._node_key,
                                   seal_params=self._seal_params, seal_priv_key=self._seal_priv_key,
                                   routing_keys=self._routing_keys)

    def run(self):
        while True:
            try:
                self._node.run()
            except KeyboardInterrupt:
                self._node.stop()
                break
            self._maybe_reconnect()

    def _maybe_reconnect(self):
        if self._node.should_reconnect:
            self._node.stop()
            reconnect_delay = self._get_reconnect_delay()
            LOGGER.info('Reconnecting after %d seconds', reconnect_delay)
            time.sleep(reconnect_delay)
            self._node = DataCollector(ca_cert=self._ca_cert, node_cert=self._node_cert, node_key=self._node_key,
                                       seal_params=self._seal_params, seal_priv_key=self._seal_priv_key,
                                       routing_keys=self._routing_keys)

    def _get_reconnect_delay(self):
        if self._node.was_consuming:
            self._reconnect_delay = 0
        else:
            self._reconnect_delay += 1
        if self._reconnect_delay > 30:
            self._reconnect_delay = 30
        return self._reconnect_delay
