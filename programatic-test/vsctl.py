#!/usr/bin/env python2
'''ovs-vsctl python 2 wrapper for ovs-vswitchd.

This wrapper handle some of the basic functions provided by ovs-vsctl involving
openvswitch bridge management, port management and traffic mirroring.

The main purpose of this module is to provide the capabilities for a simple SDN
management using python.'''

import os
import errno
from subprocess import Popen, PIPE
from re import match

IPREGEX = r'^(?:(?:2(?:5[0-5]|[0-4]\d)|1\d\d|[1-9]?\d)[.]){3}(?:2(?:5[0-5]|[0-4]\d)|1\d\d|[1-9]?\d)$'

class VSCtl():

    def __init__(self, fmt=None):
        if os.geteuid() != 0:
            raise OSError('[Errno {0:d}] This class requires root privileges'.format(errno.EPERM))
        else:
            if fmt is not None:
                self.fmt = fmt
            else:
                self.fmt = 'list'
            popen = Popen(['ovs-vsctl', 'init'], stdout=PIPE)
            popen.wait()

    def __run(self, args):
        '''Run a given vsctl command.
        
        Keyword arguments:
        args -- list of arguments to pass on to ovs-vsctl.'''
        popen = Popen(['ovs-vsctl', '-f', self.fmt] + args, stdout=PIPE, stderr=PIPE)
        sout, serr = popen.communicate()
        return (popen.returncode, sout, serr)
    
    # Bridge commands
    def listbr(self):
        '''List existing openvswitch bridges.'''
        res = self.__run(['list-br'])
        res = res[1].split('\n')[0:-1]
        return res

    def addbr(self, bridge=None):
        '''Create a new openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} already exists'.format(errno.EFAULT, bridge))
        else:
            res = self.__run(['add-br', bridge])
            return res[0]
    
    def delbr(self, bridge=None):
        '''Delete an existing openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        else:
            res = self.__run(['del-br', bridge])
            return res[0]
    
    def getbrid(self, bridge=None):
        '''Get the datapath ID of a specific bridge. This ID is also used for OpenFlow communications.
        
        Keyword arguments:
        bridge -- The local name of the bridge (default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        else:
            res = self.__run(['get', 'Bridge', bridge, 'datapath_id'])
            res = res[1].split('\n')[0]
            res = res[1:-1]
            return res
    
    def setbrtcpcontroller(self, bridge=None, ipaddr=None, port=None):
        '''Assign an OpenFlow controller to a given openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (default None)
        ipaddr -- The IP address of the controller (default None)
        port   -- The port number to connect to (default None)'''
        if ipaddr is None or port is None:
            raise ValueError('[Errno {0:d}] neither ipaddr nor port can be None'.format(errno.EINVAL))
        elif type(ipaddr) is not str:
            raise TypeError('[Errno {0:d}] ipaddr must be a string'.format(errno.EINVAL))
        elif type(port) is not int:
            raise TypeError('[Errno {0:d}] port must be an integer'.format(errno.EINVAL))
        elif match(IPREGEX, ipaddr) is None:
            raise ValueError('[Errno {0:d}] ipaddr must be an IPv4 address'.format(errno.EINVAL))
        elif port < 1 or port > 65535:
            raise ValueError('[Errno {0:d}] port must be a valid IP port number (1-65535)'.format(errno.EINVAL))
        elif bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        else:
            res = self.__run(['set-controller', bridge, 'tcp:{0:s}:{1:d}'.format(ipaddr, port)])
            return res[0]
    
    def delbrcontroller(self, bridge=None):
        '''Remove the current controller from an openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        else:
            res = self.__run(['del-controller', bridge])
            return res[0]
    
    # Port commands
    def createveth(self, port1=None, port2=None):
        '''Create a new pair of virtual ethernet devices.
        
        Virtual ethernet devices act as tunnels between network namespaces. veth devices are always
        created in interconnected pairs, such that packets transmitted on one device in the pair are
        immediately received on the other device.
        
        Keyword arguments:
        port1 -- Name of the first veth device (default None)
        port2 -- Name of the second veth device (default None)'''
        if port1 is None or port2 is None:
            raise ValueError('[Errno {0:d}] ports cannot be None'.format(errno.EINVAL))
        elif type(port1) is not str or type(port2) is not str:
            raise TypeError('[Errno {0:d}] both ports must be strings'.format(errno.EINVAL))
        elif self.portexists(port1):
            raise ValueError('[Errno {0:d}] port {1:s} already exists'.format(errno.EINVAL, port1))
        elif self.portexists(port2):
            raise ValueError('[Errno {0:d}] port {1:s} already exists'.format(errno.EINVAL, port2))
        else:
            res = os.system('ip link add {0:s} type veth peer name {1:s} >/dev/null 2>&1'.format(port1, port2))
            res += os.system('ip link set {0:s} up >/dev/null 2>&1'.format(port1))
            res += os.system('ip link set {0:s} up >/dev/null 2>&1'.format(port2))
            return res
    
    def destroyport(self, port=None):
        '''Destroy an existing virtual ethernet device.
        
        This effectively destroys the pair of devices conforming the veth.
        
        Keyword arguments:
        port -- The name of either veth device in the pair (Default None)'''
        if port is None:
            raise ValueError('[Errno {0:d}] port cannot be None'.format(errno.EINVAL))
        elif type(port) is not str:
            raise TypeError('[Errno {0:d}] port must be a string'.format(errno.EINVAL))
        elif self.isportassigned(port):
            raise RuntimeError('[Errno {0:d}] port {1:s} is currently assigned to a bridge'.format(errno.EBUSY, port))
        elif not self.portexists(port):
            raise ValueError('[Errno {0:d}] port {1:s} does not exist'.format(errno.ENODEV, port))
        else:
            res = os.system('ip link del {0:s} >/dev/null 2>&1'.format(port))
            return res
    
    def portexists(self, port=None):
        '''Check whether a given veth exists in the current state.
        
        Keyword arguments:
        port -- The name of the device (Default None)'''
        if port is None:
            raise ValueError('[Errno {0:d}] port cannot be None'.format(errno.EINVAL))
        elif type(port) is not str:
            raise TypeError('[Errno {0:d}] port must be a string'.format(errno.EINVAL))
        else:
            res = os.system('ip link show {0:s} >/dev/null 2>&1'.format(port))
            if res != 0:
                return False
            else:
                return True

    def listports(self, bridge=None):
        '''List the existing ports on an openvswitch bridge
        
        Keyword arguments:
        bridge -- The local name of the bridge (default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        else:
            res = self.__run(['list-ports', bridge])
            res = res[1].split('\n')[0:-1]
            return res

    def isportassigned(self, port=None):
        '''Check whether or not a given port has been assigned to any existing
        openvswitch bridge.
        
        Keyword arguments:
        port -- The veth device to check (Default None)'''
        if port is None:
            raise ValueError('[Errno {0:d}] port cannot be None'.format(errno.EINVAL))
        elif type(port) is not str:
            raise TypeError('[Errno {0:d}] port must be a string'.format(errno.EINVAL))
        elif not self.portexists(port):
            raise ValueError('[Errno {0:d}] port {1:s} does not exist'.format(errno.ENODEV, port))
        else:
            for br in self.listbr():
                if port in self.listports(br):
                    return True
            return False

    def islinktoswitch(self, port=None):
        '''Check whether or not a given veth has both devices assigned to different
        openvswitch bridges.
        
        Keyword arguments:
        port -- The name of the veth device to check (Default None)'''
        if port is None:
            raise ValueError('[Errno {0:d}] port cannot be None'.format(errno.EINVAL))
        elif type(port) is not str:
            raise TypeError('[Errno {0:d}] port must be a string'.format(errno.EINVAL))
        elif not self.portexists(port):
            raise ValueError('[Errno {0:d}] port {1:s} does not exist'.format(errno.ENODEV, port))
        else:
            popen = Popen(['ip', 'link', 'show', port], stdout=PIPE, stderr=PIPE)
            sout = popen.communicate()
            sout = sout[0]
            sout = sout.split('\n')[0]
            sout = sout.split(' ')[1][:-1]
            if '@' not in sout:
                raise ValueError('[Errno {0:d}] port {1:s} is not a veth'.format(errno.EINVAL, port))
            else:
                sout = sout.split('@')[1]
                sout = sout.split('-')[0]
                return sout in self.listbr()

    def addport(self, bridge=None, port=None):
        '''Assign an unassigned veth to an existing openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (Default None)
        port   -- The veth device to be assigned (Default None)'''
        if bridge is None or port is None:
            raise ValueError('[Errno {0:d}] neither bridge nor port can be None'.format(errno.EINVAL))
        elif type(bridge) is not str or type(port) is not str:
            raise TypeError('[Errno {0:d}] both bridge and port must be strings'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        elif port in self.listports(bridge):
            raise ValueError('[Errno {0:d}] port {1:s} has already been assigned to bridge {2:s}'.format(errno.ENODEV, port, bridge))
        elif self.isportassigned(port):
            raise RuntimeError('[Errno {0:d}] port {1:s} has already been assigned to another bridge'.format(errno.EBUSY, port))
        elif not self.portexists(port):
            raise ValueError('[Errno {0:d}] port {1:s} does not exist'.format(errno.ENODEV, port))
        else:
            res = self.__run(['add-port', bridge, port])
            return res[0]

    def delport(self, bridge=None, port=None):
        '''Remove a veth device from a given openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (Default None)
        port   -- The veth device to be removed (Default None)'''
        if bridge is None or port is None:
            raise ValueError('[Errno {0:d}] neither bridge nor port can be None'.format(errno.EINVAL))
        elif type(bridge) is not str or type(port) is not str:
            raise TypeError('[Errno {0:d}] both bridge and port must be strings'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        elif port not in self.listports(bridge):
            raise ValueError('[Errno {0:d}] port {1:s} is not currently assigned to bridge {2:s}'.format(errno.ENODEV, port, bridge))
        else:
            res = self.__run(['del-port', bridge, port])
            return res[0]

    # Mirroring commands
    def hasmirror(self, bridge=None):
        '''Check whether or not a given openvswitch bridge has a configured mirroring scheme.
        
        Keyword arguments:
        bridge -- The local name of the bridge (Default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        else:
            res = self.__run(['get', 'Bridge', bridge, 'mirrors'])
            res = res[1].split('\n')[0]
            return res != '[]'

    def createmirror(self, bridge=None, span=None, sall=False):
        '''Create a new mirroring scheme within an openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (Default None).
        span   -- The veth name of the device in which all the traffic will be mirrored (Default None).
        sall   -- Boolean indicating whether all the ports should be mirrored, or only those in which hosts are connected. (Default False).'''
        if bridge is None or span is None:
            raise ValueError('[Errno {0:d}] neither bridge nor span can be None'.format(errno.EINVAL))
        elif type(bridge) is not str or type(span) is not str:
            raise TypeError('[Errno {0:d}] both bridge and span must be strings'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        elif span not in self.listports(bridge):
            raise ValueError('[Errno {0:d}] chosen span port {1:s} is not currently assigned to bridge {2:s}'.format(errno.ENODEV, span, bridge))
        elif self.hasmirror(bridge):
            raise RuntimeError('[Errno {0:d}] bridge {1:s} already has a mirror'.format(errno.EBUSY, bridge))
        elif type(sall) is not bool:
            raise TypeError('[Errno {0:d}] sall must be a boolean'.format(errno.EINVAL))
        else:
            cmd_args = []
            mname = 'name=' + bridge + 'm'
            if not sall:
                swports = self.listports(bridge=bridge)
                pcnt = 0
                pids = ''
                for p in swports:
                    if p != span and not self.islinktoswitch(p):
                        prid = '@sp{0:d}'.format(pcnt)
                        pids += prid + ','
                        cmd_args += ['--', '--id=' + prid, 'get', 'Port', p]
                        pcnt += 1
                pids = pids[:-1]
                cmd_args += ['--', '--id=@p', 'get', 'Port', span]
                selectp = 'select-src-port=' + pids
                cmd_args += ['--', '--id=@m', 'create', 'Mirror', mname, 'select-all=false', selectp, 'output-port=@p']
            else:
                cmd_args += ['--', '--id=@p', 'get', 'Port', span]
                cmd_args += ['--', '--id=@m', 'create', 'Mirror', mname, 'select-all=true', 'output-port=@p']
            cmd_args += ['--', 'set', 'Bridge', bridge, 'mirrors=@m']
            res = self.__run(cmd_args)
            return res[0]

    def removemirror(self, bridge=None):
        '''Remove the mirroring scheme from a given openvswitch bridge.
        
        Keyword arguments:
        bridge -- The local name of the bridge (Default None)'''
        if bridge is None:
            raise ValueError('[Errno {0:d}] bridge cannot be None'.format(errno.EINVAL))
        elif type(bridge) is not str:
            raise TypeError('[Errno {0:d}] bridge must be a string'.format(errno.EINVAL))
        elif bridge not in self.listbr():
            raise ValueError('[Errno {0:d}] bridge {1:s} does not exist'.format(errno.ENODEV, bridge))
        elif not self.hasmirror(bridge):
            raise RuntimeError('[Errno {0:d}] bridge {1:s} does not have a mirror'.format(errno.ENODEV, bridge))
        else:
            mname = bridge + 'm'
            cmd_args = ['--', '--id=@m', 'get', 'Mirror', mname]
            cmd_args += ['--', 'remove', 'Bridge', bridge, 'mirrors', '@m']
            res = self.__run(cmd_args)
            return res[0]

    def raw(self, args):
        '''Execute ovs-vsctl with the given arguments. [NOT RECOMMENDED]
        
        Keyword arguments:
        args -- list of arguments to pass on to ovs-vsctl.'''
        if type(args) is not list:
            raise TypeError('[Errno {0:d}] args must be a list'.format(errno.EINVAL))
        else:
            res = self.__run(args)
            return res

    
