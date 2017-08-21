#!/usr/bin/env python
'''
Drive an OpenLCB link via TCP (native protocol)

@author: Stuart Baker - cleaned up and modernized
'''
import time
import array

import tcpolcblink
import mtiDefs
import defaults
import canolcbutils

## Mapping between an alias an a Node ID.
class AliasMap :
    ## Constructor.
    def __init__(self) :
        self.alias = None
        self.nodeID = None
        self.timestamp = 0

    ## Setup and alias/Node ID map.
    # @param alias alias to set
    # @param nodeID Node ID to set
    def setup(self, alias, nodeID) :
        self.alias = alias
        self.nodeID = nodeID
        if (self.alias == None or self.nodeID == None) :
            self.timestamp = 0
        else :
            self.timestamp = time.time()

    ## Get the alias/Node ID map
    # @return (alias, nodeID) alias that is mapped, Node ID that is mapped
    def get(self) :
        return self.alias, self.nodeID

    ## Get the timestamp of last use
    # @return timestamp of last use
    def timestamp(self) :
        return self.timestamp

    ## Update the timestamp
    def touch(self) :
        self.timestamp = time.time()

## Small cache of alias mappings
class AliasCache :
    ## Constructor.
    def __init__(self) :
        self.cache = []
        for x in range(16) :
            self.cache.append(AliasMap())

    ## Get the alias from a Node ID
    def alias_lookup(self, nodeID) :
        for x in self.cache :
            try_alias, try_node_id = x.get()
            if (try_node_id == nodeID) :
                return try_alias
        return 0

    ## purge alias from cache
    # @param alias alias to purge
    # @param nodeID Node ID to purge
    def alias_purge(self, alias) :
        for x in self.cache :
            try_alias, try_node_id = x.get()
            if (try_alias == alias) :
                x.setup(None, None)
                break

    ## purge Node ID from cache
    # @param alias alias to purge
    # @param nodeID Node ID to purge
    def node_id_purge(self, nodeID) :
        for x in self.cache :
            try_alias, try_node_id = x.get()
            if (try_node_id == nodeID) :
                x.setup(None, None)
                break

    ## cache an alias/Node ID mapping
    # @param alias alias to cache
    # @param nodeID Node ID to cache
    def cache(self, alias, nodeID) :
        oldest = 0
        oldest_time = time.time()
        for x in self.cache :
            x_timestamp = x.timestamp()
            if (x_timestamp < oldest_time) :
                oldest_time = x_timestamp
                oldest = x
        self.cache[x].setup(alias, nodeID)

