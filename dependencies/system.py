import os
import sqlite3
import warnings
from queue import *

class System:
    def __init__(self):
        self.systemdataFilepath = os.path.abspath('dependencies/systemdata.db')
        self.connect = sqlite3.connect(self.systemdataFilepath, check_same_thread=False)
        self.devices = []

    def updateFromDB(self):
        self.devices = []
        self.cursor = self.connect.cursor()
        self.cursor.execute("""
            SELECT * FROM systemdata                            
            """)

        found = self.cursor.fetchall()

        for i in found:
            match i[1]:
                case 'server':
                    dev = Server(i[0], i[1])
                case 'pump-syringe':
                    dev = SyringePump(i[0], i[1])
                case 'pump-peristaltic':
                    dev = PeristalticPump(i[0], i[1])
                case 'mixer':
                    dev = Mixer(i[0], i[1])
                case 'shutter':
                    dev = Shutter(i[0], i[1])
                case 'extraction':
                    dev = Extraction(i[0], i[1])
                case 'valve':
                    dev = Valve(i[0], i[1])
                case _:
                    warnings.warn('Unrecognized device in database.')

            self.devices.append(dev)
        
        self.cursor.close()


    def addToDB(self, id, descriptor):
        # Inserts new element or updates an existing one  !!WARNING
        self.cursor = self.connect.cursor()
        self.cursor.execute("""
            INSERT INTO systemdata(id, device) VALUES(?, ?)
            """, (id, descriptor))
        
        self.connect.commit()
        self.cursor.close()
        self.updateFromDB()

    def removeFromDB(self, id):
        # Removes a known entry based on device ID
        self.cursor = self.connect.cursor()
        self.cursor.execute(f"""
            DELETE FROM systemdata WHERE id={id}
            """)
        
        self.connect.commit()
        self.cursor.close()
        self.updateFromDB()

    def updateID(self, oldID, newID):
        # Updates record of device without adding/removing listing
        self.cursor = self.connect.cursor()
        self.cursor.execute(f"""
            UPDATE systemdata SET id = REPLACE(id, {oldID}, {newID})
            """)

        self.connect.commit()
        self.cursor.close()
        self.updateFromDB()

    def updateServerID(self, newID):
        # Updates server id specifically without need for old id
        self.cursor = self.connect.cursor()
        self.cursor.execute(f"""
            UPDATE systemdata SET id ='{newID}' WHERE device='server'
            """)

        self.connect.commit()
        self.cursor.close()
        self.updateFromDB()

    def listDevices(self):
        for i in self.devices:
            print(f'Device {i.type} at ID {i.id}\n')

    def findDeviceByID(self, id):
        for i in self.devices:
            if i.id == id:
                return i

    def setDeviceStatus(self, id, status):
        device = self.findDeviceByID(id)
        device.status = status

    def define(self):
        # Method used for serializing data to send over sockets
        # Method addresses problems with devices list not being JSON serializeable
        data = []

        for i in self.devices:
            data.append((i.id, i.type))

        return data
    
    def generateCommand(self, data):
        id = int(data[2])
        result = 'No Valid Command'
        for device in self.devices:
            if id == device.id:
                result = device.parseCommand(data)
                break
        else:
            warnings.warn('Unrecognized device request.')
        return result
    
    def handleQueues(self):
        for component in self.devices:
            if (component.q.qsize()>0) & (component.status == 'free'):
                return component.q.get()
        return None

class Component:
    def __init__(self, id, descriptor):
        self.status = 'free'
        self.id = id
        self.type = descriptor
        self.cmd = ''
        self.transcript = ''
        self.packets = [] # Flexible array of individual packet elements
        self.commandPacket = () # Immutable serial command and transcript
        self.q = Queue(-1)
    
    def setCmdBase(self, senderDevice, senderID, receiverID):
        self.cmd = f'[sID{senderID} rID{receiverID}'
        self.transcript = f'{str(senderDevice).capitalize()} ({senderID}) requests {str(self.type).capitalize()} ({receiverID})'
        return
    
    def assembleCmd(self):
        numOfPackets = len(self.packets)
        self.cmd += f' PK{numOfPackets}' # Automatic packet length
        for entry in self.packets:
            self.cmd += f' {entry}' # Add all packets
        self.cmd += ']' # End command
        self.commandPacket = (self.cmd, self.transcript) # Create immutable cmd/transcript pair
        self.cmd = '' # Clear cmd
        self.transcript = '' # Clear transcript
        self.packets = [] # Empty packet array
        return
    
    def setStatus(self, status):
        self.status = status

    def getStatus(self):
        return self.status

