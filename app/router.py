import socket
import json
import threading
import time
import sys
import random
import os

# --- CONFIGURATION ---
MY_NAME = sys.argv[1]
MY_IP = sys.argv[2]
PORT = 8888
ALPHA = 0.5   # Learning Rate
GAMMA = 0.9   # Discount Factor
MODEL_FILE = f"logs/q_table_{MY_NAME}.json"

# Q-Table Structure: { 'Destination_IP': { 'Neighbor_IP': Estimated_Cost } }
Q_TABLE = {}
NEIGHBORS = [] 

# --- UTILITIES (Neighbor Discovery) ---

def get_neighbors_from_ip(my_ip, grid_size=3):
    """Calculates neighbor IPs for a grid topology (10.0.r.c)."""
    try:
        parts = my_ip.split('.')
        row = int(parts[2])
        col = int(parts[3])
    except:
        return []

    neighbor_ips = []
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)] # Up, Down, Left, Right
    
    for r_move, c_move in moves:
        new_r, new_c = row + r_move, col + c_move
        if 0 <= new_r < grid_size and 0 <= new_c < grid_size:
            neighbor_ips.append(f"10.0.{new_r}.{new_c}")
            
    return neighbor_ips

# --- Q-LEARNING CORE ---

def load_model():
    global Q_TABLE
    if os.path.exists(MODEL_FILE):
        try:
            with open(MODEL_FILE, 'r') as f:
                Q_TABLE = json.load(f)
            print(f"[{MY_NAME}] Loaded Q-Table from disk.")
        except:
            print(f"[{MY_NAME}] Error loading model, starting fresh.")

def save_model():
    with open(MODEL_FILE, 'w') as f:
        json.dump(Q_TABLE, f)

def get_best_neighbor(destination):
    """Decides where to send the packet next."""
    # Initialize if we've never heard of this destination
    if destination not in Q_TABLE:
        Q_TABLE[destination] = {n: 5.0 for n in NEIGHBORS} # Default high cost
    
    # Epsilon-Greedy: 10% chance to explore a random path
    if random.random() < 0.1:
        return random.choice(NEIGHBORS)
    
    # Exploitation: Pick the neighbor with the lowest estimated cost
    estimates = Q_TABLE[destination]
    # Filter only valid current neighbors
    valid_estimates = {k: v for k, v in estimates.items() if k in NEIGHBORS}
    
    if not valid_estimates:
        return random.choice(NEIGHBORS)
        
    return min(valid_estimates, key=valid_estimates.get)

def update_q_table(source_neighbor, destination, neighbor_best_estimate):
    """The Bellman Equation: Updates the Q-Value based on feedback."""
    if destination not in Q_TABLE:
        Q_TABLE[destination] = {n: 5.0 for n in NEIGHBORS}
    
    if source_neighbor not in Q_TABLE[destination]:
         Q_TABLE[destination][source_neighbor] = 5.0

    current_q = Q_TABLE[destination][source_neighbor]
    
    # Reward structure: Cost = 1 hop (simplified cost)
    step_cost = 1 
    
    # New_Q = Old_Q + Alpha * ( (Reward + Gamma * Future) - Old_Q )
    new_q = current_q + ALPHA * ( (step_cost + GAMMA * neighbor_best_estimate) - current_q )
    
    Q_TABLE[destination][source_neighbor] = new_q
    
    # Auto-save model occasionally
    save_model() 

# --- PACKET HANDLING ---

def send_packet(target_ip, data):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(data).encode(), (target_ip, PORT))
    except Exception as e:
        print(f"[{MY_NAME}] Failed to send to {target_ip}: {e}")

def handle_incoming(data, addr):
    try:
        pkt = json.loads(data.decode())
    except:
        return
        
    sender_ip = addr[0]

    # --- TYPE 1: FEEDBACK (Learning Signal) ---
    if pkt['type'] == 'FEEDBACK':
        # Neighbor telling us: "It will take me X time to get to Destination D"
        update_q_table(sender_ip, pkt['for_dest'], pkt['best_estimate'])
        return

    # --- TYPE 2: DATA (The actual message) ---
    if pkt['type'] == 'DATA':
        dest = pkt['destination']
        
        # A. Am I the destination?
        if dest == MY_IP:
            print(f"[{MY_NAME}] \033[92mPACKET RECEIVED!\033[0m Payload: {pkt['payload']}")
            return

        # B. I need to forward it.
        next_hop = get_best_neighbor(dest)
        
        # 1. Send FEEDBACK to the Previous Node
        # "Hey sender, I received your packet for {dest}. My best estimate to get there is X."
        my_best_est = min(Q_TABLE[dest].values()) if dest in Q_TABLE else 5.0
        feedback_pkt = {
            "type": "FEEDBACK",
            "from_node": MY_IP,
            "for_dest": dest,
            "best_estimate": my_best_est
        }
        send_packet(sender_ip, feedback_pkt)
        
        # 2. Forward the Packet
        send_packet(next_hop, pkt)

def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((MY_IP, PORT))
    print(f"[{MY_NAME}] Router online. IP: {MY_IP}, Neighbors: {NEIGHBORS}")
    
    while True:
        data, addr = sock.recvfrom(4096)
        # Handle in a thread to avoid blocking
        threading.Thread(target=handle_incoming, args=(data, addr)).start()

if __name__ == "__main__":
    # 1. Discover Neighbors
    NEIGHBORS = get_neighbors_from_ip(MY_IP)
    
    # 2. Load previous learning
    load_model()
    
    # 3. Start Router
    start_server()