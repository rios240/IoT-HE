FROM rabbitmq:4.0-management

COPY --chown=rabbitmq:rabbitmq --chmod=664 30-tls.conf /etc/rabbitmq/conf.d/
COPY --chown=rabbitmq:rabbitmq --chmod=600 rabbit_fog_keypair.pem /tmp/rabbitmq-ssl/
COPY --chown=rabbitmq:rabbitmq --chmod=664 rabbit_fog.pem iot_he.pem /tmp/rabbitmq-ssl/
