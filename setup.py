from multiprocessing import Process, Pipe
import time
import radio
from tuntap import TunTap
from scapy.all import Ether, IP, IPv6, hexdump
import os
import subprocess



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

tx_from_main, main_to_tx = Pipe() # from docs: conn1 can only be used for receiving messages and conn2 can only be used for sending messages.
main_from_rx, rx_to_main = Pipe()


rx_process = Process(target=radio.rx, kwargs={'radio':rx_nrf, 'address':address[0], 'conn':rx_to_main })
tx_process = Process(target=radio.tx, kwargs={'radio':tx_nrf, 'address':address[0], 'conn':tx_from_main})

rx_process.start()
time.sleep(1)
tx_process.start()


name="myG"
ip = "192.168.2.2"
tun = TunTap(nic_type="Tun",nic_name=name)

#this is to stop IPv6 router solicitation packets from coming to tun interface
cmd = f"sysctl -w net.ipv6.conf.{name}.disable_ipv6=1"
try:
    result = subprocess.run(cmd.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("IPv6 disabled:", result.stdout.decode())
except subprocess.CalledProcessError as e:
    print("Failed to disable IPv6:", e.stderr.decode())

tun.config(ip=ip,mask="255.255.255.0")
# temporary, just so that ping to the device itself gets picked up by this program
#os.system("sudo ip addr del 10.0.0.0/24 dev lo") 
#os.system("sudo ip route add 10.0.0.0/24 dev tun0" ) 
os.system(f"ip route add default via 192.168.2.1 dev myG")


# TODO, investigate how to use less than 1 byte, would have to iterate thrugh individual bits
# use 1 byte to denote fragment seq number, so 31 bytes for payload

def fragment(seq, size=31):
    fragments = [seq[pos:pos + size] for pos in range(0, len(seq), size)]
    return [(i).to_bytes(1) + f for i, f in enumerate(fragments)]


# TODO, some initial thoughts about 'protocol'
# we should pad chunks less than size 32 with filler data like 'z' or 'x', i.e so nrf doesn't pad it with zeros
# then check if last element is a filler, then iterate backwards until not filler

# TODO, what should happen if a fragmented chunk doens't get thorugh? not sure how to handle
# NRF lib code has ACK payloads, could investigate that.

# TODO clean up linux commands in tundev.py

# TODO handle fragmentation better? 

# TODO create startup scripts for base station and mobile (modify setup.py)
# major things is to setup routing, tun, IP tables on base station, and get ping -> base station and ping to 8.8.8.8 working

# TODO big-endian versus little endian seems to be messed up

# TODO must take into account random requests, like NTP requests

try:
    while True:
        data = tun.read()
        hexdump(data)
        fragmented_chunks = fragment(data)
        for chunk in fragmented_chunks:
            main_to_tx.send(chunk)
        #print(packet)
        #hexdump(packet)  # See the raw bytes
except KeyboardInterrupt:
    pass
finally:
    os.system(f"ip link delete {name}")


tx_process.join()
rx_process.join()
