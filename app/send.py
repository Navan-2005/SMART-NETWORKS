import socket
import json
import sys
import time

# Usage: python3 send.py <ROUTER_IP> <DESTINATION_IP> <MESSAGE>

if len(sys.argv) < 4:
    print("Usage: python3 send.py <ROUTER_IP> <FINAL_DEST_IP> <MSG>")
    sys.exit()

router_ip = sys.argv[1]
final_dest_ip = sys.argv[2]
msg_content = sys.argv[3]
PORT = 8888

packet = {
    "type": "DATA",
    "source": router_ip, 
    "destination": final_dest_ip,
    "payload": msg_content,
    "timestamp": time.time()
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(json.dumps(packet).encode(), (router_ip, PORT))

print(f"[*] Injected message at {router_ip} --> headed for {final_dest_ip}")