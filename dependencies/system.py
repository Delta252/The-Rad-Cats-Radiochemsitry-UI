import os 
import sqlite3

class System:
    def __init__(self):
        self.systemdataFilepath = os.path.abspath('dependencies/systemdata.db')
        self.connect = sqlite3.connect(self.systemdataFilepath, check_same_thread=False)
        self.cursor = self.connect.cursor()
        self.devices = []

    def updateFromDB(self):
        self.devices = []
        self.cursor.execute("""
            SELECT * FROM systemdata                            
            """)

        found = self.cursor.fetchall()

        for i in found:
            dev = Component(i[0], i[1])
            self.devices.append(dev)


    def addToDB(self, id, descriptor):
        # Inserts new element or updates an existing one  !!WARNING
        self.cursor.execute("""
            REPLACE INTO systemdata(id, device) VALUES(?, ?)
            """, (id, descriptor))
        
        self.updateFromDB()

    def removeFromDB(self, id):
        # Removes a known entry based on device ID
        self.cursor.execute(f"""
            DELETE FROM systemdata WHERE id={id}
            """)
        
        self.updateFromDB()

    def updateID(self, oldID, newID):
        # Updates record of device without adding/removing listing
        self.cursor.execute(f"""
            UPDATE systemdata SET id = REPLACE(id, {oldID}, {newID})
            """)

        self.updateFromDB()

    def listDevices(self):
        for i in self.devices:
            print(f'Device {i.type} at ID {i.id}\n')

class Component:
    def __init__(self, id, descriptor):
        self.status = -1
        self.id = id
        self.type = descriptor
