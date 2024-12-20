# Practical Demonstration of Homomorphic Encryption in Fog/Cloud Computing for IoT Devices
In the modern era of interconnected devices, web services are indispensable in both personal
and business computing. These services facilitate the seamless exchange of information and control
between users, devices, and remote servers through standardized communication protocols.
However, the ubiquity of these services introduces significant security challenges, particularly when
communication takes place over public networks prone to monitoring, manipulation, and
unauthorized access.
In this context, IoT (Internet of Things) devices represent a rapidly growing segment of web
service applications. These devices generate and transmit vast amounts of data, necessitating robust
mechanisms for securing sensitive information and ensuring the integrity of communications. The
integration of fog and cloud computing architectures further amplifies the complexity, as data is
often processed and stored at multiple intermediary nodes before reaching a centralized collector or
storage location.
This project demonstrates the application of homomorphic encryption to address the security
concerns inherent in IoT-based fog/cloud computing systems. Homomorphic encryption enables
operations on encrypted data without exposing the plaintext, ensuring data privacy while supporting
computational needs. By employing Microsoft SEAL’s Python library, RabbitMQ as a message
broker, and secure communication protocols, the project exemplifies a practical solution for
securing IoT device communications in a fog/cloud architecture.

---

## Setup

1. **Ensure Docker and Docker Compose Plugin are installed.**
2. **Install Python Virtual Environment.**
3. **Clone this repository:**

    ```bash
    git clone git@github.com:rios240/IoT-HE.git
    cd IoT-HE
    ```

4. **Create a virtual environment and install packages:**

    ```bash
    cd python
    python3 -m venv env
    source env/bin/activate
    pip3 install -r requirements.txt
    ```

---

## Running

1. **You will need at least four terminal tabs/windows open:**
   - One for running the Docker container.
   - One for running the IoT Devices.
   - One for running the Fog Nodes.
   - One for running the Data Collector node.

2. **In the first tab/window, start the Docker container:**

    ```bash
    cd docker
    docker compose up
    ```

3. **In the second tab/window, start the IoT devices:**

    ```bash
    cd python/Device
    source ../env/bin/activate
    python3 main.py
    ```

4. **In the third tab/window, start the Fog Nodes:**

    ```bash
    cd python/FogNode
    source ../env/bin/activate
    python3 main.py
    ```

5. **In the fourth tab/window, start the Data Collector node:**

    ```bash
    cd python/DataCollector
    source ../env/bin/activate
    python3 main.py
    ```

---

## Output

The `device.py`, `fognode.py`, and `datacollector.py` scripts generate extensive log data. While most logs can be ignored, focus on the following **INFO logs**:

- **On `device.py`:** Look for logs with the message `"### Published message..."`, which show the device and the plaintext number generated.
- **On `fognode.py`:** Look for logs with the message `"### Received message..."`, which display the device whose message was received and the homomorphic operation performed on the encrypted text (e.g., `x^4`).
- **On `datacollector.py`:** Look for logs with the message `"### Received message..."`, which show the device and the result of the operation as plaintext.
