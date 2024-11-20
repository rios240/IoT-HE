import device

CA_CERTIFICATE = "trust_store/iot_he.crt"

DEV_1A2B3C_CERTIFICATE = "key_store/dev_1A2B3C.crt"
DEV_1A2B3C_KEY = "key_store/dev_1A2B3C_keypair.pem"

DEV_4D5E6F_CERTIFICATE = "key_store/dev_4D5E6F.crt"
DEV_4D5E6F_KEY = "key_store/dev_4D5E6F_keypair.pem"

DEV_7G8H9I_CERTIFICATE = "key_store/dev_7G8H9I.crt"
DEV_7G8H9I_KEY = "key_store/dev_7G8H9I_keypair.pem"

SEAL_PUB_KEY = "trust_store/seal_public_key.bin"
SEAL_PARAMS_KEY = "trust_store/seal_params.bin"

def main():

    dev_1a2b3c = device.Device(ca_cert=CA_CERTIFICATE, seal_pub_key=SEAL_PUB_KEY, seal_params=SEAL_PARAMS_KEY,
                               device_cert=DEV_1A2B3C_CERTIFICATE,
                               device_key=DEV_1A2B3C_KEY, device_id="dev-1A2B3C", device_sn="T79HD20J",
                               routing_key="dev-1A2B3C.unprocessed")

    dev_4d5e6f = device.Device(ca_cert=CA_CERTIFICATE, seal_pub_key=SEAL_PUB_KEY, seal_params=SEAL_PARAMS_KEY,
                               device_cert=DEV_4D5E6F_CERTIFICATE,
                               device_key=DEV_4D5E6F_KEY, device_id="dev-4D5E6F", device_sn="H54JU72D",
                               routing_key="dev-4D5E6F.unprocessed")

    dev_7g8h9i = device.Device(ca_cert=CA_CERTIFICATE, seal_pub_key=SEAL_PUB_KEY, seal_params=SEAL_PARAMS_KEY,
                               device_cert=DEV_7G8H9I_CERTIFICATE,
                               device_key=DEV_7G8H9I_KEY, device_id="dev-7G8H9I", device_sn="L20YT63C",
                               routing_key="dev-7G8H9I.unprocessed")

    dev_1a2b3c.start()
    dev_4d5e6f.start()
    dev_7g8h9i.start()


if __name__ == '__main__':
    main()
