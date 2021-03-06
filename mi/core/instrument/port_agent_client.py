#!/usr/bin/env python

"""
@package mi.core.instrument.port_agent_client
@file mi/core/instrument/port_agent_client
@author David Everett
@brief Client to connect to the port agent
and logging.
"""

__author__ = 'David Everett'
__license__ = 'Apache 2.0'

import socket
import errno
import threading
import time
import datetime
import struct
import array
import binascii
import ctypes

from mi.core.log import get_logger ; log = get_logger()
from mi.core.exceptions import InstrumentConnectionException

HEADER_SIZE = 16 # BBBBHHLL = 1 + 1 + 1 + 1 + 2 + 2 + 4 + 4 = 16


OFFSET_P_CHECKSUM_LOW = 6
OFFSET_P_CHECKSUM_HIGH = 7

"""
Offsets into the unpacked header fields
"""
SYNC_BYTE1_INDEX = 0
SYNC_BYTE1_INDEX = 1
SYNC_BYTE1_INDEX = 2
TYPE_INDEX = 3
LENGTH_INDEX = 4 # packet size (including header)
CHECKSUM_INDEX = 5
TIMESTAMP_UPPER_INDEX = 6
TIMESTAMP_LOWER_INDEX = 6

SYSTEM_EPOCH = datetime.date(*time.gmtime(0)[0:3])
NTP_EPOCH = datetime.date(1900, 1, 1)
NTP_DELTA = (SYSTEM_EPOCH - NTP_EPOCH).days * 24 * 3600


MAX_SEND_ATTEMPTS = 15              # Max number of times we can get EAGAIN

class PortAgentPacket():
    """
    An object that encapsulates the details packets that are sent to and
    received from the port agent.
    https://confluence.oceanobservatories.org/display/syseng/CIAD+MI+Port+Agent+Design
    """
    
    """
    Port Agent Packet Types
    """
    DATA_FROM_INSTRUMENT = 1
    DATA_FROM_DRIVER = 2
    PORT_AGENT_COMMAND = 3
    PORT_AGENT_STATUS = 4
    PORT_AGENT_FAULT = 5
    INSTRUMENT_COMMAND = 6
    HEARTBEAT = 7

    def __init__(self, packetType = None):
        self.__header = None
        self.__data = None
        self.__type = packetType
        self.__length = None
        self.__port_agent_timestamp = None
        self.__recv_checksum  = None
        self.__checksum = None
        self.__isValid = False

    def unpack_header(self, header):
        self.__header = header
        #@TODO may want to switch from big endian to network order '!' instead of '>' note network order is big endian.
        # B = unsigned char size 1 bytes
        # H = unsigned short size 2 bytes
        # L = unsigned long size 4 bytes
        # d = float size8 bytes
        variable_tuple = struct.unpack_from('>BBBBHHII', header)
        # change offset to index.
        self.__type = variable_tuple[TYPE_INDEX]
        self.__length = int(variable_tuple[LENGTH_INDEX]) - HEADER_SIZE
        self.__recv_checksum  = int(variable_tuple[CHECKSUM_INDEX])
        upper = variable_tuple[TIMESTAMP_UPPER_INDEX]
        lower = variable_tuple[TIMESTAMP_LOWER_INDEX]
        self.__port_agent_timestamp = float("%s.%s" % (upper, lower))

    def pack_header(self):
        """
        Given a type and length, pack a header to be sent to the port agent.
        """
        if self.__data == None:
            log.error('pack_header: no data!')
            """
            TODO: throw an exception here?
            """
        else:
            """
            Set the packet type if it was not passed in as parameter
            """
            if self.__type == None:
                self.__type = self.DATA_FROM_DRIVER
            self.__length = len(self.__data)
            self.__port_agent_timestamp = time.time() + NTP_DELTA


            variable_tuple = (0xa3, 0x9d, 0x7a, self.__type, 
                              self.__length + HEADER_SIZE, 0x0000, 
                              self.__port_agent_timestamp)

            # B = unsigned char size 1 bytes
            # H = unsigned short size 2 bytes
            # L = unsigned long size 4 bytes
            # d = float size 8 bytes
            format = '>BBBBHHd'
            size = struct.calcsize(format)
            temp_header = ctypes.create_string_buffer(size)
            struct.pack_into(format, temp_header, 0, *variable_tuple)
            self.__header = temp_header.raw
            #print "here it is: ", binascii.hexlify(self.__header)
            
            """
            do the checksum last, since the checksum needs to include the
            populated header fields.  
            NOTE: This method is only used for test; messages TO the port_agent
            do not include a header (as I mistakenly believed when I wrote
            this)
            """
            self.__checksum = self.calculate_checksum()
            self.__recv_checksum  = self.__checksum

            """
            This was causing a problem, and since it is not used for our tests,
            commented out; if we need it we'll have to fix
            """
            #self.__header[OFFSET_P_CHECKSUM_HIGH] = self.__checksum & 0x00ff
            #self.__header[OFFSET_P_CHECKSUM_LOW] = (self.__checksum & 0xff00) >> 8


    def attach_data(self, data):
        self.__data = data

    def attach_timestamp(self, timestamp):
        self.__port_agent_timestamp = timestamp

    def calculate_checksum(self):
        checksum = 0
        for i in range(HEADER_SIZE):
            if i < OFFSET_P_CHECKSUM_LOW or i > OFFSET_P_CHECKSUM_HIGH:
                checksum += struct.unpack_from('B', str(self.__header[i]))[0]
                
        for i in range(self.__length):
            checksum += struct.unpack_from('B', str(self.__data[i]))[0]
            
        return checksum
            
                                
    def verify_checksum(self):
        checksum = 0
        for i in range(HEADER_SIZE):
            if i < OFFSET_P_CHECKSUM_LOW or i > OFFSET_P_CHECKSUM_HIGH:
                checksum += struct.unpack_from('B', self.__header[i])[0]
                
        for i in range(self.__length):
            checksum += struct.unpack_from('B', self.__data[i])[0]
            
        if checksum == self.__recv_checksum:
            self.__isValid = True
        else:
            self.__isValid = False
            
        #log.debug('checksum: %i.' %(checksum))

    def get_data_size(self):
        return self.__length
    
    def get_header(self):
        return self.__header

    def get_data(self):
        return self.__data

    def get_timestamp(self):
        return self.__port_agent_timestamp

    def get_header_length(self):
        return self.__length

    def get_header_type(self):
        return self.__type

    def get_header_checksum(self):
        return self.__checksum

    def get_header_recv_checksum (self):
        return self.__recv_checksum

    def get_as_dict(self):
        """
        Return a dictionary representation of a port agent packet
        """
        return {
            'type': self.__type,
            'length': self.__length,
            'checksum': self.__checksum,
            'raw': self.__data
        }

    def is_valid(self):
        return self.__isValid
                    

