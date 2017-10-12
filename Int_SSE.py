#!/usr/bin/python2.7
# -*- coding: UTF-8 -*-# enable debugging

# Rick Faszold
# XEn, Inc
# October 11th, 2017
# This program can only be used with permission from XEn, LLC.  Missouri, USA  (c)
#
# This Python script accepts fully formatted JSON messages from a server and
# immediately streams that data to a browser.  The browser uses a few lines of
# .js to place that data into theie correct locations.  Like this .py script, the .js
# in the browser is kept to a minimum in order to ensure greater performance.
#
# There are two UDP connections that handle server side communications
#    Com Channel - This establishes communications with the server 
#		The IP/Port of the server is stored in a config file located in the .py cgi dir
#               Once a connection is established, this handles the initial handshake
#               .py -> HELLO
#               Server => HIYA,xxxxx   (xxxxx = some Port Number)
#                   If there is no HIYA,xxxxx, the server is not running
#                   HELLO is resent every x seconds until a valid HIYA reply is received.
#               .py -> CONFIRM,xxxxx
#                       This new Port xxxxx number is the Data Channel
#
#               Once HIYA is received,
#                   The Com Channel is then closed
#                   The new data port is opened and all triffic is moved to this.
#
#    Data Channel - Handles all of the streamed JSON data (from the server)
#               Periodically the Data Channel sends out a heartbeat "RUNNING" to keep the connection alive.
#               This is due to the fact the the Server does not know if the browser is still active.
#
#               If Data does not stream, it may be that the board is down
#
#               The data port number is different for each Browser connected.
#               The server manages all of the different ports used by the browsers
#
#               Once a JSON message is received, that message is immediately passed to the browser.
#
#		Example:
#               	while True
#                   		Get message from server
#                   		Send message to browser
#
# When sending a message to the server, the initial 8 bytes are a 'HEADER' message
# When the message arrives at the server, the header is inspected and dealt with
# accordingly.  
#     HELLO    -> HIYA,xxxxx
#     CONFIRM,xxxxx -> Initiates Data Transfer
#     RUNNING -> Updates heartbeat Timer
#
# No Known Bugs
#
# Features to be added:
#     1. Command Line Logging via a touch file
#     2. Command Line Messaging... Prod Messages or Pre-Scripted Messages
#

import sys
import cgitb
import socket
import time

cgitb.enable()


def publish_error_to_browser_e(str_message, e):
    # send an error message to the broswer
    s_error = str_message + (" I/O error({0}): {1}".format(e.errno, e.strerror))

    print('event: message\n' + 'data: {"Element":"Error_Message","Data":' + '"' + str(s_error) + '"' + '}\n\n')
    sys.stdout.flush()

def publish_error_to_browser(str_message):
    # send an error message to the broswer
    s_error = str_message

    print('event: message\n' + 'data: {"Element":"Error_Message","Data":' + '"' + str(s_error) + '"' + '}\n\n')
    sys.stdout.flush()

class Comm_Generic:

    def __init__(self, comm_type):
        self.comm_socket = 0
        self.comm_socket_ip = ""
        self.comm_socket_port = 0
        self.comm_type = comm_type

    def open(self):

        try:
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as e:
            publish_error_to_browser_e(self.comm_type + "()::socket.socket()", e)
            self.close()
            return 5

        try:
            self.comm_socket.bind(("", self.comm_socket_port))
        except socket.error as e:
            publish_error_to_browser_e(self.comm_type + "()::bind()", e)
            self.close()
            return 10

        return 0

    def close(self):

        if self.comm_socket == 0:
            publish_error_to_browser(self.comm_type + "()::close() Socket Not Defined")
            return "ERROR"

        try:
            self.comm_socket.close()
        except socket.error as e:
            publish_error_to_browser_e(self.comm_type + "()::close()", e)
            return "ERROR"

        return "OK"

    def receive(self):

        if self.comm_socket == 0:
            publish_error_to_browser(self.comm_type + "()::receive() Socket Not Defined")
            return "ERROR"

        try:
            b_data, sender_addr = self.comm_socket.recvfrom(128)
        except socket.error as e:

            if e.errno == None:
                return "TIMEOUT"

            publish_error_to_browser_e(self.comm_type + "()::receive() ", e)
            return "ERROR"

        return b_data.decode('utf-8')

    def send(self, write_buffer):

        if self.comm_socket == 0:
            publish_error_to_browser(self.comm_type + "()::send() Socket Not Defined")
            return 40

        output_buffer = write_buffer.encode('utf-8')
        try:
            self.comm_socket.sendto(output_buffer, (self.comm_socket_ip, self.comm_socket_port))
        except socket.error as e:
            publish_error_to_browser_e(self.comm_type + "()::send()", e)
            return 50

        return 0

    def settimeout(self, timeout):

        try:
            self.comm_socket.settimeout(timeout)
        except socket.error as e:
            publish_error_to_browser_e(self.comm_type + "()::settimeout()", e)
            return 50

        return 0

    def print_contents(self, s_text):
        print(s_text + " Type: " + self.comm_type + " IP: " + self.comm_socket_ip + " Port: " + str(self.comm_socket_port))

