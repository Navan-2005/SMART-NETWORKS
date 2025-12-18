import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

class GridTopo(Topo):
    def build(self, n=3):
        hosts = {}
        
        # 1. Create Hosts
        for r in range(n):
            for c in range(n):
                name = f'h{r}_{c}'
                # We use /24 to isolate them.
                # We start IPs at .1 (e.g., 10.0.1.1) to avoid invalid .0 addresses
                ip = f'10.0.{r+1}.{c+1}/24' 
                mac = f'00:00:00:00:{r+1:02x}:{c+1:02x}'
                host = self.addHost(name, ip=ip, mac=mac)
                hosts[(r,c)] = host
                
        # 2. Add Links 
        # The order here determines which interface is eth0 vs eth1
        for r in range(n):
            for c in range(n):
                # Horizontal Link (Right)
                if c < n-1: 
                    self.addLink(hosts[(r,c)], hosts[(r,c+1)])
                # Vertical Link (Down)
                if r < n-1: 
                    self.addLink(hosts[(r,c)], hosts[(r+1,c)])

def setup_grid_routes(net, n=3):
    """
    Manually set up static routes. This iterates through every link in the network
    and tells the hosts at both ends exactly how to reach each other.
    """
    print("[*] Setting up Static Routes for Grid...")
    
    # Map (r,c) to host objects
    hosts = {}
    for r in range(n):
        for c in range(n):
            hosts[(r,c)] = net.get(f'h{r}_{c}')

    # Iterate through all hosts to find their neighbors and interfaces
    for host in net.hosts:
        # Get list of interfaces (excluding loopback)
        for intf in host.intfList():
            if intf.name == 'lo': continue
            
            # Find the link connected to this interface
            link = intf.link
            if not link: continue
            
            # Identify the neighbor node
            node1, node2 = link.intf1.node, link.intf2.node
            neighbor = node2 if node1 == host else node1
            
            # Add a specific route: "To reach neighbor's IP, use this interface"
            host.cmd(f'ip route add {neighbor.IP()} dev {intf.name}')
            
            # Add a static ARP entry so we don't need ARP broadcasts
            host.cmd(f'arp -s {neighbor.IP()} {neighbor.MAC()}')

def run():
    os.system('mn -c') # Clean up old run
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Build Topology
    topo = GridTopo(n=3)
    net = Mininet(topo=topo, switch=OVSKernelSwitch, controller=None)
    net.start()

    # 🔧 APPLY THE ROUTING FIX
    setup_grid_routes(net, n=3)

    print("\n[+] Network Started. Initializing Q-Routers...")
    
    for host in net.hosts:
        # Disable Linux forwarding so our Python script handles the packets
        host.cmd('sysctl -w net.ipv4.ip_forward=0')
        
        print(f'Starting Router on {host.name} ({host.IP()})...')
        cmd = f'python3 router.py {host.name} {host.IP()} > logs/{host.name}.log 2>&1 &'
        host.cmd(cmd)

    print("[*] Q-Routing Agents running.")
    print("[*] Type 'exit' to stop.")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()