from multiprocessing import Process
import time
import struct
from pyrf24 import RF24, RF24_PA_MIN, RF24_PA_LOW, RF24_2MBPS

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our float number for the payloads sent
payload = [b"Hello, Universe!"]

# For this example, we will use different addresses
# An address need to be a buffer protocol object (bytearray)
address = [b"1Node", b"2Node"]

# It is very helpful to think of an address as a path instead of as
# an identifying device destination

# To save time during transmission, we'll set the payload size to be only what
# we need. A float value occupies 4 bytes in memory using struct.calcsize()
# "<f" means a little endian unsigned float

def radio_one(radio: RF24, address_in: bytes, address_out: bytes, timeout: int = 5): 
    """ Starts in transfering mode."""
    radio.open_tx_pipe(address_out)
    radio.open_rx_pipe(1,address_in)
    msg_count = 0
    msg_sent = 5
    for _ in range(msg_sent):
        msg_count += 1
        radio.listen = False  # ensures the nRF24L01 is in TX mode
        msg = "ping"
        time.sleep(1)
        print(f"Sent: {msg} -->\n")
        radio.write(msg.encode())
        answer_rc = False
        radio.listen = True
        if msg_sent == msg_count:
            print("Sent all messages!\n")
        timeout_start = time.time() + timeout
        while not answer_rc:
            has_payload, pipe_number = radio.available_pipe()
            if has_payload:
                received = radio.read()
                received = received.decode('utf-8')
                print(f"Received: {received}\n")
                if msg_sent == msg_count:
                    print("Recieved same amount of messages as I've sent!\n")
                break
            if time.time() >= timeout_start:
                print("Radio one timed out\n")
                exit(-1)


def radio_two(radio: RF24, address_in: bytes, address_out: bytes, timeout: int = 5):
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission.
    Starts in listening mode."""
    radio.open_rx_pipe(0, address_in) # not sure about address, double check
    radio.open_tx_pipe(address_out)
    radio.listen = True  # put radio into RX mode and power up

    timeout_start = time.time() + timeout
    while time.time() < timeout_start:
        has_payload, pipe_number = radio.available_pipe()
        #print("listening")
        if has_payload:
            received = radio.read()
            received = received.decode('utf-8')
            print(f"Received: {received}\n")
            radio.listen = False
            msg = "pong"
            time.sleep(1)
            print(f"Sent: {msg} -->\n")
            radio.write(msg.encode())
            radio.listen = True
            timeout_start = time.time() + timeout
            
    print("\n Radio two timed out")
            
# Setup for GPIO pins (CE, CSN) on the Raspberry Pi
# CE pin on GPIO17, CSN pin on GPIO0 (using spidev0.0)
# 27, 10 for other radio
# pins = [(17, 0), (27, 10)]
radios = [RF24(17, 0),  RF24(27, 10)]

# Initialize the RF24 object with the CE and CSN pin numbers
rx_nrf, tx_nrf = radios
for radio in radios:

    if not radio.begin():
        raise RuntimeError("NRF24L01+ hardware is not responding")
    # for consistency purposes, since pipes remain open after program close
    radio.close_rx_pipe(0)
    radio.close_rx_pipe(1)
    #print(rx_nrf.is_chip_connected, rx_nrf.is_valid)
    radio.set_pa_level(RF24_PA_MIN)
    radio.payload_size = len(payload[0])
    radio.data_rate = RF24_2MBPS

    #radio.print_pretty_details()
    
rx_process = Process(target=radio_one, kwargs={'radio':rx_nrf, 'address_in':address[1],'address_out':address[0]})
tx_process = Process(target=radio_two, kwargs={'radio':tx_nrf, 'address_in':address[0],'address_out':address[1]})
rx_process.start()
time.sleep(1)
tx_process.start()

tx_process.join()
rx_process.join()
