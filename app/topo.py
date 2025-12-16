import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

class GridTopo(Topo):
    def build(self, n=3):
        # Create a Grid of Hosts (h0_0 to h2_2)
        switches = {}
        hosts = {}
        
        # 1. Create Hosts
        for r in range(n):
            for c in range(n):
                name = f'h{r}_{c}'
                # Simple IP assignment: 10.0.r.c
                # MAC address is set deterministically for easier debugging
                mac = f'00:00:00:00:0{r}:0{c}'
                host = self.addHost(name, ip=f'10.0.{r}.{c}/24', mac=mac)
                hosts[(r,c)] = host
                
        # 2. Add Links (Horizontal & Vertical)
        # We add links between hosts to create the grid structure
        for r in range(n):
            for c in range(n):
                # Connect to Right Neighbor
                if c < n-1: 
                    self.addLink(hosts[(r,c)], hosts[(r,c+1)])
                # Connect to Bottom Neighbor
                if r < n-1: 
                    self.addLink(hosts[(r,c)], hosts[(r+1,c)])

def run():
    # Clean up any previous runs
    os.system('mn -c')
    
    # Create logs directory
    if not os.path.exists('logs'):
        os.makedirs('logs')

    topo = GridTopo(n=3)
    net = Mininet(topo=topo, switch=OVSKernelSwitch)
    net.start()

    print("\n[+] Network Started. Initializing Q-Routers...")
    print("[+] Logs for each router will be in the 'logs/' folder.\n")
    
    # Start the router script on every host
    for host in net.hosts:
        # Disable default Linux forwarding so our script handles packets
        host.cmd('sysctl -w net.ipv4.ip_forward=0')
        
        # Run router.py in background
        # We pass the Host Name and IP as arguments
        # Output is redirected to a log file for debugging
        cmd = f'python3 router.py {host.name} {host.IP()} > logs/{host.name}.log 2>&1 &'
        host.cmd(cmd)

    print("[*] Q-Routing Agents are running on all nodes.")
    print("[*] You can now inject traffic using send.py")
    print("[*] Type 'exit' to stop the simulation.")
    
    CLI(net)
    
    print("[-] Stopping network...")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()