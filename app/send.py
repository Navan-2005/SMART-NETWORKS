import socket
import json
import sys
import time

# USAGE: python3 send.py <DESTINATION_IP> <MESSAGE>

if len(sys.argv) < 3:
    print("Usage: python3 send.py <DESTINATION_IP> <MESSAGE>")
    sys.exit()

# We always send to the local router on THIS node
ROUTER_IP = "127.0.0.1" 
PORT = 8888

final_dest_ip = sys.argv[1]
msg_content = " ".join(sys.argv[2:])

packet = {
    "type": "DATA",
    "destination": final_dest_ip,
    "payload": msg_content,
    "timestamp": time.time()
}

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(packet).encode(), (ROUTER_IP, PORT))
    print(f"[*] Packet injected! Dest: {final_dest_ip} | Msg: {msg_content}")
except Exception as e:
    print(f"[!] Error: {e}")