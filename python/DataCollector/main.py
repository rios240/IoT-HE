import datacollector

CA_CERTIFICATE = "trust_store/iot_he.crt"

DATA_COLLECTOR_CERTIFICATE = "key_store/data_collector.crt"
DATA_COLLECTOR_KEY = "key_store/data_collector_keypair.pem"

SEAL_PRIV_KEY = "key_store/seal_secret_key.bin"
SEAL_PARAMS = "trust_store/seal_params.bin"


def main():

    data_collector_routing_keys = ["*.processed"]
    data_collector = datacollector.ReconnectingDataCollector(ca_cert=CA_CERTIFICATE,
                                                             node_cert=DATA_COLLECTOR_CERTIFICATE,
                                                             node_key=DATA_COLLECTOR_KEY,
                                                             seal_params=SEAL_PARAMS,
                                                             seal_priv_key=SEAL_PRIV_KEY,
                                                             routing_keys=data_collector_routing_keys)
    data_collector.run()


if __name__ == '__main__':
    main()