class GenericToGC :
    def __init__(self) :
        self.aliasCache = AliasCache()
        self.aliasSource = AliasMap()
        self.rcvData = ""
        self.rcvIndex = 0
        self.verbose = True
        return

    ## Write raw data to the interface
    # @param string data to write
    def raw_write(self, string) :
        print string

    ## Read raw data from the interface
    # @param size size of data to try and read
    # @return data read
    def raw_read(self, size) :
        return ""

    ## Get the alias for the source Node ID, allocate it if necessary
    # @param source source Node ID
    def source_alias(self, source) :
        src_alias, src_nodeID = self.aliasSource.get()
        if (src_nodeID == source) :
            return src_alias

        alias = self.aliasCache.alias_lookup(source)
        if (alias != 0) :
            if (src_alias != None) :
                # must reset alias mappings
                raw_write(canolcbutils.makeframestring(0x10703000 + src_alias,
                                                       src_NodeID))
                self.aliasCache.alias_purge(src_alias)

            self.aliasSource.setup(alias, source)
            return alias

        # alias not found in any local storage
        for x in xrange(0x001, 0xFFE) :
            self.raw_write(canolcbutils.makeframestring(0x17000000 +
                                                   ((source[0] & 0xFF) << 16) +
                                                   ((source[1] & 0xF0) <<  8) +
                                                   x, 
                                                   None))
            self.raw_write(canolcbutils.makeframestring(0x16000000 +
                                                   ((source[1] & 0x0F) << 20) +
                                                   ((source[2] & 0xFF) << 12) +
                                                   x, 
                                                   None))
            self.raw_write(canolcbutils.makeframestring(0x15000000 +
                                                   ((source[3] & 0xFF) << 16) +
                                                   ((source[4] & 0xF0) <<  8) +
                                                   x, 
                                                   None))
            self.raw_write(canolcbutils.makeframestring(0x14000000 +
                                                   ((source[4] & 0x0F) << 20) +
                                                   ((source[5] & 0xFF) << 12) +
                                                   x, 
                                                   None))
            start = time.time()
            success = False;
            time.sleep(0.2)
            while (True) :
                result = None #self.receive()
                if (result == None) :
                    # no conflicts found
                    success = True
                    break
                elif (result[7:10] == str(x)) :
                    # conflict found
                    break

            if (success == True) :
                self.raw_write(canolcbutils.makeframestring(0x10700000 + x, 
                                                            None))
                self.raw_write(canolcbutils.makeframestring(0x10701000 + x, 
                                                            source))
                self.aliasSource.setup(x, source)
                return x
            
        assert False, "cannot allocate an alias"

    ## Get the alias for the destination Node ID
    # @param source Node ID making the lookup
    # @param dest destination Node ID we are looking up the alias for
    # @return destination alias, else 0 on error
    def dest_alias(self, souce, dest) :
        alias = aliasCache.lookup(dest)
        if (alias != 0) :
            return alias

        # try and find the node alias out on the bus
        src_alias = source_alias(source)
        self.raw_write(verifyNodeGlobal.makeframe(src_alias, dest))
        reply = expect(startswith=':X19170', data=dest, timeout=.3)
        if (reply != None) :
            alias = int(reply[7:10])
            aliasCache.cache(alias, dest)
            return alias

        assert False, "cannot find alias for Node ID"

    ## Add payload bytes to the string.  Pop the added bytes off the payload
    # @param string string to add payload bytes to
    # @param alias destination alias
    # @param payload list of payload data
    # @param size number of payload bytes to append
    # @return (string, payload) appended string, payload less appended items
    def append_payload(self, string, alias, flags, payload, size) :
        if (alias != None) :
            alias += flags << 12
            retval += hex(alias).upper()[2:]
        while (size) :
            string += ("00"+(hex(payload[0]).upper()[2:]))[-2:]
            payload.pop(0)
            size = size - 1;
        return string, payload

    ## Send message.
    # @param mti generic message MTI
    # @param source source Node ID
    # @param paylaod list of payload bytes
    # @param dest destination Node ID
    def send(self, mti, source, payload=None, dest=None) :
        src_alias = self.source_alias(source)
        flags = 0
        if (payload == None) :
            payload = []
        while (True) :
            string = ":X"
            if (mti <= 0x0FFF) :
                string += "19"
                string += ("000"+(hex(mti).upper()[2:]))[-3:]
            #else if (mti == MTI_DATAGRAM) :
            #else if (mti == MTI_STREAM_DATA_SEND) :
            else :
                assert False, "unknown message type"

            string += ("000"+(hex(src_alias).upper()[2:]))[-3:]
            string += "N"
            if (dest != None) :
                dst_alias = dest_alias(source, dest)
                size = 0
                if (flags == 0 and len(paylaod) > 6) :
                    # first
                    flags = 1
                    size = 6
                elif (flags == 1 or flags == 2) :
                    if (len(payload) > 6) :
                        # middle
                        flags = 2
                        size = 6
                    else :
                        # last
                        flags = 2
                        size = len(payload)
                else :
                    # only
                    size = len(payload)

                string, payload = self.append_payload(string, dst_alias, flags,
                                                      payload, size)
            else :
                if (payload != None) :
                    assert (len(payload) <= 8), "Broadcast payload to large"
                    string, payload = self.append_payload(string, None, 0,
                                                          payload, len(payload))

            string += ";"

            # if verbose, print
            if (self.verbose) :
                print "   send   ",string
        
            # send
            self.raw_write(string)
            if (len(payload) == 0 or dest == None) :
                return;
        
    # returns multiplet or None on error
    #    transmitter
    #    message (includes MTI)   
    def receive(self) : # returns frame
        if (self.rcvIndex >= len(self.rcvData)) :
            self.rcvIndex = 0
            self.rcvData = ""

        result = ""
        i = 0
        while (True) :
            if (len(self.rcvData) == 0) :
                # get more data
                try:
                    self.rcvData = self.raw_read(1024)
                    if (self.rcvData == None) :
                        return None
                    self.rcvIndex = 0
                except socket.timeout, err:
                    if (self.verbose) :
                        print "<none>" # blank line to show delay?
                    return None
            else :
                # parse our data
                while (True) :
                    if (self.rcvData[self.rcvIndex] == ':') :
                        result = ""
                        i = 0
                    result = result + self.rcvData[self.rcvIndex]
                    if (self.rcvData[self.rcvIndex] == ';') :
                        self.rcvIndex = self.rcvIndex + 1
                        # if verbose, print
                        if (self.verbose) :
                            print "   receive",result
                        return result
                    i = i + 1
                    self.rcvIndex = self.rcvIndex + 1
                    if (self.rcvIndex >= len(self.rcvData)) :
                        self.rcvIndex = 0
                        self.rcvData = ""
                        break
        # shouldn't reach here

    '''
    Continue receiving data until the we get the expected result or timeout.
    @param exact if != None, look for result with exact string
    @param startswith if != None, look for result starting with string
    @param data if != None, tuple of data bytes to match
    @param timeout timeout in seconds, if timeout != 0, return None on timeout
    @return resulting message on success, None on timeout
    '''
    def expect(self, exact=None, startswith=None, data=None, timeout=1) :
        start = time.time()
        while (True) :
            result = self.receive()
            if (data != None and result != None) :
                if (len(data) == ((len(result) - 12) / 2)) :
                    i = 0
                    j = 11
                    while (data[i] == int('0x' + result[j] + result[j + 1], 16)) :
                        i = i + 1
                        j = j + 2
                        if (i == len(data)) :
                            return result
            elif (exact != None) :
                if (result == exact) :
                    return result
            elif (startswith != None and result != None) :
                if (result.startswith(startswith)) :
                    return result
            elif (exact == None and startswith == None and data == None) :
                return result

            if (timeout != 0) :
                if (time.time() > (start + timeout)) :
                    if (self.verbose) :
                        print "Timeout"
                    return None

