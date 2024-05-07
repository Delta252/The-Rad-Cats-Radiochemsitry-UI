# Comms handler, ported from now obsolete `Serial_lib.py`
# File is responsible for user interaction with communications process
# Command creation, comms initialization, and device identification are all contained within this file

import os, time, re
from threading import Thread
from .serialhandler import Serial

# Creation of a Comms object
# Object is responsible for interfacing with user input as a wrapper for the serial connection
# Object is responsible for creating desired serial commands
class Comms:
    def __init__(self, system, socket):
        self.system = system
        self.comPorts = -1
        self.s = Serial()
        self.isConnected = False
        self.socket = socket

    # Find and open a COM port where the chamber is connected
    def start(self):
        try:
            self.socket.emit('system_msg', {'data':'Initializing comms process...'}) 
            result = self.findPorts()
            portList = ''
            if result:
                for entry in self.comPorts:
                    portList += (f' {entry[0]} ')
                msg = 'Opened [' + portList + '] ports'
                self.socket.emit('system_msg', {'data':msg})
                self.openPorts(self.comPorts)
                self.isConnected = True
                # Create process to feed commands to and read responses from Serial
                # Process runs in parallel to main program
                thread = Thread(target=self.runComms)
                thread.start()
                return True
            else:
                self.socket.emit('system_msg', {'data':'Encountered an issue, unable to start comms'})
                return False
                       
        except Exception as error:
            self.socket.emit('system_msg', {'data':'Encountered an error during startup'})
            errorMsg = 'Error: ' + repr(error)
            self.socket.emit('system_msg', {'data':errorMsg})
            return False

    # Close a connection
    def stop(self):
        try:
            self.socket.emit('system_msg', {'data':'Stopping comms process...'}) 
            self.closePorts()
            self.isConnected = False
            return True         
        except Exception as error:
            self.socket.emit('system_msg', {'data':'Encountered an error during shutdown'})
            errorMsg = 'Error: ' + repr(error)
            self.socket.emit('system_msg', {'data':errorMsg})
            return False
    
    # Create a command based on user input (placeholder)
    def createCommand(self):
        return
    
    # Run a created command and ensure success
    def runCommand(self, command):
        self.socket.emit('log_command', {'data':command})
        destination= int(re.findall(' rID(\d+) ', command[0])[0])
        for port in self.comPorts:
            if port[1] == destination:
                print(f'Started command execution for {destination} at {time.time()}')
                self.s.WRITE(port[0], command[0]) # This method will be replaced in order to receive success feedback
        return

    def readResponse(self):
        result = None
        for port in self.comPorts:
            result = self.s.READ(port[0])
            if result != None:
                for entry in result:
                    self.socket.emit('serial_response', {'data':entry})
                    self.system.handleResponse(entry)
        return result     

    # Discover which COM port a system is connected on
    def findPorts(self):
        self.comPorts = self.s.FIND_COM_PORTS()
        print(self.comPorts)
        if self.comPorts != False:
            self.socket.emit('system_msg', {'data':'Eligible COM ports found'})
            return True
        else:
            self.socket.emit('system_msg', {'data':'No eligible COM port found'})
            self.socket.emit('system_msg', {'data':'Comms could not be established'})
            return False

    # Underlying wrapper method to connect to a COM port  
    def openPorts(self, portList):
        ports = []
        for entry in portList:
            ports.append(entry[0])
        self.s.OPEN_SERIAL_PORTS(ports)
        print('Successfully opened ports')

    # Underlying wrapper method to close a current connection
    def closePorts(self):
        self.s.CLOSE_SERIAL_PORTS(self.comPorts)
    
    def runComms(self):
        try:
            run = True
            while run:
                if self.system.q.qsize()>0:
                    cmd = self.system.q.get()
                    print(f'Got command at {time.time()}')
                    self.runCommand(cmd)
                incoming = self.readResponse() # Assigned response package to variable for future handling (not implemented)
                time.sleep(0.001) # 1ms tic for comms handling
        except BrokenPipeError:
            return