def read_config_file():

    sPlace = "read_config_file()"

    # This file tells Python where the Data Server is
    s_config_file = "BoardServerIPPort.txt"

    try:
        f = open(s_config_file, mode="r")
    except IOError as e:
        publish_error_to_browser_e(sPlace + "::open() ", e)
        return "ERROR,ERROR"

    try:
        s_ip_port = f.read()
    except IOError as e:
        publish_error_to_browser_e(sPlace + "::read() ", e)
        return "ERROR,ERROR"

    f.close()

    # do a little pre-checking on the string

    iCnt = s_ip_port.count(",")

    if iCnt != 1:
        sLen = str(iCnt)
        publish_error_to_browser(sPlace + " Error: Data Split()->" + s_ip_port + "<- ->" + sLen + "<-")
        return "ERROR,ERROR"

    # this file 'should' contain a single line... something like 192.155.45.6,55056 -> just a simple IP and port
    config_ip, config_port = s_ip_port.split(",")

    if config_ip == "":
        publish_error_to_browser(sPlace + " Invalid IP ->" + config_ip + "<-")
        return "ERROR,ERROR"

    if config_port.isdigit() == False:
        publish_error_to_browser(sPlace + " Port Not Numeric ->" + config_port + "<-")
        return "ERROR,ERROR"

    i_port = int(config_port)

    if i_port < 1000:
        publish_error_to_browser(sPlace + " Invalid Port < 1000 ->" + config_port + "<-")
        return "ERROR,ERROR"

    return s_ip_port


def getDataPort(genComm):

    sPlace = "getDataPort()"

    if genComm.open() != 0:
        publish_error_to_browser(sPlace + " Unable to Open()")
        return 10

    if genComm.settimeout(10.0) != 0:
        publish_error_to_browser(sPlace + " Unable to SetTimeOut()")
        return 15

    # this sends a handshake and waits for a valid reply from the server
    # if no or improper reply, the handshake is sent again
    iWait = 0
    while True:
        if genComm.send("HELLO   ") != 0:
            publish_error_to_browser(sPlace + " Unable to Send() HELLO")
            return 20

        s_data = genComm.receive()
        if s_data == "ERROR":
            publish_error_to_browser(sPlace + " Unable to Receive() HIYA")
            return 25

        if s_data == "TIMEOUT":
            iWait = iWait + 1
            publish_error_to_browser(sPlace + " Waiting For Reply From Server.  Attempt: " + str(iWait))

        # found the HIYA, time to get out
        if s_data.find("HIYA") != -1:
            break

    if genComm.settimeout(None) != 0:
        publish_error_to_browser(sPlace + " Unable to SetTimeOut() To None")
        return 30


    s_elements = s_data.split(",")
    if len(s_elements) != 2:
        publish_error_to_browser(sPlace + " Unexpected Number Of Elements From HIYA Split()->" + s_data + "<-")
        return 35

    s_command = s_elements[0]
    data_port = s_elements[1]

    if s_command != "HIYA":
        publish_error_to_browser(sPlace + " HIYA not received ->" + s_command + "<-")
        return 40

    i_port = int(data_port)

    if i_port < 1000:
        publish_error_to_browser(sPlace +  " HIYA, Invalid Data Port. ->" + data_port + "<-")
        return 45

    if genComm.send("CONFIRM " + "," + data_port) != 0:
        publish_error_to_browser(sPlace + " Unable to Send() CONFIRM")
        return 50

    return i_port


