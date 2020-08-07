#!/usr/bin/env python2
'''Create a traffic mirroring scheme within a mininet environment using ONOS as
the SDN controller.

This module creates a new openvswitch 'span' within the existing SDN and mirrors
all the traffic originating from the SDN into the new openvswitch bridge.

As an extra assurance against any tampering comming from the SDN, a flow rule is
added in the SDN controller to prevent any traffic from propagating from the new
openvswitch bridge into the SDN. This rule is added to the flow table with a high
priority (60000), effectively 'disconnecting' the span bridge from the SDN while
it receives all the traffic.'''

import sys
from vsctl import VSCtl
from base64 import standard_b64encode
import json
import requests
from requests.auth import HTTPBasicAuth
from time import sleep

# SDN Controller information
CONTROLLER_IP = '192.168.56.50'
CONTROLLER_PORT = 6633
# REST API information
REST_PORT = 8181
REST_USER = 'onos'
REST_PASS = 'rocks'

def mirror():
    '''Create the mirroring scheme in the current instance of mininet using the
    specified ONOS controller.'''
    try:
        rest_auth = HTTPBasicAuth(REST_USER, REST_PASS)                                             # Initialize
        ovs = VSCtl()
        switches = ovs.listbr()
        ovs.addbr('span')                                                                           # Create openvswitch bridge for the mirror
        ovs.setbrtcpcontroller('span', CONTROLLER_IP, CONTROLLER_PORT)                              # Assing the ONOS controller to the new bridge
        span_id = 'of:' + ovs.getbrid('span')                                                       # Acquire the bridge's ID
        ovs.createveth('sp-span', 'sp-out')                                                         # Create the output veth interface
        ovs.addport('span', 'sp-span')                                                              # Assing the output interface to the bridge
        flow = {}                                                                                   # Create the flow rule
        flow['priority'] = 60000
        flow['timeout'] = 0
        flow['isPermanent'] = True
        flow['deviceId'] = span_id
        treatment = {}
        treatment['instructions'] = []
        treatment['instructions'].append({'type': 'OUTPUT', 'port': '1'})                           # This is the only port in the bridge
        flow['treatment'] = treatment
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json'
        }
        flow = json.dumps(flow)
        params = {'appid': 'org.onosproject.core'}
        uri = 'http://{0:s}:{1:d}/onos/v1/flows/{2:s}'.format(CONTROLLER_IP, REST_PORT, span_id)
        resp = requests.post(uri, data=flow, headers=headers, auth=rest_auth, params=params)        # Add the rule to the flow table
        print resp.text
        ecnt = 0
        for sw in switches:
            ovs.createveth(sw + '-span', 'sp-eth{0:d}'.format(ecnt))                                # Create a new veth to link the span bridge to every other existing bridge in the SDN
            ovs.addport(sw, sw + '-span')                                                           # Assing one end to the existing bridge
            ovs.addport('span', 'sp-eth{0:d}'.format(ecnt))                                         # Assing the other end to the output bridge
            ovs.createmirror(sw, sw + '-span', False)                                               # Create an openvswitch mirroring scheme in the existing bridge
            ecnt += 1
    except OSError:
        print 'SDN Mirroring requires root privileges'
        sys.exit(1)

def cleanup():
    '''Remove the mirroring scheme and return the SDN to its original state.'''
    try:
        ovs = VSCtl()                                                                                       # Initialize
        switch_id = ovs.getbrid('span')                                                                     # Acquire ID from the output bridge
        for sw in ovs.listbr():
            if ovs.hasmirror(sw):
                ovs.removemirror(sw)                                                                        # Remove openvswitch mirroring scheme from every bridge
                ovs.delport(sw, sw + '-span')                                                               # Remove outbound link between each bridge and the output bridge
        rest_auth = HTTPBasicAuth(REST_USER, REST_PASS)
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'curl/7.52.1'
        }
        uri = 'http://{0:s}:{1:d}/onos/v1/devices/of:{2:s}'.format(CONTROLLER_IP, REST_PORT, switch_id)
        ovs.delbr('span')                                                                                   # Destroy the output bridge
        ovs.destroyport('sp-out')                                                                           # Destroy the outbound veth
        for sw in ovs.listbr():
            ovs.destroyport(sw + '-span')                                                                   # Destroy every outbound veth in the existing bridges
        sres = {}
        while 'message' not in sres.keys():                                                                 # Due to the response time of ONOS, this can fail several times. Therefore, do it in a loop until it succeds.
            sleep(1)
            resp = requests.delete(uri, auth=rest_auth, headers=headers )                                   # Remove the output bridge from the ONOS inventory
            sres = resp.json()

    except OSError:
        print 'SDN Mirroring requires root privileges'
        sys.exit(1)

if __name__ == '__main__':
    '''CLI raw execution'''
    if len(sys.argv) != 2:
        print '''Usage: {0:s} m|c

m   Mirror
c   Cleanup
        '''.format(sys.argv[0])
        sys.exit(1)
    elif sys.argv[1] == 'm':
        mirror()
    elif sys.argv[1] == 'c':
        cleanup()
    else:
        print 'Unknown argument: ' + sys.argv[1]
        sys.exit(1)
