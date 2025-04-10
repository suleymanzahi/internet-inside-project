from multiprocessing import Process
import time
import radio

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our float number for the payloads sent
payload = [b"Hello, Universe!"]

# For this example, we will use different addresses
# An address need to be a buffer protocol object (bytearray)
address = [b"1Node", b"2Node"]

"""
* The main process will read from the TUN device
* Fragment data into packets (create a separate module for that) and send to Tx-process via mp.Queue
* Rx-process listens for data and deposits to mp.Queue, main process grabs it and writes back to TUN device
"""

rx_nrf, tx_nrf = radio.init_radios()

rx_process = Process(target=radio.rx, kwargs={'radio':rx_nrf, 'address':address[0]})
tx_process = Process(target=radio.tx, kwargs={'radio':tx_nrf, 'address':address[0], 'payload':payload[0]})

rx_process.start()
time.sleep(1)
tx_process.start()

tx_process.join()
rx_process.join()