def receive_server_send_browser():

    sPlace = "receive_server_send_browser()"

    # Set up two UDP communication objects... The objects just handle a few simple functions
    genComm = Comm_Generic("general")
    dataComm = Comm_Generic("data")

#   genComm.print_contents("1. general")
#   dataComm.print_contents("1. data")

    # The config file indicates where the data server is and the port to use
    s_return = read_config_file()

    config_ip, config_port = s_return.split(",")
    if config_ip == "ERROR":
        publish_error_to_browser(sPlace + " ERROR Returned on Config Read - IP")
        return

    if config_port == "ERROR":
        publish_error_to_browser(sPlace + " ERROR Returned on Config Read - Port")
        return

    # setting Comm object variables... just to make sure...!
    if hasattr(genComm, 'comm_socket_ip'):
        setattr(genComm, 'comm_socket_ip', config_ip)
    else:
        publish_error_to_browser(sPlace + " Object Issue: genComm::comm_socket_ip")

    if hasattr(genComm, 'comm_socket_port'):
        setattr(genComm, 'comm_socket_port', int(config_port))
    else:
        publish_error_to_browser(sPlace + " Object Issue: genComm::comm_socket_port")

    # this can be set later, but, I did not want the config_ip variable hanging around!!
    if hasattr(dataComm, 'comm_socket_ip'):
        setattr(dataComm, 'comm_socket_ip', config_ip)
    else:
        publish_error_to_browser(sPlace + " Object Issue: dataComm::comm_socket_ip")

#       genComm.print_contents("2. general")
#       dataComm.print_contents("2. data")


    # we have the 'general' communications port to the server.  This is merely to establish
    # an initial connection.  Once this link is established there is a simple handshake with a
    # new data port provided.  All of the communications will take place with the new data port
    # once the hand shake is compelete
    # If there is only one port to use, the server port may go into over drive handling
    #   all of the traffic on 1 port
    i_port = getDataPort(genComm)

    # at this point we are done with gencom.  close it and get out
    genComm.close()

    # this is BAD coding...  I used the return from getDataPort for a STATUS return AND
    # an actual port value... To be fixed later...
    if i_port < 1000:
        s_port = str(i_port)
        publish_error_to_browser(sPlace + " Invalid Data Port Return.  Error: " + s_port)
        return

    dataComm.set_port = i_port
    if hasattr(dataComm, 'comm_socket_port'):
        setattr(dataComm, 'comm_socket_port', i_port)
    else:
        publish_error_to_browser(sPlace + " Object Issue: dataComm::comm_socket_port")

    #genComm.print_contents("3. general")
    #dataComm.print_contents("3. data")

    if dataComm.open() != 0:
        publish_error_to_browser(sPlace + " Unable to Open Data Port")
        return

    # OK, we are ready to begin processing....

    # Time to begin talking to the browser...
    print("Content-Type: text/event-stream\n\n")
    sys.stdout.flush()

    timeBegin = time.time()

    while True:
        s_event = dataComm.receive()
        if s_event == "ERROR":
            publish_error_to_browser(sPlace + " Unable to Receive Data!")
            dataComm.close()
            return

        print(s_event)
        sys.stdout.flush()

        #send out a RUNNNG message every 10 seconds....
        timeNow = time.time()
        if timeNow - timeBegin >= 10:
            timeBegin = time.time()
            if dataComm.send("RUNNING ") != 0:
                publish_error_to_browser(sPlace + " Unable to Send RUNNING Message")
                dataComm.close()
                return

     # check both for close, just in case... they are wrapped in try's
    dataComm.close()
    genComm.close()
    exit(0)

#def over_test():
#    print("Content-Type: text/event-stream\n\n")
#    sys.stdout.flush()
#
#    icount = 0
#    while True:
#        icount = icount + 1
#        print('event: message\n' + 'data: {"Element":"EEPROM_RebootCount","Data":' + '"' + str(icount) + '"' + '}\n\n')
#        sys.stdout.flush()
#
#over_test()

receive_server_send_browser()

exit(0)
