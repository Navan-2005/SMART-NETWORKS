# utils.py

def get_neighbors_from_ip(my_ip, grid_size=3):
    """
    Returns a list of neighbor IPs based on the current node's IP.
    Assumes IP scheme: 10.0.Row.Col (e.g., 10.0.0.0 to 10.0.2.2)
    """
    try:
        # Parse the IP (e.g., "10.0.1.2")
        parts = my_ip.split('.')
        row = int(parts[2])
        col = int(parts[3])
    except:
        return []

    neighbors = []
    
    # Potential moves: Up, Down, Left, Right
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    for r_move, c_move in moves:
        new_r, new_c = row + r_move, col + c_move
        
        # Check Boundaries (Is this inside the grid?)
        if 0 <= new_r < grid_size and 0 <= new_c < grid_size:
            neighbor_ip = f"10.0.{new_r}.{new_c}"
            neighbors.append(neighbor_ip)
            
    return neighbors