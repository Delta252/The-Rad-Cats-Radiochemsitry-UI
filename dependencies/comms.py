# Comms handler, ported from now obsolete `Serial_lib.py`
# File is responsible for user interaction with communications process
# Command creation, comms initialization, and device identification are all contained within this file

from multiprocessing import Manager
from dependencies.serialhandler import Serial

class Comms:

    def __init__(self):
        self.ID = 1000
        self.comport = -1
        self.s = Serial()
        self.isConnected = False
        
    def start(self):
        try:
            print('Initializing comms process...') 
            self.openPort('COM15')
            return True
#            result = self.findPort()
#            if result:
#                print('Opened ',self.s.comPort, ' port')
#                self.openPort()
#                self.isConnected = True
#                return True
#            else:
#                print('Encountered an issue, unable to start comms')
#                return False
                       
        except Exception as error:
            print('Encountered an error during startup')
            print('Error:',error)
            return False

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
        
    def createCommand(self):
        return
    
    def runCommand(self, command):
        self.s.WRITE(command)
        return

    def findPort(self):
        success = self.s.FIND_COM_PORT()
        if success:
            print('Eligible COM port found')
            return True
        else:
            print('No eligible COM port found')
            print('Comms could not be established')
            return False
        
    def openPort(self, port):
        self.s.OPEN_SERIAL_PORT(port)

    def closePort(self):
        self.s.CLOSE_SERIAL_PORT()
    
    
#    def addCommand(self, cmd):
#        try:
#            print('Attempting to add to buffer:',cmd)
#            self.queue.put(cmd)
#        except Exception as error:
#            print('Experienced error loading command into buffer')
#            print('Error:',error)
