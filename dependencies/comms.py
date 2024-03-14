# Comms handler, ported from now obsolete `Serial_lib.py`
# File is responsible for user interaction with communications process
# Command creation, comms initialization, and device identification are all contained within this file

import os, time, re
from threading import Thread
from dependencies.serialhandler import Serial

# Creation of a Comms object
# Object is responsible for interfacing with user input as a wrapper for the serial connection
# Object is responsible for creating desired serial commands
class Comms:
    def __init__(self, system, socket):
        self.system = system
        self.comport = -1
        self.s = Serial()
        self.isConnected = False
        self.socket = socket

    # Find and open a COM port where the chamber is connected
    def start(self):
        try:
            self.socket.emit('serial_response', {'data':'Initializing comms process...'}) 
            result = self.findPort()
            if result:
                msg = 'Opened ' + self.s.comPort + ' port'
                self.socket.emit('serial_response', {'data':msg})
                self.openPort()
                self.isConnected = True
                # Create process to feed commands to and read responses from Serial
                # Process runs in parallel to main program
                thread = Thread(target=self.runComms)
                thread.start()
                return True
            else:
                self.socket.emit('serial_response', {'data':'Encountered an issue, unable to start comms'})
                return False
                       
        except Exception as error:
            self.socket.emit('serial_response', {'data':'Encountered an error during startup'})
            errorMsg = 'Error: ' + error
            self.socket.emit('serial_response', {'data':errorMsg})
            return False

    # Close a connection
    def stop(self):
        try:
            self.socket.emit('serial_response', {'data':'Stopping comms process...'}) 
            self.closePort()
            self.isConnected = False
            return True         
        except Exception as error:
            self.socket.emit('serial_response', {'data':'Encountered an error during shutdown'})
            errorMsg = 'Error: ' + error
            self.socket.emit('serial_response', {'data':errorMsg})
            return False
    
    # Create a command based on user input (placeholder)
    def createCommand(self):
        return
    
    # Run a created command and ensure success
    def runCommand(self, command):
        self.socket.emit('log_command', {'data':command})
        self.s.WRITE(command[0]) # This method will be replaced in order to receive success feedback
        return

    def readResponse(self):
        result = self.s.READ()
        if result != None:
            for entry in result:
                self.socket.emit('serial_response', {'data':entry})
                if 'FREE' in entry:
                    deviceID = int((re.search('sID(.*) rID', entry)).group(1))
                    self.system.setDeviceStatus(deviceID, 'free')
        return result     

    # Discover which COM port a system is connected on
    def findPort(self):
        self.comport = self.s.FIND_COM_PORT()
        if self.comport != -1:
            self.socket.emit('serial_response', {'data':'Eligible COM port found'})
            return True
        else:
            self.socket.emit('serial_response', {'data':'No eligible COM port found'})
            self.socket.emit('serial_response', {'data':'Comms could not be established'})
            return False

    # Underlying wrapper method to connect to a COM port  
    def openPort(self):
        self.s.OPEN_SERIAL_PORT(self.comport)

    # Underlying wrapper method to close a current connection
    def closePort(self):
        self.s.CLOSE_SERIAL_PORT()
    
    def runComms(self):
        try:
            run = True
            while run:
                cmd = self.system.handleQueues()
                if cmd != None:
                    self.runCommand(cmd)
                incoming = self.readResponse()
                time.sleep(1)
        except BrokenPipeError:
            return
    # Add a command to a queue (not currently implemented)
#    def addCommand(self, cmd):
#        try:
#            print('Attempting to add to buffer:',cmd)
#            self.queue.put(cmd)
#        except Exception as error:
#            print('Experienced error loading command into buffer')
#            print('Error:',error)
