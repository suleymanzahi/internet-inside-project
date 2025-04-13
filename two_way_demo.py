from multiprocessing import Process
import time
import struct
from pyrf24 import RF24, RF24_PA_MIN, RF24_PA_LOW, RF24_2MBPS
import random
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
    """Radio 1: Sends a list of messages and waits for a reply to each."""
    radio.open_tx_pipe(address_out)
    radio.open_rx_pipe(1, address_in)
    messages = ["this","is","a","secret","message", "END"]
    # Loop through the messages and send them one by one
    for msg in messages:
        msg_success = False
        retries = 0
        while not msg_success:
            radio.stopListening()
            print(f" Sending: {msg} ")
            
            # Send the message
            success = radio.write(msg.encode())
            
            radio.startListening()
            start_time = time.time()

            # Wait for a reply for up to 'timeout' seconds
            while time.time() - start_time < timeout:
                if radio.available():
                    reply = radio.read().decode('utf-8')
                    print(f" {reply} ")
                    msg_success = True
                    # Wait for Radio 2's custom message
                    custom_msg = radio.read()
                    print(f" Received custom message from Radio 2: {custom_msg.decode()} ")
                    break
                time.sleep(0.7)
            else:
                if retries == 5:
                    print(" Other side is not communicating. Closing ..")
                    exit(-1)
                print(" Timeout waiting for reply. Sending again.. ")
                retries += 1
                

def radio_two(radio: RF24, address_in: bytes, address_out: bytes, timeout: int = 5):
    """Radio 2: Listens for a message, sends an acknowledgment, and also sends its own message."""
    radio.open_rx_pipe(1, address_in)
    radio.open_tx_pipe(address_out)
    radio.startListening()
    # Loop indefinitely to handle multiple messages
    while True:
        start_time = time.time()

        # Wait for a message for up to 'timeout' seconds
        while time.time() - start_time < timeout:
            if radio.available():
                received_msg = radio.read(radio.payload_size)
                received_msg = received_msg.decode('utf-8')
                if received_msg == "END":
                    print(f" Closing radio two.")
                    exit(0)
                # Send acknowledgment back (pong)
                radio.stopListening()
                ack_msg = f"ACK: {received_msg}"
                radio.write(ack_msg.encode())

                # Now send Radio 2's custom response message
                response_message = str(random.randint(1,100))
                radio.write(response_message.encode())
                start_time = time.time()
                radio.startListening()
                break

            time.sleep(0.7)
        else:
            print("Timeout waiting for message.")
            exit(-1)
            
# Setup for GPIO pins (CE, CSN) on the Raspberry Pi
# CE pin on GPIO17, CSN pin on GPIO0 (using spidev0.0)
# 27, 10 for other radio
# pins = [(17, 0), (27, 10)]
def setup_radio(radio: RF24, ce_pin: int, csn_pin: int):
    """Initializes the radio with necessary configurations."""
    if not radio.begin():
        raise RuntimeError(f"NRF24L01+ on pins {ce_pin}, {csn_pin} not responding")
    
    radio.set_pa_level(RF24_PA_MIN)
    radio.payload_size = 100
    radio.data_rate = RF24_2MBPS
    radio.close_rx_pipe(0)
    radio.close_rx_pipe(1)

def main():
    # Setup radios
    rx_radio = RF24(17, 0)  # Receiver radio (CE pin 17, CSN pin 0)
    tx_radio = RF24(27, 10)  # Transmitter radio (CE pin 27, CSN pin 10)

    # Initialize radios
    setup_radio(rx_radio, 17, 0)
    setup_radio(tx_radio, 27, 10)

    # Start processes for sending and receiving
    rx_process = Process(target=radio_one, kwargs={'radio': rx_radio, 'address_in': address[1], 'address_out': address[0]})
    tx_process = Process(target=radio_two, kwargs={'radio': tx_radio, 'address_in': address[0], 'address_out': address[1]})

    # Start both processes
    tx_process.start()
    time.sleep(1)  # Allow receiver to start first
    rx_process.start()

    # Wait for both processes to finish
    tx_process.join()
    rx_process.join()

if __name__ == "__main__":
    main()
