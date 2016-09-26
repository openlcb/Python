#!/usr/bin/env python
'''
Drive an OpenLCB link via TCP (native protocol)

argparse is new in Jython 2.7, so dont use here

@author: Bob Jacobsen
'''
import socket
import time

import tcpolcbutils

class TcpToOlcbLink :
    def __init__(self) :
        # prepare, but don't open
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.socket.timeout(10)
        
        # defaults (generally overridden by system-wide defaults elsewhere)
        self.host = "172.168.1.10" # Arduino adapter default
        self.port = 12021
        self.timeout = 1.0
        self.verbose = True
        self.startdelay = 0
        self.socket = None
        self.rcvData = ""
        self.rcvIndex = 0
        return
    
    def connect(self) :
        # if verbose, print
        if (self.verbose) : print "   connect to ",self.host,":",self.port
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        
        # wait for link startup
        # after (possible) reset due to serial startup
        if self.startdelay > 0 :
            if self.verbose : print "   waiting", self.startdelay, "seconds for adapter restart"
            time.sleep(self.startdelay)

        return
        
    def send(self, string) :
        if (self.socket == None) : self.connect()
        
        # if verbose, print
        if (self.verbose) :
            print "   send   ",string
    
        # send
        self.socket.send(string)
        
        return
        
    # returns multiplet or None on error
    #    transmitter
    #    message (includes MTI)   
    def receive(self) : # returns frame
        if (self.socket == None) : self.connect()
        
        self.socket.settimeout(self.timeout)

        if (self.rcvIndex >= len(self.rcvData)) :
            self.rcvIndex = 0
            self.rcvData = ""

        result = ""
        i = 0
        while (True) :
            if (len(self.rcvData) == 0) :
                # get more data
                try:
                    self.rcvData = self.socket.recv(1024)
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
        
    def close(self) :
        return


import getopt, sys

def main():
    global frame
    
    # create connection object
    network = TcpToOlcbLink()

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

def usage() :
    print ""
    print "Python module for connecting to an OpenLCB via an Tcp native connection."
    print "Called standalone, will send one message frame."
    print ""
    print "valid options:"
    print "  -v for verbose; also displays any responses"
    print "  -h, --host for host name or IP address"
    print "  -p, --port for port number"
    print ""
    print "valid usages (default values):"
    print "  ./etcpolcblink.py --host=10.00.01.98"
    print "  ./tcpolcblink.py --host=10.00.01.98 --port=23"
    print "  ./tcpolcblink.py --host=10.00.01.98 --port=23 :X182DF123N0203040506080001\;"
    print ""
    
def args(host, port, frame, verbose) :
    # argument processing
    try:
        opts, remainder = getopt.getopt(sys.argv[1:], "h:p:v", ["host=", "port="])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-v":
            verbose = True
        elif opt in ("-h", "--host"):
            host = arg
        elif opt in ("-p", "--port"):
            port = int(arg)
        else:
            assert False, "unhandled option"
    if (len(remainder) > 0) : 
        frame = remainder[0]
    return (host, port, frame, verbose)
    
if __name__ == '__main__':
    main()
    
