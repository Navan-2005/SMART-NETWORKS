def get_neighbors_from_ip(ip, grid_size=3):
    r, c = map(int, ip.split(".")[2:])
    neighbors = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < grid_size and 0 <= nc < grid_size:
            neighbors.append(f"10.0.{nr}.{nc}")
    return neighbors
