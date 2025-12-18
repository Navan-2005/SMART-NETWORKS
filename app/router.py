import socket
import json
import threading
import sys
import random
import os

# ---------------- CONFIG ----------------
MY_NAME = sys.argv[1]
MY_IP = sys.argv[2]
PORT = 8888

# Q-Learning Params
ALPHA = 0.5
GAMMA = 0.9
EPSILON = 0.1

MODEL_FILE = f"logs/q_table_{MY_NAME}.json"
Q_TABLE = {}
NEIGHBORS = []

# ---------------- HELPERS ----------------

def get_neighbors_from_ip(my_ip, grid_size=3):
    parts = my_ip.split('.')
    # Adjust for the +1 offset we added in topo.py
    # IP 10.0.1.1 corresponds to grid index (0,0)
    row, col = int(parts[2]) - 1, int(parts[3]) - 1

    neighbors = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = row + dr, col + dc
        if 0 <= nr < grid_size and 0 <= nc < grid_size:
            # Reconstruct neighbor IP with +1 offset
            neighbors.append(f"10.0.{nr+1}.{nc+1}")
    return neighbors

def load_model():
    global Q_TABLE
    if os.path.exists(MODEL_FILE):
        try:
            with open(MODEL_FILE) as f:
                Q_TABLE = json.load(f)
        except:
            Q_TABLE = {}

def save_model():
    with open(MODEL_FILE, 'w') as f:
        json.dump(Q_TABLE, f)

def init_dest(dest):
    if dest not in Q_TABLE:
        Q_TABLE[dest] = {n: 5.0 for n in NEIGHBORS}

# ---------------- CORE LOGIC ----------------

def choose_next_hop(dest, sender_ip):
    init_dest(dest)
    # Don't send back to the node that sent it to us!
    candidates = [n for n in NEIGHBORS if n != sender_ip]
    
    if not candidates:
        return None

    # Epsilon-Greedy Exploration
    if random.random() < EPSILON:
        choice = random.choice(candidates)
    else:
        # Exploit: Choose neighbor with lowest cost
        choice = min(candidates, key=lambda n: Q_TABLE[dest].get(n, 5.0))
    
    print(f"Next Hop Choice: {choice}", flush=True)
    return choice

def update_q(source_neighbor, dest, neighbor_est):
    init_dest(dest)
    current = Q_TABLE[dest].get(source_neighbor, 5.0)
    step_cost = 1
    new_q = current + ALPHA * ((step_cost + GAMMA * neighbor_est) - current)
    Q_TABLE[dest][source_neighbor] = new_q
    save_model()

# ---------------- NETWORKING ----------------

def send_packet(target_ip, pkt):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # NO BIND HERE! Let OS handle it.
        sock.sendto(json.dumps(pkt).encode(), (target_ip, PORT))
        sock.close()
    except Exception as e:
        print(f"[{MY_NAME}] ❌ SEND ERROR to {target_ip}: {e}", flush=True)

def handle_packet(data, addr):
    # addr is a tuple (ip, port)
    sender_ip_actual = addr[0] 
    
    try:
        pkt = json.loads(data.decode())
    except:
        return

    # 1. HANDLE FEEDBACK
    if pkt['type'] == 'FEEDBACK':
        # sender_ip_actual is the neighbor who gave us feedback
        print(f"[{MY_NAME}] ⬅️ Feedback from {sender_ip_actual} for {pkt['for_dest']}", flush=True)
        update_q(sender_ip_actual, pkt['for_dest'], pkt['best_estimate'])
        return

    # 2. HANDLE DATA
    dest = pkt['destination']
    
    # AM I THE DESTINATION?
    if dest == MY_IP:
        print(f"[{MY_NAME}] ✅ RECEIVED: {pkt['payload']}", flush=True)
        # Send Feedback (Cost = 0)
        feedback = {"type": "FEEDBACK", "for_dest": dest, "best_estimate": 0}
        send_packet(sender_ip_actual, feedback)
        return

    # FORWARDING
    print(f"[{MY_NAME}] ➡️ Forwarding DATA from {sender_ip_actual} to {dest}", flush=True)
    next_hop = choose_next_hop(dest, sender_ip_actual)
    
    if next_hop:
        send_packet(next_hop, pkt)
        
        # Send Feedback to previous node (Our estimated cost)
        my_best_est = min(Q_TABLE[dest].values())
        feedback = {"type": "FEEDBACK", "for_dest": dest, "best_estimate": my_best_est}
        send_packet(sender_ip_actual, feedback)

def start_router():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind to 0.0.0.0 to hear everyone
    sock.bind(('0.0.0.0', PORT)) 

    print(f"[{MY_NAME}] Online | IP={MY_IP} | Neighbors={NEIGHBORS}", flush=True)

    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(target=handle_packet, args=(data, addr), daemon=True).start()

if __name__ == "__main__":
    NEIGHBORS = get_neighbors_from_ip(MY_IP)
    load_model()
    start_router()