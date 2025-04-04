from multiprocessing import Process
import time
import struct
from pyrf24 import RF24, RF24_PA_MIN, RF24_2MBPS

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our float number for the payloads sent
payload = [b"greetings to all!"]

# For this example, we will use different addresses
# An address need to be a buffer protocol object (bytearray)
address = [b"1Node", b"2Node"]

# It is very helpful to think of an address as a path instead of as
# an identifying device destination

# To save time during transmission, we'll set the payload size to be only what
# we need. A float value occupies 4 bytes in memory using struct.calcsize()
# "<f" means a little endian unsigned float

def tx(radio: RF24, address: bytes, count: int = 5):  # count = 5 will only transmit 5 packets
    """Transmits an incrementing float every second"""
    radio.listen = False  # ensures the nRF24L01 is in TX mode

    while count:
        # use struct.pack() to pack your data into a usable payload
        # into a usable payload
        #buffer = struct.pack("<f", payload[0])
        # "<f" means a single little endian (4 byte) float value.
        start_timer = time.monotonic_ns()  # start timer
        #result = radio.write(payload[0])
        result = radio.write_fast(payload[0])
        #radio.tx_standby()

        end_timer = time.monotonic_ns()  # end timer
        if not result:
            print("Transmission failed or timed out")
        else:
            print(
                "Transmission successful! Time to Transmit:",
                f"{(end_timer - start_timer) / 1000} us. Sent: {payload[0].decode()}",
            )
            #payload[0] += 0.01
        time.sleep(1)
        count -= 1
    radio.print_pretty_details()

def rx(radio: RF24, address: bytes, timeout: int = 6):
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission."""

    radio.listen = True  # put radio into RX mode and power up

    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        has_payload, pipe_number = radio.available_pipe()
        if has_payload:
            length = radio.payload_size  # grab the payload length
            # fetch 1 payload from RX FIFO
            received = radio.read()  # also clears radio.irq_dr status flag
            #received = radio.read(length)  # also clears radio.irq_dr status flag
            # expecting a little endian float, thus the format string "<f"
            # received[:4] truncates padded 0s in case dynamic payloads are disabled
            #payload[0] = struct.unpack("<f", received[:4])[0]
            received = received.decode('utf-8')
            # print details about the received packet
            print(f"Received {len(received)} bytes on pipe {pipe_number}: {received}")
            start = time.monotonic()  # reset the timeout timer

    # recommended behavior is to keep in TX mode while idle
    radio.listen = False  # put the nRF24L01 is in TX mode
    radio.print_pretty_details()
# Setup for GPIO pins (CE, CSN) on the Raspberry Pi
# CE pin on GPIO17, CSN pin on GPIO0 (using spidev0.0)
# 27, 10 for other radio
# pins = [(17, 0), (27, 10)]
radios = [RF24(17, 0),  RF24(27, 10)]

# Initialize the RF24 object with the CE and CSN pin numbers
rx_nrf, tx_nrf = radios

for i, radio in enumerate(radios):
    if not radio.begin():
        raise RuntimeError("NRF24L01+ hardware is not responding")

    #print(rx_nrf.is_chip_connected, rx_nrf.is_valid)
    radio.set_pa_level(RF24_PA_MIN)
    i = bool(i)
    if not i:
        radio.open_tx_pipe(address[i])  # always uses pipe 0
    radio.open_rx_pipe(1, address[not i])  # using pipe 1
    #radio.payload_size = struct.calcsize("<f")
    radio.payload_size = len(payload[0])
    radio.data_rate = RF24_2MBPS

    radio.print_pretty_details()

rx_process = Process(target=rx, kwargs={'radio':rx_nrf, 'address':address})
tx_process = Process(target=tx, kwargs={'radio':tx_nrf, 'address':address})

rx_process.start()
time.sleep(1)
tx_process.start()

tx_process.join()
rx_process.join()
