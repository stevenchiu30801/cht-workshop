"""2x2 Leaf-Spine Topology

Two leaf switches directly connected to each of two spine switches plus two hosts for each leaf switch

    spine     spine
      |   \ /   |
      |   / \   |
    leaf      leaf
    /  \      /  \
  host host host host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info

class MyTopo(Topo):

    def __init__(self):

        # initialize topology
        Topo.__init__(self)

        # leaf switches
        s1 = self.addSwitch("s1", dpid="0000000000000001")
        s2 = self.addSwitch("s2", dpid="0000000000000002")

        # spine switches
        s3 = self.addSwitch("s3", dpid="0000000000000003")
        s4 = self.addSwitch("s4", dpid="0000000000000004")

        # hosts
        h1 = self.addHost("h1", mac="00:00:00:00:00:01", ip="10.0.0.1/24")
        h2 = self.addHost("h2", mac="00:00:00:00:00:02", ip="10.0.0.2/24")
        h3 = self.addHost("h3", mac="00:00:00:00:00:03", ip="10.0.0.3/24")
        h4 = self.addHost("h4", mac="00:00:00:00:00:04", ip="10.0.0.4/24")

        # links between spine and leaf switches
        self.addLink(s1, s3)
        self.addLink(s1, s4)
        self.addLink(s2, s3)
        self.addLink(s2, s4)

        # links between leaf switches and hosts
        self.addLink(s1, h1)
        self.addLink(s1, h2)
        self.addLink(s2, h3)
        self.addLink(s2, h4)

topos = {'mytopo': (lambda: MyTopo())}

if __name__ == "__main__":
    setLogLevel('info')

    topo = MyTopo()
    net = Mininet(topo=topo)

    info('[INFO] Start 2x2 leaf-spine topology...\n')
    net.start()
    CLI(net)
    net.stop()