class PortAgentClient(object):
    """
    A port agent process client class to abstract the TCP interface to the 
    of port agent. From the instrument driver's perspective, data is sent 
    to the port agent with this client's send method, and data is received 
    asynchronously via a callback from this client's listener thread.
    """
    
    """
    NOTE!!! MAX_RECOVERY_ATTEMPTS must not be greater than 1; if we decide
    in the future to make it greater than 1, we need to test the 
    error_callback, because it will be able to be re-entered.
    """
    MAX_RECOVERY_ATTEMPTS = 1  # !! MUST BE 1 and ONLY 1 (see above comment) !!
    RECOVERY_SLEEP_TIME = 2
    HEARTBEAT_INTERVAL_COMMAND = "heartbeat_interval "
    BREAK_COMMAND = "break"
    
    def __init__(self, host, port, cmd_port, delim=None):
        """
        Logger client constructor.
        """
        self.host = host
        self.port = port
        self.cmd_port = cmd_port
        self.sock = None
        self.listener_thread = None
        self.stop_event = None
        self.delim = delim
        self.heartbeat = 0
        self.max_missed_heartbeats = None
        self.send_attempts = MAX_SEND_ATTEMPTS
        self.recovery_attempts = 0
        self.user_callback_data = None
        self.user_callback_raw = None
        self.user_callback_error = None
        self.recovery_mutex = threading.Lock()
        self.recovery_attempts = 0
        
    def init_comms(self, user_callback_data = None, user_callback_raw = None, 
                   user_callback_error = None, heartbeat = 0, 
                   max_missed_heartbeats = None):
        """
        Initialize client comms with the logger process and start a
        listener thread.
        """
        self.user_callback_data = user_callback_data        
        self.user_callback_raw = user_callback_raw        
        self.user_callback_error = user_callback_error
        self.heartbeat = heartbeat
        self.max_missed_heartbeats = max_missed_heartbeats        

        try:
            self.destroy_connection()
            self.create_connection()

            heartbeat_string = str(heartbeat)
            self.send_config_parameter(self.HEARTBEAT_INTERVAL_COMMAND, 
                                       heartbeat_string)
            self.listener_thread = Listener(self.sock, self.delim, 
                                            heartbeat, max_missed_heartbeats, 
                                            self.callback_data,
                                            self.callback_raw, 
                                            self.callback_error)
            self.listener_thread.start()
            log.info('PortAgentClient.init_comms(): connected to port agent at %s:%i.'
                           % (self.host, self.port))        
        except Exception as e:
            errorString = "init_comms(): Exception initializing comms for " +  \
                      str(self.host) + ": " + str(self.port) + ": " + repr(e)
            log.error(errorString, exc_info=True)
            time.sleep(self.RECOVERY_SLEEP_TIME)
            self.callback_error(errorString)

    def create_connection(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.setblocking(0)

    def destroy_connection(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            log.info('Port agent data socket closed.')
                        
    def stop_comms(self):
        """
        Stop the listener thread and close client comms with the device
        logger. This is called by the done function.
        """
        log.info('Logger shutting down comms.')
        self.listener_thread.done()
        self.listener_thread.join()
        #-self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        self.sock = None
        log.info('Port Agent Client stopped.')

    def done(self):
        """
        Synonym for stop_comms.
        """
        self.stop_comms()

    def callback_data(self, paPacket):
        """
        A packet has been received from the port agent.  The packet is 
        contained in a packet object.  
        """
        if (self.user_callback_data):
            paPacket.verify_checksum()
            self.user_callback_data(paPacket)
        else:
            log.error("No user_callback_data defined")

    def callback_raw(self, paPacket):
        """
        A packet has been received from the port agent.  The packet is 
        contained in a packet object.  
        """
        if (self.user_callback_raw):
            paPacket.verify_checksum()
            self.user_callback_raw(paPacket)
        else:
            log.error("No user_callback_raw defined")

    def callback_error(self, errorString = "No error string passed."):
        """
        A catastrophic error has occurred; attempt to recover, and if that fails,
        call back into the instrument driver.
        """
        returnValue = False
        
        self.recovery_mutex.acquire()

        if (self.recovery_attempts >= self.MAX_RECOVERY_ATTEMPTS):
            """
            Release the mutex here.  The other thread can notice an error and
            we will have not released the semaphore, and the thread will hang.  
            The fact that we've incremented the MAX_RECOVERY_ATTEMPTS will
            stop any re-entry.

            """        
            self.recovery_mutex.release()
            if (self.user_callback_error):
                log.error("Maximum connection_level recovery attempts (%d) reached." % (self.recovery_attempts))
                self.user_callback_error(errorString)
                returnValue = True
            else:
                log.error("No user_callback_data defined")
                if self.listener_thread and self.listener_thread.is_alive():
                    self.listener_thread.done()
                returnValue = False
        else:
            """
            Try calling init_comms() again;
            release the mutex before calling init_comms, which can cause
            another exception, and we will have not released the semaphore.  
            The fact that we've incremented the MAX_RECOVERY_ATTEMPTS will
            stop any re-entry.
            """
            self.recovery_attempts = self.recovery_attempts + 1
            log.error("Attempting connection_level recovery; attempt number %d" % (self.recovery_attempts))
            self.recovery_mutex.release()
            self.init_comms(self.user_callback_data, self.user_callback_raw, 
                            self.user_callback_error, self.heartbeat, 
                            self.max_missed_heartbeats)
            returnValue = True
            
        return returnValue
            
    def send_config_parameter(self, parameter, value):
        """
        Send a configuration parameter to the port agent
        """
        command = parameter + value
        log.debug("Sending config parameter: %s" % (command))
        self._command_port_agent(command)

    def send_break(self):
        """
        Command the port agent to send a break
        """
        self._command_port_agent(self.BREAK_COMMAND)

    def _command_port_agent(self, cmd):
        """
        Command the port agent.  We connect to the command port, send the command
        and then disconnect.  Connection is not persistent
        @raise InstrumentConnectionException if cmd_port is missing.  We don't
                        currently do this on init  where is should happen because
                        some instruments wont set the  command port quite yet.
        """
        try:
            if(not self.cmd_port):
                raise InstrumentConnectionException("Missing port agent command port config")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.cmd_port))
            log.info('PortAgentClient._command_port_agent(): connected to port agent at %s:%i.'
                     % (self.host, self.cmd_port))
            self.send(cmd, sock) 
            sock.close()
        except Exception as e:
            log.error("send_break(): Exception occurred.", exc_info=True)
            raise InstrumentConnectionException('Failed to connect to port agent command port at %s:%s (%s).'
                                                % (self.host, self.cmd_port, e))


    def send(self, data, sock = None):
        """
        Send data to the port agent.
        """
        returnValue = 0
        total_bytes_sent = 0
        
        """
        The socket can be a parameter (in case we need to send to the command
        port, for instance); if not provided, default to self.sock which 
        should be the data port.
        """
        if (not sock):
            sock = self.sock

        if sock:
            would_block_tries = 0
            continuing = True
            while len(data) > 0 and continuing:
                try:
                    sent = sock.send(data)
                    total_bytes_sent = len(data[:sent])
                    data = data[sent:]
                except socket.error as e:
                    if e.errno == errno.EWOULDBLOCK:
                        would_block_tries = would_block_tries + 1
                        if would_block_tries > self.send_attempts:
                            """
                            TODO: Remove the commented out lines that print self.host and self.port after verifying that getpeername works
                            (self.host and self.port aren't necessarily correct; the sock is a parameter here and host and port might not
                            be correct).
                            """
                            #error_string = 'Send EWOULDBLOCK attempts (%d) exceeded while sending to %s:%i'  % (would_block_tries, self.host, self.port)
                            error_string = 'Send EWOULDBLOCK attempts (%d) exceeded while sending to %r'  % (would_block_tries, sock.getpeername())
                            log.error(error_string)
                            self.callback_error(error_string)
                            continuing = False 
                        else:
                            #error_string = 'Socket error while sending to (%s:%i): %r; tries = %d'  % (self.host, self.port, e, would_block_tries)
                            error_string = 'Socket error while sending to %r: %r; tries = %d'  % (sock.getpeername(), e, would_block_tries)
                            log.error(error_string)
                            time.sleep(.1)
                    else:
                        #error_string = 'Socket error while sending to (%s:%i): %r'  % (self.host, self.port, e)
                        error_string = 'Socket error while sending to %r: %r'  % (sock.getpeername(), e)
                        log.error(error_string)
                        self.callback_error(error_string)
                        continuing = False
        else:
            error_string = 'No socket defined!'
            log.error(error_string)
            self.callback_error(error_string)
        
        return total_bytes_sent
            
