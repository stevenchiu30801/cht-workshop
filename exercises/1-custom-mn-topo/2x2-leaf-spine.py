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

        """ TODO: construct 2x2 leaf-spine topology """

topos = {'mytopo': (lambda: MyTopo())}

if __name__ == "__main__":
    setLogLevel('info')

    topo = MyTopo()
    net = Mininet(topo=topo)

    info('[INFO] Start 2x2 leaf-spine topology...\n')
    net.start()
    CLI(net)
    net.stop()
