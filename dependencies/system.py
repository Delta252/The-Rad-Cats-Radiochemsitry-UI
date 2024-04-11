import os, re, time
import sqlite3
import warnings
from queue import *

class System:
    def __init__(self, socket):
        self.systemdataFilepath = os.path.abspath('dependencies/systemdata.db')
        self.connect = sqlite3.connect(self.systemdataFilepath, check_same_thread=False)
        self.devices = []
        self.cmds = []
        self.q = Queue(-1)
        self.socket = socket

    def updateFromDB(self):
        self.devices = []
        self.cursor = self.connect.cursor()
        found = self.cursor.execute("""
            SELECT * FROM systemdata                            
            """).fetchall()

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

    def findDeviceByID(self, dev):
        for i in self.devices:
            if dev == i.id:
                return i # THROWS ERROR IF DEVICE IS NOT IN DEVICE LIST (DURING SETUP)
        return None

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

    def addWait(self):
        # Add global wait time
        transcript = 'Global Wait'
        cmd = f'Wait'
        packet = (cmd, transcript)
        return packet

    def verifyScript(self):
        success = False
        msg = ''
        # Test No1 : if hold listed waits for a previous step
        for index, step in enumerate(self.cmds):
            packet = step[0][0]
            if (packet == 'Wait') and ((step[1] ==  '') or (int(step[1]) < 0)):
                msg = f'Wait time invalid for step {index + 1}'
                return [success, msg]
            elif (packet != 'Wait') and (step[1] != None) and (index-int(step[1])<0):
                msg = f'Hold request invalid for step {index + 1}'
                return [success, msg]
        # Test No2 : if all commands use components listed in system delcaration 
        for step in self.cmds:
            packet = step[0][0]
            if packet == 'Wait':
                continue
            sender = int(re.findall(r'sID(\d+) ', packet)[0])
            receiver = int(re.findall(r'rID(\d+) ', packet)[0])
            if self.findDeviceByID(sender) == None:
                msg = f'Unable to find command device sender ID {sender}'
                return [success, msg]
            if self.findDeviceByID(sender) == None:
                msg = f'Unable to find command device receiver ID {receiver}'
                return [success, msg]
        success = True
        msg = 'Script successfully validated'
        return [success, msg]

    def compileScript(self, user):
        fileName = f'./download/script_{user}.txt' # Create user-specific file
        stepNum = 1
        script = open(fileName, 'w') # User file is overwritten every time if the name is the same
        script.write('>>START\n')
        script.write('\n>>SYSTEM')
        for device in self.devices:
            script.write('\n- '+device.type+': '+str(device.id)) # System declarations
        script.write('\n>>ENDSECTION\n')
        script.write('\n>>EXPERIMENT')
        for step in self.cmds:
            packet = step[0][0]
            transcript = step[0][1]
            if packet == 'Wait':
                entry = f'\n[{stepNum}] Global Wait'
            else:
                receiver = int(re.findall(r'rID(\d+) ', packet)[0])
                if result := re.search('set|pump', transcript): # Edit as classes of actions are introduced
                    action = transcript[result.start():result.end()]
                    setValue = transcript.split()[-1]
                entry = f'\n[{stepNum}] {receiver} {action} {setValue}' # Individual steps
            if step[1] !=  None:
                if packet == 'Wait':
                    entry += f' {step[1]}s'
                else:
                    entry += f' HOLD ({step[1]})' # Hold condition (yes/no)
            stepNum += 1
            script.write(entry)
        script.write('\n>>ENDSECTION\n')
        script.write('\n>>ENDFILE\n') # EOF marker
        script.close() # Release file
        return fileName

    def parseScript(self, pathToFile):
        # Clear component database
        for device in self.devices:
            self.removeFromDB(device.id)
        # Clear system parameters
        self.devices = []
        self.cmds = []
        lineNumber = 0
        fileoutline = []
        msg = ''
        try:
            file = open(pathToFile, 'r')
            content = file.readlines() # Read file line-by-line
            # Loop through lines for sections
            flaglines = []
            for line in content:
                if line.find('>>') != -1:
                    flaglines.append(lineNumber)
                lineNumber += 1
            # Catch file format errors
            if len(flaglines) < 1:
                msg = ('error', 'No file flags detected.')
            elif 'start' not in (content[flaglines[0]].split('>>')[1]).lower():
                msg = ('error', 'File start flag misplaced.')
            elif 'endfile' not in (content[flaglines[-1]].split('>>')[1]).lower():
                msg = ('error', 'End of file misplaced.')
            # Raise error if incorrectly formatted
            if msg != '':
                raise SyntaxError
            # Keep track of sections
            for index, entry in enumerate(flaglines):
                if re.search('>>(.*)', content[entry]).group(1).strip().lower() in {'start', 'endsection', 'endfile'}:
                    continue
                if 'endsection' not in re.search('>>(.*)', content[flaglines[index+1]]).group(1).strip().lower():
                    msg = ('error', 'Section pairing headings mismatched.')
                    raise SyntaxError
                else:
                    fileoutline.append((re.search('>>(.*)', content[entry]).group(1).strip().lower(), flaglines[index], flaglines[index+1]))
            # Parse sections
            for section in fileoutline:
                for line in range(section[1]+1, section[2]): # Exclude start and end flags of section
                    if content[line] == '\n':
                        continue
                    if section[0] == 'system':
                        module = (re.search('- (.*): ', content[line])).group(1)
                        moduleID = (re.search(':(.*)', content[line])).group(1).strip()
                        self.addToDB(moduleID, module)
                    elif section[0] == 'experiment':
                        if 'Global Wait' in content[line]:
                            value = (re.search('Global Wait (\S+?)(s\s*$)', content[line])).group(1).strip()
                            self.generateCommand(['wait', value])
                        else:
                            destinationID = int((re.search(' (.*) [set|pump]', content[line])).group(1).strip()) # Find action keyword
                            action = re.search('set|pump', content[line]).group()
                            value = (re.search('[set|pump] (\S+?)(\s*$|\sHOLD)', content[line])).group(1).strip() # Find action data
                            hold = (re.search('HOLD \((\S+)\)', content[line])) # Find Hold step
                            if hold != None:
                                holdValue = hold.group(1).strip()
                            else:
                                holdValue = None
                            parseData = ['server', 1000, destinationID, value]
                            self.generateCommand([action, parseData, holdValue])
                        pass
                    else:
                        msg = ('error', 'Unknown section heading.')
                        raise SyntaxError
            file.close()

        except SyntaxError:
            print('encountered FormatError')
            print(msg)
            file.close()
            return

    def executeScript(self):
        # Divide cmd list into per-device queues; this allows for parallel operation without multithreading
        startTime = time.time()
        self.socket.emit('system_msg', {'data':'Priming'})
        for cmd in self.cmds:
            packet = cmd[0]
            if packet[0] == 'Wait':
                continue
            receiver = int(re.findall(r'rID(\d+) ', packet[0])[0]) # Extract cmd destination device id
            for device in self.devices:
                if device.id == receiver:
                    device.backlog.append(packet)
                    device.status = 'pending'
        # Active loop to work through the cmd list
        self.socket.emit('system_msg', {'data':'Beginning execution...'})
        laggingIndex = 0 # This is an index of the "slowest" cmd that is currently not done
        while laggingIndex < len(self.cmds):
            time.sleep(0.1) # 100ms tic time
            # Check if lagging index has become done and find the next incomplete command if not
            if self.cmds[laggingIndex][2] == 'done':
                laggingIndex += 1 # Make one step forward in the main record; IMPORTANT! This allows for loop termination
                continue # Next tic with updated lagging index
            # If lagging index is hung up on a wait (critical point), then execute wait
            if (self.cmds[laggingIndex][0][0] == 'Wait') and (self.cmds[laggingIndex][2] != 'done'):
                waitTime = int(self.cmds[laggingIndex][1])
                self.socket.emit('system_msg', {'data':f'Executing global wait ({waitTime}s)'})
                waitStart = time.time()
                time.sleep(waitTime)
                waitEnd = time.time()
                self.socket.emit('system_msg', {'data':f'Actual wait time: ({round((waitEnd - waitStart),2)}s)'})
                self.cmds[laggingIndex][2] = 'done'
                laggingIndex += 1
                continue
            # Check next cmd candidate for each device against main cmd record
            for device in self.devices:
                if not device.backlog:
                    if device.status == 'free':
                        continue # Ignore devices that have no backlog and are not executing
                if (device.currentCommand == None):
                    device.currentCommand = device.backlog.pop(0) # Initialize command
                    for index, cmd in enumerate(self.cmds):
                        if (device.currentCommand[0] == cmd[0][0]) and (cmd[2] != 'done'):
                            device.currentIndex = index
                            break
                    continue
                if device.status == 'done': # Check if there are any more cmds to complete
                    if not device.backlog:
                        device.status = 'free'
                        self.cmds[device.currentIndex][2] = 'done'
                        continue
                    self.cmds[device.currentIndex][2] = 'done'
                    device.currentCommand = device.backlog.pop(0) # Initialize command
                    for index, cmd in enumerate(self.cmds):
                        if (device.currentCommand[0] == cmd[0][0]) and (cmd[2] != 'done'):
                            device.currentIndex = index
                            print(f'Added cmd {device.currentCommand} with index {device.currentIndex}')
                            break
                    device.status = 'pending'
                    continue # Wait for a tic between commands
                # Check if the current cmd has been completed; wait if not
                elif device.status == 'pending': # Current device is waiting
                    # Check for incomplete prior global wait
                    proceed = True
                    for index in range(0, device.currentIndex):
                        if (self.cmds[index][0][0] == 'Wait') and (self.cmds[index][2] != 'done'):
                            proceed = False
                            break
                    # Check for a prerequisite step and completion
                    if self.cmds[device.currentIndex][1] != None:
                        previousStatus = self.cmds[self.cmds[device.currentIndex][1]-1][2]
                        if previousStatus != 'done':
                            proceed = False
                    if not proceed:
                        continue # Counterintuitive, but this jumps to the next loop iteration rather than finishing current one
                    device.status = 'active'
                    self.cmds[device.currentIndex][2] = 'in progress'
                    self.q.put(device.currentCommand) 
                else:
                    continue
        endTime = time.time()
        self.socket.emit('system_msg', {'data':'Cleaning up...'})
        # Cleanup
        for device in self.devices:
            device.status = 'free'
            device.currentCommand = None
        # Verify that all cmds are done
        for cmd in self.cmds:
            if cmd[2] != 'done':
                self.socket.emit('system_msg', {'data':'Failed to properly execute all commands'})
                print(self.cmds)
                return False
                # Reset cmds statuses
        for cmd in self.cmds:
            cmd[2] = 'pending'
        self.socket.emit('system_msg', {'data':f'Script successfully completed (Execution time = {round((endTime - startTime),2)}s)'})
        return True

    def generateCommand(self, data):
        # Expected data format: [set/pump/wait, [input1, input2, input3], holdVal]
        # Main cmd list format: [(cmd, transcript), holdValue, status]
        if data[0] == "wait":
            result = self.addWait()
            if data[1] == '':
                holdVal = 0
            else:
                holdVal = int(data[1])
            self.cmds.append([result, holdVal, 'pending']) 
        else:
            id = int(data[1][2])
            result = 'No Valid Command'
            hold = data[2]
            if (hold == None) or (hold == 'None'): # Depending on source of cmd generation call
                holdVal = None
            else:
                holdVal = int(hold)
            for device in self.devices:
                if id == device.id:
                    try:
                        result = device.parseCommand(data)
                        self.cmds.append([result, holdVal, 'pending'])
                        break
                    except KeyError:
                        print('Invalid action key submitted.')
            else:
                warnings.warn('Unrecognized device request.')
        return 
    
    def runCommand(self): # REQUIRES FIX
        for device in self.devices:
            device.status = 'active'
            device.executeCmds()

    def handleResponse(self, msg):
        if 'FREE' in msg:
            deviceID = int((re.search('sID(.*) rID', msg)).group(1))
            self.setDeviceStatus(deviceID, 'done')
        else:
             pass