import sys
from optparse import OptionParser

def main():
    network = GenericToGC()
    network.send(mtiDefs.INITIALIZATION_COMPLETE, defaults.thisNodeID, defaults.thisNodeID)
    network.send(mtiDefs.IDENTIFY_EVENTS_GLOBAL, defaults.thisNodeID)
    global frame
    
    # create connection object
    network = tcpolcblink.TcpToOlcbLink()

    # get defaults
    host = network.host 
    port = network.port
    verbose = network.verbose
    
    frame = ':X182DF123N0203040506080001;'

    # process arguments
    (host, port, frame, verbose) = args(host, port, frame, verbose)
        
    # load new defaults
    network.host = host
    network.port = port
    network.verbose = verbose
    
    # send the frame
    network.send(frame)
    
    return  # done with example

def args(host, port, frame, verbose) :
    # argument processing
    usage = "usage: %prog [options] arg1\n\n" + \
            "Python module for connecting to an OpenLCB via a TCP native " + \
            "connection.\n" + \
            "Called standalone, will send one message frame.\n\n" + \
            "valid usages (default values):\n" + \
            "  ./tcpolcblink.py --ip=localhost\n" + \
            "  ./tcpolcblink.py --ip=localhost --port=12021\n" + \
            "  ./tcpolcblink.py --ip=localhost " + \
            "--port=12021 :X182DF123N0203040506080001\;" \

    parser = OptionParser(usage=usage)
    parser.add_option("-i", "--ip", dest="host", metavar="IP",
                      default="localhost",
                      help="host name or ip address")
    parser.add_option("-p", "--port", dest="port", metavar="PORT",
                      default=12021,
                      help="port number")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="print verbose debug information")

    (options, args) = parser.parse_args()

    if (len(args) > 0) :
        frame = args[0]

    return (options.host, options.port, frame, options.verbose)
    
if __name__ == '__main__':
    main()
    