class Server(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        return

class SyringePump(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
        self.position = 0
        self.requiredVolume = 0

    def parseCommand(self, data):
        self.requiredVolume = int(data[6])
        while self.requiredVolume>0: # Loop until full necessary volume is delivered
            self.fill(data) # Fill full volume of syringe
            self.empty(data) # Empty necessary volume of syringe
        return self.commandPacket
    
    def fill(self, data):
        self.packets.append(f'Y{int(data[3])}') # Pump module number
        return
    
    def empty(self, data):
        return
    
    def resetPosition(self):
        return

class PeristalticPump(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        self.pumpVolume(data)
        self.q.put(self.commandPacket)
        return self.commandPacket
    
    def pumpVolume(self, data):
        self.packets.append(f'P{int(data[3])}') # Pump module number
        volume = int(data[4])
        self.packets.append(f'm{volume}') # Pump volume
        self.setCmdBase(data[0], data[1], data[2]) # Cmd1
        self.transcript += f' pump {volume}ml'
        self.assembleCmd()
        return

class Mixer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):        
        self.setSpeed(data)
        self.q.put(self.commandPacket)
        return self.commandPacket
    
    def setSpeed(self, data):
        self.packets.append(f'M{int(data[3])}') # Mixer module number
        mode = data[4]
        match mode:
            case 'stop':
                speed = 0
            case 'slow':
                speed = 45
            case 'medium':
                speed = 60
            case 'fast':
                speed = 200
            case _:
                speed = 0
                mode = 'stop'
                self.transcript = 'An unexpected mixer speed has been encountered; speed has been set to 0 and mixer' # First half of error transcript
                return
        self.packets.append(f'S{speed}') # Mixer speed
        direction = 1 # Permanent direction
        self.packets.append(f'D{direction}')
        self.setCmdBase(data[0], data[1], data[2]) # Cmd1
        self.transcript += f' set to {mode}' # Add to transcript
        self.assembleCmd()
        return

class Shutter(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        self.setPosition(data)
        self.q.put(self.commandPacket)
        return self.commandPacket
    
    def setPosition(self, data):
        self.packets.append(f'I{int(data[3])}') # Shutter module number
        position = data[4]
        match position:
            case 'closed':
                posNum = 0
            case 'open':
                posNum = 1
            case 'partial':
                posNum = 2
            case _:
                posNum = 0
                position = 'closed'
                self.transcript = 'An unexpected shutter position has been encountered; shutter has been' # First half of error transcript
                return
        self.packets.append(f'S{posNum}')
        self.setCmdBase(data[0], data[1], data[2]) # Cmd1
        self.transcript += f' set to {position}' # Add to transcript
        self.assembleCmd()
        return

class Extraction(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        self.setAngle(data)
        self.q.put(self.commandPacket)
        self.pumpVolume(data)
        self.q.put(self.commandPacket)
        return self.commandPacket
    
    def setAngle(self, data):
        self.packets.append(f'E{int(data[3])}') # Extractor module number
        slot = int(data[4])
        angle = ((slot)-1)*(180/4)
        self.packets.append(f'S{angle}') # Extractor slot
        self.setCmdBase(data[0], data[1], data[2]) # Cmd1
        self.transcript += f' set to position {slot}' # Add to transcript
        self.assembleCmd()
        return
    
    def pumpVolume(self, data):
        self.packets.append(f'P5') # Extractor pump module number (static)
        volume = int(data[5])
        self.packets.append(f'm{volume}') # Pump volume
        self.setCmdBase(data[0], data[1], data[2]) # Cmd2
        self.transcript += f' extract {volume}ml' # Add to transcript
        self.assembleCmd()
        return

class Valve(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
        self.numberOfValves = 5
    
    def parseCommand(self, data):
        self.setValves(data)
        self.q.put(self.commandPacket)
        return self.commandPacket
    
    def setValves(self, data):
        for valve in range(0,self.numberOfValves):
            self.packets.append(f'V{valve}') # Valve module number
            output = int(data[3])
            if valve<output:
                self.transcript = None
                status = 1
            elif valve==output:
                self.transcript += f' set output to {data[3]}' # Add to transcript
                status = 0
            else:
                self.transcript = None
                status = 2
            self.packets.append(f'S{status}')
            self.setCmdBase(data[0], data[1], data[2]) # Cmd2           
            self.assembleCmd()
        return

class Spectrometer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        return