Rick Faszold

XEn, LLC - USA, Missouri (c)

October 11th, 2017

This program can only be used with permission from XEn, LLC.  Missouri, USA  (c)

This Python script accepts fully formatted JSON messages from a server and
immediately streams that data to a browser.  The browser uses a few lines of
.js to place that data into their correct locations.  Like this .py script, the .js
in the browser is kept to a minimum in order to ensure greater performance.

There are two UDP connections that handle server side communications
   Com Channel - This establishes communications with the server 
		The IP/Port of the server is stored in a config file located in the .py cgi dir
		Once a connection is established, this handles the initial handshake
              .py -> HELLO
              Server -> HIYA,xxxxx   (xxxxx = some Port Number)
                  If there is no HIYA,xxxxx, the server is not running
                  HELLO is resent every x seconds until a valid HIYA reply is received.
              .py -> CONFIRM,xxxxx
                      This new Port xxxxx number is the Data Channel

              Once HIYA is received on Python,
                  The Com Channel is then closed
                  The new data port is opened and all traffic is moved to this.
                  
              Once CONFIRMed is by the Go Middleware, data starts streaming to Python.

   Data Channel - Handles all of the streamed JSON data (from the server)
              Periodically the Data Channel sends out a heartbeat "RUNNING" to keep the connection alive.
              This is due to the fact the the Server does not know if the browser is still active.

              If Data does not stream, it may be that the board is down

              The data port number is different for each Browser connected.
              The server manages all of the different ports used by the browsers

              Once a JSON message is received, that message is immediately passed to the browser.

		Example:
              	while True
                  		Get message from server
                  		Send message to browser

When sending a message to the server, the initial 8 bytes are a 'HEADER' message
When the message arrives at the server, the header is inspected and dealt with
accordingly.  
    HELLO    -> HIYA,xxxxx
    CONFIRM,xxxxx -> Initiates Data Transfer
    RUNNING -> Updates heartbeat Timer - every 10 seconds

