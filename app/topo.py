import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

class GridTopo(Topo):
    def build(self, n=3):
        self.grid_n = n
        hosts = {}
        
        # 1. Create Hosts with 0.0.0.0
        # We assign the real IP to the Loopback interface later to fix routing issues.
        for r in range(n):
            for c in range(n):
                name = f'h{r}_{c}'
                mac = f'00:00:00:00:{r+1:02x}:{c+1:02x}'
                # Init with 0.0.0.0 so Mininet doesn't create default routes
                host = self.addHost(name, ip='0.0.0.0', mac=mac)
                hosts[(r,c)] = host
                
        # 2. Add Links 
        for r in range(n):
            for c in range(n):
                if c < n-1: self.addLink(hosts[(r,c)], hosts[(r,c+1)]) # Horizontal
                if r < n-1: self.addLink(hosts[(r,c)], hosts[(r+1,c)]) # Vertical

def configure_network(net, n=4):
    print("[*] Configuring Loopback IPs, Static Routes, and Disabling Filters...")
    
    # 1. Setup Loopback IPs
    for r in range(n):
        for c in range(n):
            host = net.get(f'h{r}_{c}')
            # IP Scheme: h0_0 -> 10.0.1.1
            ip = f'10.0.{r+1}.{c+1}'
            host.cmd(f'ip addr add {ip}/32 dev lo')

    # 2. Setup Static Routes for every link
    for link in net.links:
        node1, intf1 = link.intf1.node, link.intf1
        node2, intf2 = link.intf2.node, link.intf2
        
        if 'h' not in node1.name or 'h' not in node2.name: continue
        
        # Helper to get IP from name hR_C
        get_ip = lambda h: f"10.0.{int(h.name.split('_')[0][1:])+1}.{int(h.name.split('_')[1])+1}"
        ip1, ip2 = get_ip(node1), get_ip(node2)

        # Route Node1 -> Node2 via specific interface
        node1.cmd(f'ip route add {ip2} dev {intf1.name} scope link')
        
        # 🔴 CHANGE 1: Use intf2.MAC() instead of node2.MAC()
        # This ensures the ARP entry matches the specific interface the wire connects to.
        node1.cmd(f'arp -s {ip2} {intf2.MAC()}')
        
        # Route Node2 -> Node1 via specific interface
        node2.cmd(f'ip route add {ip1} dev {intf2.name} scope link')
        
        # 🔴 CHANGE 2: Use intf1.MAC() instead of node1.MAC()
        node2.cmd(f'arp -s {ip1} {intf1.MAC()}')

def run():
    os.system('mn -c') # Clean up previous runs
    if not os.path.exists('logs'): os.makedirs('logs')

    topo = GridTopo(n=4)
    net = Mininet(topo=topo, switch=OVSKernelSwitch, controller=None)
    net.start()

    configure_network(net, n=4)

    print("\n[+] Network Started. Initializing Q-Routers...")
    
    for host in net.hosts:
        # 1. Disable IP Forwarding (Python handles it)
        host.cmd('sysctl -w net.ipv4.ip_forward=0')
        
        # 2. 🛑 DISABLE RP_FILTER (CRITICAL FIX)
        # This prevents Linux from dropping packets that come from "weird" interfaces
        host.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0')
        host.cmd('sysctl -w net.ipv4.conf.default.rp_filter=0')
        for intf in host.intfList():
            host.cmd(f'sysctl -w net.ipv4.conf.{intf}.rp_filter=0')

        # 3. Start Router Script
        r, c = map(int, host.name[1:].split('_'))
        my_ip = f"10.0.{r+1}.{c+1}"
        
        print(f'Starting Router on {host.name} ({my_ip})...')
        cmd = f'python3 router.py {host.name} {my_ip} > logs/{host.name}.log 2>&1 &'
        host.cmd(cmd)

    print("[*] Q-Routing Agents running. Type 'exit' to stop.")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()