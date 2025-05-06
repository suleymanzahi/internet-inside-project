# must be run with python from virtual environment, sudo .venv/bin/python tundev.py

# from pytun import TunTapDevice


# tun = TunTapDevice()

# tun = TunTapDevice(name='tun1')

# print(tun.name)
# tun.addr = '10.8.0.1'
# tun.dstaddr = '10.8.0.2'
# tun.netmask = '255.255.255.0'
# tun.mtu = 1500
# tun.up()

# while True:
#     buf = tun.read(tun.mtu)
#     print()
from tuntap import TunTap
from scapy.all import Ether, IP, IPv6, hexdump
import os
import subprocess

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

try:
    while True:
        packet = tun.read()
        print(f" Length of packet: {len(packet)}" )
        print(packet)
        #hexdump(packet)  # See the raw bytes
except KeyboardInterrupt:
    pass
finally:
    os.system(f"ip link delete {name}")