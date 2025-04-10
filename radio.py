from pyrf24 import RF24, RF24_PA_MIN, RF24_PA_LOW, RF24_2MBPS
from multiprocessing import Queue
import time

def init_radios() -> tuple[RF24, RF24]:
    """Configures and returns the RX radio and TX radio for the device to use"""
    
    # TODO: both radios must be on different channels later
    # channel(tx_dev_0) == channel(rx_dev_1)
    # channel(tx_dev_1) == channel(rx_dev_0)
    # Initialize the RF24 object with the CE and CSN pin numbers
    # CE_PIN and CSN_PIN hardcoded since they won't change
    radios = (RF24(17, 0),  RF24(27, 10))
    #channel = 119, add a parameter so order switched between base station and mobile unit
    for radio in radios:

        if not radio.begin():
            raise RuntimeError("NRF24L01+ hardware is not responding")
        # for consistency purposes, since pipes remain open after program close
        radio.close_rx_pipe(0)
        radio.close_rx_pipe(1)
        #print(rx_nrf.is_chip_connected, rx_nrf.is_valid)
        radio.set_pa_level(RF24_PA_MIN) # can change to RF24_PA_LOW
        #radio.payload_size = len(payload[0])
        radio.data_rate = RF24_2MBPS
        #radio.channel = channel + 1 # for later when doing communication between two devices
        radio.print_pretty_details()

    # RF24(17, 0) should be rx, RF24(27, 10) tx
    return radios

def tx(radio: RF24, address: bytes, payload: bytes | bytearray, count: int = 5) -> None:   # count = 5 will only transmit 5 packets
    """Transmits an incrementing float every second"""
    radio.open_tx_pipe(address)
    radio.listen = False  # ensures the nRF24L01 is in TX mode


    # TODO: refactor so that it has a while loop running, polling a multiprocessing.Queue for data to Tx
    while count:
        # use struct.pack() to pack your data into a usable payload
        # into a usable payload
        #buffer = struct.pack("<f", payload[0])
        # "<f" means a single little endian (4 byte) float value.
        start_timer = time.monotonic_ns()  # start timer
        result = radio.write(payload)
        #result = radio.write_fast(payload[0])
        #radio.tx_standby(50)

        end_timer = time.monotonic_ns()  # end timer
        if not result:
            print("Transmission failed or timed out")
        else:
            print(
                "Transmission successful! Time to Transmit:",
                f"{(end_timer - start_timer) / 1000} us. Sent: {payload.decode()}",
            )
            #payload[0] += 0.01
        time.sleep(1)
        count -= 1
    radio.print_pretty_details()


def rx(radio: RF24, address: bytes, timeout: int = 6):
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission."""
    radio.open_rx_pipe(1, address) # not sure about address, double check
    radio.listen = True  # put radio into RX mode and power up

    # TODO: refactor so that it has a while True loop running, when data arrives -> deposit to multiprocessing.Queue
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        has_payload, pipe_number = radio.available_pipe()
        if has_payload:
            # TODO: we will always send full 32 bytes so manually setting paylaod length shouldn't be concern
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