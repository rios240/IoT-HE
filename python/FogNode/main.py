import fognode

CA_CERTIFICATE = "trust_store/iot_he.crt"

FOG_NODE_1_CERTIFICATE = "key_store/fog_1.crt"
FOG_NODE_1_KEY = "key_store/fog_1_keypair.pem"

FOG_NODE_2_CERTIFICATE = "key_store/fog_2.crt"
FOG_NODE_2_KEY = "key_store/fog_2_keypair.pem"

SEAL_RELIN_KEYS = "trust_store/seal_relin_keys.bin"
SEAL_PARAMS = "trust_store/seal_params.bin"


def main():

    fog_1_routing_keys = ["dev-1A2B3C.unprocessed", "dev-4D5E6F.unprocessed"]
    fog_1 = fognode.ReconnectingFogNode(ca_cert=CA_CERTIFICATE,
                                        node_cert=FOG_NODE_1_CERTIFICATE, node_key=FOG_NODE_1_KEY,
                                        routing_keys=fog_1_routing_keys,
                                        seal_params=SEAL_PARAMS, seal_relin_keys=SEAL_RELIN_KEYS)

    fog_2_routing_keys = ["dev-7G8H9I.unprocessed"]
    fog_2 = fognode.ReconnectingFogNode(ca_cert=CA_CERTIFICATE,
                                        node_cert=FOG_NODE_2_CERTIFICATE, node_key=FOG_NODE_2_KEY,
                                        routing_keys=fog_2_routing_keys,
                                        seal_params=SEAL_PARAMS, seal_relin_keys=SEAL_RELIN_KEYS)

    fog_1.start()
    fog_2.start()


if __name__ == '__main__':
    main()