class Listener(threading.Thread):

    MAX_HEARTBEAT_INTERVAL = 20 # Max, for range checking parameter
    MAX_MISSED_HEARTBEATS = 5   # Max number we can miss 
    HEARTBEAT_FUDGE = 1         # Fudge factor to account for delayed heartbeat

    """
    A listener thread to monitor the client socket data incoming from
    the port agent process. 
    """
    
    def __init__(self, sock, delim = None, heartbeat = 0, 
                 max_missed_heartbeats = None, 
                 callback_data = None, callback_raw = None, 
                 callback_error = None):
        """
        Listener thread constructor.
        @param sock The socket to listen on.
        @param delim The line delimiter to split incoming lines on, used in
        debugging when no callback is supplied.
        @param callback The callback on data arrival.
        """
        threading.Thread.__init__(self)
        self.sock = sock
        self._done = False
        self.linebuf = ''
        self.delim = delim
        self.heartbeat_timer = None
        if (max_missed_heartbeats == None):
            self.max_missed_heartbeats = self.MAX_MISSED_HEARTBEATS
        else:
            self.max_missed_heartbeats = max_missed_heartbeats
        self.heartbeat_missed_count = self.max_missed_heartbeats
        
        self.set_heartbeat(heartbeat)
        
        def fn_callback_data(paPacket):
            if callback_data:
                callback_data(paPacket)
            else:
                log.error("No callback_data function has been registered")            

        def fn_callback_raw(paPacket):
            if callback_raw:
                callback_raw(paPacket)
            else:
                log.error("No callback_raw function has been registered")            
                            
        def fn_callback_error(errorString = "No error string passed."):
            """
            Error callback; try our own recovery first; if this gets called
            again, we call the callback_error
            """
            log.error("Connection error: %s" % (errorString))
            
            if callback_error:
                callback_error(errorString)
            else:
                log.error("No callback_raw function has been registered")            

        """
        Now that the callbacks have have been defined, assign them
        """                
        self.callback_data = fn_callback_data
        self.callback_raw = fn_callback_raw
        self.callback_error = fn_callback_error

    def heartbeat_timeout(self):
        log.error('heartbeat timeout')
        self.heartbeat_missed_count = self.heartbeat_missed_count - 1
    
        """
        Take corrective action here.
        """
        if self.heartbeat_missed_count <= 0:
            errorString = 'Maximum allowable Port Agent heartbeats (' + str(self.max_missed_heartbeats) + ') missed!'
            log.error(errorString)
            self.callback_error(errorString)
        else:
            self.start_heartbeat_timer()

    def set_heartbeat(self, heartbeat):
        """
        Make sure the heartbeat is reasonable; if so, initialize the class 
        member heartbeat (plus fudge factor) to greater than the value passed 
        in.  This is to account for possible delays in the heartbeat packet 
        from the port_agent.
        """
        if heartbeat == 0:
            self.heartbeat = heartbeat
            returnValue = True
        elif heartbeat > 0 and heartbeat <= self.MAX_HEARTBEAT_INTERVAL: 
            self.heartbeat = heartbeat + self.HEARTBEAT_FUDGE;
            returnValue = True
        else:
            log.error('heartbeat out of range: %d' % (heartbeat))
            returnValue = False
            
        return returnValue
        
    def start_heartbeat_timer(self):
        """
        Note: the threading timer here is only run once.  The cancel
        only applies if the function has yet run.  You can't reset
        it and start it again, you have to instantiate a new one.
        I don't like this; we need to implement a tread timer that 
        stays up and can be reset and started many times.
        """
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()

        self.heartbeat_timer = threading.Timer(self.heartbeat, 
                                            self.heartbeat_timeout)
        self.heartbeat_timer.start()
        
    def done(self):
        """
        Signal to the listener thread to end its processing loop and
        conclude.
        """
        self._done = True

    def handle_packet(self, paPacket):
        packet_type = paPacket.get_header_type()
        
        if packet_type == PortAgentPacket.DATA_FROM_INSTRUMENT:
            self.callback_raw(paPacket)
            self.callback_data(paPacket)
        elif packet_type == PortAgentPacket.DATA_FROM_DRIVER:
            self.callback_raw(paPacket)
        elif packet_type == PortAgentPacket.PORT_AGENT_COMMAND:
            self.callback_raw(paPacket)
        elif packet_type == PortAgentPacket.PORT_AGENT_STATUS:
            self.callback_raw(paPacket)
        elif packet_type == PortAgentPacket.PORT_AGENT_FAULT:
            self.callback_raw(paPacket)
        elif packet_type == PortAgentPacket.INSTRUMENT_COMMAND:
            self.callback_raw(paPacket)
        elif packet_type == PortAgentPacket.HEARTBEAT:
            """
            Got a heartbeat; reset the timer and re-init 
            heartbeat_missed_count.
            """
            if self.heartbeat:
                self.start_heartbeat_timer()
                
            self.heartbeat_missed_count = self.max_missed_heartbeats
            
                
    def run(self):
        """
        Listener thread processing loop. Block on receive from port agent.
        Receive HEADER_SIZE bytes to receive the entire header.  From that,
        get the length of the whole packet (including header); compute the
        length of the remaining data and read that.  
        NOTE (DHE): I've noticed in my testing that if my test server
        (simulating the port agent) goes away, the client socket (ours)
        goes into a CLOSE_WAIT condition and stays there for a long time. 
        When that happens, this method loops furiously and for a long time. 
        I have not had the patience to wait it out, so I don't know how long
        it will last.  When it happens though, 0 bytes are received, which
        should never happen unless something is wrong.  So if that happens,
        I'm considering it an error.
        """
        log.info('Logger client listener started.')
        if self.heartbeat:
            self.start_heartbeat_timer()

        while not self._done:
            try:
                received_header = False
                bytes_left = HEADER_SIZE
                while not received_header and not self._done: 
                    header = self.sock.recv(bytes_left)
                    bytes_left -= len(header)
                    if bytes_left == 0:
                        received_header = True
                        paPacket = PortAgentPacket()         
                        paPacket.unpack_header(header)         
                        data_size = paPacket.get_data_size()
                        bytes_left = data_size
                    elif len(header) == 0:
                        errorString = 'Zero bytes received from port_agent socket'
                        log.error(errorString)
                        self.callback_error(errorString)
                        """
                        This next statement causes the thread to exit.
                        """
                        self._done = True
                
                received_data = False
                while not received_data and not self._done: 
                    data = self.sock.recv(bytes_left)
                    bytes_left -= len(data)
                    if bytes_left == 0:
                        received_data = True
                        paPacket.attach_data(data)
                    elif len(data) == 0:
                        errorString = 'Zero bytes received from port_agent socket'
                        log.error(errorString)
                        self.callback_error(errorString)
                        """
                        This next statement causes the thread to exit.
                        """
                        self._done = True

                if not self._done:
                    """
                    Should have complete port agent packet.
                    """
                    self.handle_packet(paPacket)

            except socket.error as e:
                if e.errno == errno.EWOULDBLOCK:
                    time.sleep(.1)
                else:
                    errorString = 'Socket error while receiving from port agent: %r'  % (e)
                    log.error(errorString)
                    self.callback_error(errorString)
                    self._done = True


        log.info('Port_agent_client thread done listening; going away.')

