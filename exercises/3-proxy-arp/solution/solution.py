""" Proxy ARP

Handle ARP request and reply packets as a proxy

- For ARP requests, first record source node in ARP cache and then search for request address in cache
    - If hit, Packet-OUT with ARP reply
    - If miss, flood the ARP request on all edge switches

- For ARP reply, record ARP information in cache and forward

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

# arp operation codes
ARP_REQUEST = 1
ARP_REPLY = 2
ARP_REV_REQUEST = 3
ARP_REV_REPLY = 4

class ProxyARP(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProxyARP, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.arp_table = {}
        self.switch_map = {}


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.switch_map.update({datapath.id: datapath})

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

        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            # ignore ipv6 router solicitation message
            return

        host_list = get_host(self.topology_api_app, None)

        arp_pkt = pkt.get_protocol(arp.arp)
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.logger.info(" ARP: %s -> %s", arp_pkt.src_ip, arp_pkt.dst_ip)

            # record source ip to mac address in arp cache
            self.arp_table[arp_pkt.src_ip] = arp_pkt.src_mac

            if arp_pkt.opcode == ARP_REQUEST:
                if arp_pkt.dst_ip in self.arp_table:
                    # build a packet for sending arp reply to src_ip
                    e = ethernet.ethernet(dst=arp_pkt.src_mac, src=self.arp_table[arp_pkt.dst_ip], ethertype=ether_types.ETH_TYPE_ARP)
                    a = arp.arp(hwtype=1, proto=0x800, hlen=6, plen=4, opcode=2, src_mac=self.arp_table[arp_pkt.dst_ip], src_ip=arp_pkt.dst_ip, dst_mac=arp_pkt.src_mac, dst_ip=arp_pkt.src_ip)
                    arp_reply = packet.Packet()
                    arp_reply.add_protocol(e)
                    arp_reply.add_protocol(a)
                    arp_reply.serialize()

                    actions = [parser.OFPActionOutput(in_port)]
                    data = arp_reply.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.datapath.ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=data)
                    datapath.send_msg(out)

                else:
                    # build a packet for sending arp request to dst_ip
                    arp_request = pkt

                    for host in host_list:
                        if arp_pkt.src_ip not in host.ipv4:
                            actions = [parser.OFPActionOutput(host.port.port_no)]
                            data = arp_request.data
                            datapath = self.switch_map[host.port.dpid]
                            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.datapath.ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=data)
                            datapath.send_msg(out)

            if arp_pkt.opcode == ARP_REPLY:
                # build a packet for sending arp reply to src_ip
                arp_reply = pkt

                for host in host_list:
                    if arp_pkt.dst_ip in host.ipv4:
                        actions = [parser.OFPActionOutput(host.port.port_no)]
                        data = arp_reply.data
                        datapath = self.switch_map[host.port.dpid]
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.datapath.ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=data)
                        datapath.send_msg(out)
