""" Path Service

With global view of the topology, use Breadth First Search (BFS) to find a path from two nodes

- For ARP packets, simply flood (Thus, this application could not run on topologies with loops)

- For IPv4 packets, install flow rules on each switch of the path, which matching inport,
  source and destination Ethernet addresses, and then output

This script is the modification of Ryu built-in application, SimpleSwitch13
Please refer to https://github.com/osrg/ryu/blob/master/ryu/app/simple_switch_13.py
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

from ryu.lib import mac
from ryu.lib.packet import arp
from ryu.topology.api import get_link, get_switch, get_host
from ryu.topology import event, switches

class PathService(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PathService, self).__init__(*args, **kwargs)
        self.switch_graph = {}
        self.switch_map = {}
        self.topology_api_app = self


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.switch_map.update({datapath.id : datapath})

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)


    def get_topology(self):
        switch_list = get_switch(self.topology_api_app, None)
        for switch in switch_list:
            self.switch_graph.setdefault(switch.dp.id, [])

        link_list = get_link(self.topology_api_app, None)
        for link in link_list:
            if (link.dst.dpid, link.src.port_no, link.dst.port_no) not in self.switch_graph[link.src.dpid]:
                self.switch_graph[link.src.dpid].append((link.dst.dpid, link.src.port_no, link.dst.port_no))


    def bfs_shortest_path(self, src_switch, src_port, dst_switch, dst_port):
        visited = []
        queue = [[(src_switch, None, src_port)]]

        while queue:
            path = queue.pop(0)

            node = path[-1][0]
            if node not in visited:
                neighbors = self.switch_graph[node]

                for neighbor in neighbors:
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)

                    if neighbor[0] == dst_switch:
                        return new_path
            visited.append(node)
        return []


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        arp_pkt = pkt.get_protocol(arp.arp)
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.logger.info(" ARP: %s -> %s", arp_pkt.src_ip, arp_pkt.dst_ip)

            """ TODO: flood ARP packets """

            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.logger.info("packet in dpid %s src %s dst %s in_port %s", dpid, src, dst, in_port)

        # get topology
        self.get_topology()
        src_switch = None
        src_port = in_port
        dst_switch = None
        dst_port = None

        host_list = get_host(self.topology_api_app, None)

        for host in host_list:
            if host.mac == src:
                src_switch = host.port.dpid
                    
            if host.mac == dst:
                dst_switch = host.port.dpid
                dst_port = host.port.port_no

        if dst_switch == None:
            self.logger.info("Destination switch not found on host %s", dst)
            return

        if src_switch == dst_switch:
            # If source edge switch is equal to destination edge switch,
            # there is not need to perform BFS
            
            """ TODO: install flow rule """

        else:
            bfs_shortest_path = self.bfs_shortest_path(src_switch, src_port, dst_switch, dst_port)
            if len(bfs_shortest_path) == 0:
                self.logger.info("Cannot find path!!!")
            else:
                pre_node = None
                for node in reversed(bfs_shortest_path):
                    if node[0] == dst_switch:
                        actions = [parser.OFPActionOutput(dst_port)]
                        match = parser.OFPMatch(in_port=node[2], eth_src=src, eth_dst=dst, eth_type=0x0800)

                    elif node[0] == src_switch:
                        actions = [parser.OFPActionOutput(pre_node[1])]
                        match = parser.OFPMatch(in_port=src_port, eth_src=src, eth_dst=dst, eth_type=0x0800)

                    else:
                        actions = [parser.OFPActionOutput(pre_node[1])]
                        match = parser.OFPMatch(in_port=node[2], eth_src=src, eth_dst=dst, eth_type=0x0800)

                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(self.switch_map[node[0]], 1, match, actions, msg.buffer_id)
                    else:
                        self.add_flow(self.switch_map[node[0]], 1, match, actions)
                    pre_node = node
