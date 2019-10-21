# Mininet/Open vSwitch/Ryu Cheatsheet

## Mininet
**1. Start a minimal topology**
```
$ sudo mn
```

**2. Change topology size and type**
```
$ sudo mn --topo single,3
$ sudo mn --topo tree,2
```

**3. Start custom topology**
```
$ sudo mn --custom <custom-topo-path> --topo <custom-topo>
```
Take topology file, `example.py`, in exercise 1 as example
```
$ sudo mn --custom exercises/1-custom-mn-topo/example.py --topo mytopo
```

**4. Start topology using remote controller**
```
$ sudo mn --controller=remote,ip=<controller-ip>,port=<controller-port>
```
Take local Ryu controller as example
```
$ sudo mn --controller=remote,ip=127.0.0.1,port=6653
```

**5. Cleanup Mininet**
```
$ sudo mn -c
```

## Open vSwitch
**1. Print a brief overview of switch database contents**
```
$ ovs-vsctl show
```

**2. Print flow entries in switch's tables**
```
$ ovs-ofctl dump-flows <bridge>
```

**3. Add flow entries to switch’s table**
```
$ ovs-ofctl add-flow <bridge> <flow-entry>
```
For example, add a flow entry simply using traditional non-OpenFlow pipeline and outputting on `s1`
```
$ ovs-ofctl add-flow s1 actions=normal
```
For another example, add a flow entry with priority `1000` which matching Ethernet source address `F6:DB:E3:88:DE:2C` and outputting to port `2` on bridge `s1`
```
$ ovs-ofctl add-flow s1 priority=1000,eth_src=f6:db:e3:88:de:2c,actions=output:2
```

**4. Delete all or single flow entry from switch's table**
```
$ ovs-ofctl del-flows <bridge>
$ ovs-ofctl del-flows <bridge> <flow-entry>
```

## Ryu
**1. Run Ryu application**
```
$ ryu-manager <built-in-app>
$ ryu-manager <app-file-path>
```
For example, run built-in application which providing REST API, and path service application in exercise 2
```
$ ryu-manager ryu.app.ofctl_rest exercises/2-path-service/path_service.py
```