class Component:
    def __init__(self, id, descriptor):
        self.status = 'free'
        self.id = id
        self.type = descriptor
        self.cmd = ''
        self.transcript = ''
        self.packets = [] # Flexible array of individual packet elements
        self.commandPacket = () # Immutable serial command and transcript
        self.backlog = [] # Array to keep commands prior to them being pushed to execution
        self.currentCommand = None
        self.currentIndex = 0 # Location in main command log
    
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
        return self.commandPacket
    
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
        action = data[0]
        info = data[1]
        self.requiredVolume = int(info[5])
        while self.requiredVolume>0: # Loop until full necessary volume is delivered
            self.fill(info) # Fill full volume of syringe
            self.empty(info) # Empty necessary volume of syringe
        return self.backlog #ERROR >> REQUIRES REWORK
    
    def fill(self, info):
        self.packets.append(f'Y1') # Pump module number
        return
    
    def empty(self, info):
        return
    
    def resetPosition(self):
        return

class PeristalticPump(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        if action == 'pump':
            result = self.pumpVolume(info)
            return result
        else:
            raise KeyError
    
    def pumpVolume(self, info):
        self.packets.append(f'P1') # Pump module number
        if type(info[3]) == str:
            volume = int(re.findall(r'\d+', info[3])[0])
        else:
            volume = int(info[3])
        self.packets.append(f'm{volume}') # Pump volume
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' pump {volume}mL'
        return self.assembleCmd()

class Mixer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        if action == 'set':  
            result = self.setSpeed(info)
            return result
        else:
            raise KeyError
    
    def setSpeed(self, info):
        self.packets.append(f'M1') # Mixer module number
        mode = info[3]
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
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' set to {mode}' # Add to transcript
        return self.assembleCmd()

class Shutter(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        if action == 'set':
            result = self.setPosition(info)
            return result
        else:
            raise KeyError
    
    def setPosition(self, info):
        self.packets.append(f'I1') # Shutter module number
        position = info[3]
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
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' set to {position}' # Add to transcript
        return self.assembleCmd()

class Extraction(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        self.backlog = [] # Clear backlog for new commands
        if action == 'set':
            result = self.setAngle(info)
        elif action == 'pump':
            result = self.pumpVolume(info)
        else:
            raise KeyError
        return result
    
    def setAngle(self, info):
        self.packets.append(f'E') # Extractor module number
        slot = int(info[3])
        angle = ((slot)-1)*(180/4)
        self.packets.append(f'S{angle}') # Extractor slot
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' set to position {slot}' # Add to transcript
        return self.assembleCmd()
    
    def pumpVolume(self, info):
        self.packets.append(f'P5') # Extractor pump module number (static)
        volume = int(info[4])
        self.packets.append(f'm{volume}') # Pump volume
        self.setCmdBase(info[0], info[1], info[2]) # Cmd2
        self.transcript += f' pump {volume}mL' # Add to transcript
        return self.assembleCmd()

class Valve(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
        self.numberOfValves = 5
    
    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        if action == 'set':
            result = self.setValves(info)
            return result
        else:
            raise KeyError
    
    def setValves(self, info):
        self.packets.append(f'V') # Valve module number
        # output = int(info[3])
        # if valve<output:
        #     self.transcript = None
        #     status = 1
        # elif valve==output:
        #     self.transcript += f' set output to {info[3]}' # Add to transcript
        #     status = 0
        # else:
        #     self.transcript = None
        #     status = 2
        # self.packets.append(f'S{status}')
        # self.setCmdBase(info[0], info[1], info[2]) # Cmd2           
        return self.assembleCmd()

class Spectrometer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        return