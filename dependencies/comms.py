# Comms handler, ported from now obsolete `Serial_lib.py`
# File is responsible for user interaction with communications process
# Command creation, comms initialization, and device identification are all contained within this file

from dependencies.serialhandler import Serial

# Creation of a Comms object
# Object is responsible for interfacing with user input as a wrapper for the serial connection
# Object is responsible for creating desired serial commands
class Comms:

    def __init__(self):
        self.ID = 1000
        self.comport = -1
        self.s = Serial()
        self.isConnected = False
    
    # Find and open a COM port where the chamber is connected
    def start(self):
        try:
            print('Initializing comms process...') 
            result = self.findPort()
            if result:
                print('Opened ',self.s.comPort, ' port')
                self.openPort()
                self.isConnected = True
                return True
            else:
                print('Encountered an issue, unable to start comms')
                return False
                       
        except Exception as error:
            print('Encountered an error during startup')
            print('Error:',error)
            return False

    # Close a connection
    def stop(self):
        try:
            print('Stopping comms process...') 
            self.closePort()
            self.isConnected = False
            return True         
        except Exception as error:
            print('Encountered an error during shutdown')
            print('Error:',error)
            return False
    
    # Create a command based on user input (placeholder)
    def createCommand(self):
        return
    
    # Run a created command and ensure success
    def runCommand(self, command):
        self.s.WRITE(command) # This method will be replaced in order to receive success feedback
        return

    # Discover which COM port a system is connected on
    def findPort(self):
        success = self.s.FIND_COM_PORT()
        if success:
            print('Eligible COM port found')
            return True
        else:
            print('No eligible COM port found')
            print('Comms could not be established')
            return False

    # Underlying wrapper method to connect to a COM port  
    def openPort(self, port):
        self.s.OPEN_SERIAL_PORT(port)

    # Underlying wrapper method to close a current connection
    def closePort(self):
        self.s.CLOSE_SERIAL_PORT()
    
    # Add a command to a queue (not currently implemented)
#    def addCommand(self, cmd):
#        try:
#            print('Attempting to add to buffer:',cmd)
#            self.queue.put(cmd)
#        except Exception as error:
#            print('Experienced error loading command into buffer')
#            print('Error:',error)
