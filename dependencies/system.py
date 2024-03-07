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
        return ''

class Component:
    def __init__(self, id, descriptor):
        self.status = 'free'
        self.id = id
        self.type = descriptor
        self.commandPacket = [] # Serial command and transcript
        self.q = Queue(-1)
    
    def setCmdBase(self, senderDevice, senderID, receiverID):
        cmd = f'[sID{senderID} rID{receiverID}'
        transcript = f'{str(senderDevice).capitalize()} ({senderID}) requests {str(self.type).capitalize()} ({receiverID})'
        self.commandPacket = [cmd, transcript]
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

    def parseCommand(self, data):
        return

class PeristalticPump(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        return

class Mixer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        return

class Shutter(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        return

class Extraction(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        print(data)
        slot = int(data[3])
        volume = int(data[4])
        self.setCmdBase(data[0], data[1], data[2]) # Cmd1
        self.setAngle(slot)
        self.q.put(self.commandPacket[0])
        self.setCmdBase(data[0], data[1], data[2]) # Cmd2
        self.pumpVolume(volume)
        self.q.put(self.commandPacket[0])
        return self.commandPacket
    
    def setAngle(self, slot):
        angle = ((slot)-1)*(180/4)
        self.commandPacket[0] += f' PK1 E1 S{angle}]'
        self.commandPacket[1] += f' set to position {slot}'
        return
    
    def pumpVolume(self, volume):
        self.commandPacket[0] += f' PK2 P5 m{volume}]'
        self.commandPacket[1] += f' extract {volume}ml'
        return

class Valve(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        print(data)
        cmd = f'[sID{data[0]} rID{data[0]} PK1 E1 {data[0]}]'
        return cmd

class Spectrometer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        return