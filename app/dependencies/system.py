import os, re, time, sys
import sqlite3
import warnings
from queue import *
from .analysis import Analysis
from .cameras import SpectrometerVideo

class System:
    def __init__(self, socket):
        databaseFilepath = 'systemdata.db'
        if getattr(sys, 'frozen', False):
            applicationPath = os.path.dirname(sys.executable)
        elif __file__:
            applicationPath = os.path.dirname(__file__)
        systemdataFilepath = os.path.join(applicationPath, databaseFilepath)
        self.connect = sqlite3.connect(systemdataFilepath, check_same_thread=False)
        cursor = self.connect.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS systemdata (
                id INT UNSIGNED NOT NULL,
                device VARCHAR(255) NOT NULL,
                UNIQUE(id, device)
                )
            """)
        self.connect.commit()
        cursor.execute(f"""
            INSERT INTO systemdata(id, device) 
                SELECT 1000, 'server' 
                    WHERE NOT EXISTS(SELECT 1 FROM systemdata WHERE device='server')
            """)
        self.connect.commit()
        cursor.close()
        self.devices = []
        self.cmds = []
        self.q = Queue(-1)
        self.socket = socket
        self.tempReadings = [] # This should be consolidated elsewhere (within a sensor module)
        self.lastReadingTime = 0
        self.analysis = Analysis()
        self.updateFromDB()

    def updateFromDB(self):
        self.devices = []
        cursor = self.connect.cursor()
        found = cursor.execute("""
            SELECT * FROM systemdata                            
            """).fetchall()

        print(found)

        for i in found:
            match i[1]:
                case 'server':
                    dev = Server(i[0], i[1])
                case 'pump-syringe':
                    dev = SyringePump(i[0], i[1])
                case 'pump-peristaltic':
                    dev = PeristalticPump(i[0], i[1])
                case 'mixer-shutter':
                    dev = MixerShutter(i[0], i[1])
                case 'extraction':
                    dev = Extraction(i[0], i[1])
                case 'valve':
                    dev = Valve(i[0], i[1])
                case 'sensor':
                    dev = Sensor(i[0], i[1])
                case 'spectrometer':
                    dev = Spectrometer(i[0], i[1])
                case _:
                    warnings.warn('Unrecognized device in database.')
            print(dev)
            self.devices.append(dev)
        
        cursor.close()

    def addToDB(self, id, descriptor):
        # Inserts new element or updates an existing one  !!WARNING
        cursor = self.connect.cursor()
        cursor.execute("""
            INSERT INTO systemdata(id, device) VALUES(?, ?)
            """, (id, descriptor))
        
        self.connect.commit()
        cursor.close()
        self.updateFromDB()

    def removeFromDB(self, id):
        # Removes a known entry based on device ID
        cursor = self.connect.cursor()
        cursor.execute(f"""
            DELETE FROM systemdata WHERE id={id}
            """)
        
        self.connect.commit()
        cursor.close()
        self.updateFromDB()

    def updateID(self, oldID, newID):
        # Updates record of device without adding/removing listing
        cursor = self.connect.cursor()
        cursor.execute(f"""
            UPDATE systemdata SET id = REPLACE(id, {oldID}, {newID})
            """)

        self.connect.commit()
        cursor.close()
        self.updateFromDB()

    def updateServerID(self, newID):
        # Updates server id specifically without need for old id
        cursor = self.connect.cursor()
        cursor.execute(f"""
            UPDATE systemdata SET id ='{newID}' WHERE device='server'
            """)

        self.connect.commit()
        cursor.close()
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
            if (packet == 'Wait') and ((step[1] ==  '') or (int(step[1][0]) < 0)):
                msg = f'Wait time invalid for step {index + 1}'
                return [success, msg]
            elif (packet != 'Wait') and (step[1] != None):
                print(f'packet: {packet}, step: {step}')
                for hold in step[1]:
                    if (index-int(hold)<0):
                        msg = f'Hold request invalid for step {index + 1}'
                        return [success, msg]
        # Test No2 : if all commands use components listed in system delcaration 
        for step in self.cmds:
            packet = step[0][0]
            if (packet == 'Wait') or (packet == 'Spectrometer Reading'):
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
        fileName = f'/download/script_{user}.txt' # Create user-specific file
        stepNum = 1
        scriptLoc = f'app/{fileName}'
        script = open(scriptLoc, 'w') # User file is overwritten every time if the name is the same
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
                if result := re.search('set|pump|mix', transcript): # Edit as classes of actions are introduced
                    action = transcript[result.start():result.end()]
                    print(transcript)
                    setValue = transcript.split()[-1]
                    if 'mix' in transcript:
                        direction = (re.search('mix (.*) ', transcript)).group(1).strip()
                    else:
                        direction = ""
                    if 'Pump-syringe' in transcript:
                        syringeID = (re.search('\[S(.*)\]', transcript)).group(1).strip()
                        syringeType = f' type {syringeID}'
                    else:
                        syringeType = ""
                entry = f'\n[{stepNum}] {receiver}{syringeType} {action} {setValue} {direction} ' # Individual steps
            if step[1] !=  None:
                if packet == 'Wait':
                    entry += f' {step[1]}s'
                else:
                    entry += f'HOLD ({",".join(step[1])})' # Hold condition (yes/no)
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
                            value = (re.search('Global Wait \[\'(\S+?)\'\](s\s*$)', content[line])).group(1).strip()
                            self.generateCommand(['wait', value])
                        else:
                            lineElements = content[line].split()
                            destinationID = int(lineElements[1]) # Find action keyword
                            action = lineElements[2]
                            if action == 'type':
                                action = lineElements[4]
                            values = []
                            for element in lineElements[3:None]:
                                if element == 'HOLD':
                                    holdValue = lineElements[-1]
                                    break
                                if element == 'type':
                                    continue
                                else:
                                    values.append(element)
                                    holdValue = None
                            parseData = ['server', 1000, destinationID]
                            parseData.extend(values)
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
        for device in self.devices:
            device.status = 'free'
        # Divide cmd list into per-device queues; this allows for parallel operation without multithreading
        startTime = time.time()
        self.socket.emit('system_msg', {'data':'Priming'})
        for cmd in self.cmds:
            packet = cmd[0]
            if packet[0] == 'Wait':
                continue
            elif packet[0] == 'Spectrometer Reading':
                receiver = 1011 # THIS IS A TEMPORARY FIX FOR THE SPECTROMETER OPERATION!!!
            else:
                receiver = int(re.findall(r'rID(\d+) ', packet[0])[0]) # Extract cmd destination device id
            for device in self.devices:
                if device.id == receiver:
                    device.backlog.append(packet)
                    device.status = 'pending'
        # Active loop to work through the cmd list
        self.socket.emit('system_msg', {'data':'Beginning execution...'})
        print(self.cmds)
        laggingIndex = 0 # This is an index of the "slowest" cmd that is currently not done
        while laggingIndex < len(self.cmds):
            time.sleep(0.05) # 50ms tic time
            self.socket.emit('update-history', {'data':self.cmds})
            # Check if lagging index has become done and find the next incomplete command if not
            if self.cmds[laggingIndex][2] == 'done':
                laggingIndex += 1 # Make one step forward in the main record; IMPORTANT! This allows for loop termination
                continue # Next tic with updated lagging index
            for device in self.devices:
                if (device.type == 'sensor') and (device.status != 'active'):
                    if ((time.time()-self.lastReadingTime) > 1): # Request temperature reading from all sensor modules that are not currently awaiting response
                        device.status = 'active'
                        self.q.put(device.takeTempReading())
            # If lagging index is hung up on a wait (critical point), then execute wait
            if (self.cmds[laggingIndex][0][0] == 'Wait') and (self.cmds[laggingIndex][2] != 'done'):
                if (self.cmds[laggingIndex][2] == 'active') and (time.time()-waitStart < waitTime):
                    continue
                elif (self.cmds[laggingIndex][2] == 'pending'):
                    self.cmds[laggingIndex][2] = 'active'
                    waitTime = int(self.cmds[laggingIndex][1][0])
                    self.socket.emit('system_msg', {'data':f'Executing global wait ({waitTime}s)'})
                    waitStart = time.time()
                    continue
                else:
                    self.cmds[laggingIndex][2] = 'done'
                    waitEnd = time.time()
                    self.socket.emit('system_msg', {'data':f'Actual wait time: ({round((waitEnd - waitStart),2)}s)'})
                    laggingIndex += 1
                    continue
            # Check next cmd candidate for each device against main cmd record
            for device in self.devices:
                if (device.status == 'free') or (device.type == 'sensor'):
                    continue # Ignore devices that have no backlog and are not executing
                if (device.currentCommand == None):
                    print(f'adding command for {device.type} ({device.status}) and {device.id}')
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
                        previousIndeces = [ int(x) for x in self.cmds[device.currentIndex][1]]
                        for index in previousIndeces:
                            previousStatus = self.cmds[index-1][2]
                            if previousStatus != 'done':
                                proceed = False
                    if not proceed:
                        continue # Counterintuitive, but this jumps to the next loop iteration rather than finishing current one
                    device.status = 'active'
                    print(f'Added command at {time.time()}')
                    self.cmds[device.currentIndex][2] = 'active'
                    if device.currentCommand[0] == 'Spectrometer Reading':
                        device.takeSpectReading() # THIS IS A TEMPORARY FIX FOR THE SPECTROMETER OPERATION!!!
                    else:
                        self.q.put(device.currentCommand)
                else:
                    continue
        endTime = time.time()
        self.socket.emit('update-history', {'data':self.cmds})
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
        # Export data
        filename = f'TestRun{round(time.time())}'
        self.analysis.exportToFile(self.tempReadings, filename)
        # Reset cmds statuses
        for cmd in self.cmds:
            cmd[2] = 'pending'
        self.socket.emit('system_msg', {'data':f'Script successfully completed (Execution time = {round((endTime - startTime),2)}s)'})
        return True

    def generateCommand(self, data):
        # Expected data format: [set/pump/mix/wait/spectrometer, [input1, input2, input3], holdVal]
        # Main cmd list format: [(cmd, transcript), holdValue, status]
        if data[0] == "wait":
            result = self.addWait()
            if data[1] == '':
                holdVal = 0
            else:
                holdVal = int(data[1])
            self.cmds.append([result, holdVal, 'pending']) 
        elif data[0] == "spectrometer":
            result = [("Spectrometer Reading", "Server (1000) requests Spectrometer (1011) take spectrometer reading"), None, "pending"] # THIS IS A FUDGE TO GET THE SPECTROMETER WORKING !!!
            self.cmds.append(result)
        else:
            id = int(data[1][2])
            result = 'No Valid Command'
            hold = data[2]
            if (hold == None) or (hold == 'None'): # Depending on source of cmd generation call
                holdVal = None
            else:
                values = re.search('\(([^)]+)', hold).group(1)
                holdVal = [int(x) for x in values.split(',')]
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
        return result

    def handleResponse(self, msg):
        print(msg)
        if 'FREE' in msg:
            deviceID = int((re.search('sID(.*) rID', msg)).group(1))
            self.setDeviceStatus(deviceID, 'done')
            print(f'Updated device {deviceID} status at {time.time()}')
        elif 'SEN' in msg:
            if ' T' in msg: # Is a temperature sensor
                value = float((re.search('T(.) S(.*)]', msg)).group(2))
                self.tempReadings.append(value)
                deviceID = int((re.search('sID(.*) rID', msg)).group(1))
                self.setDeviceStatus(deviceID, 'done')
                self.lastReadingTime = time.time()
                filename = self.analysis.generateTempGraph(self.tempReadings)
                print(f'forwarding {filename}')
                self.socket.emit('tempPlot', {'data':filename})
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
        print(self.commandPacket)
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
        # [sID rID PK3 Y S{type} m{volume}]
        action = data[0]
        info = data[1]
        if action == 'pump':
            result = self.pumpVolume(info)
            return result
        else:
            raise KeyError
    
    def pumpVolume(self, info):
        print(info)
        self.packets.append(f'Y') # Pump module number
        syringeType = info[3]
        self.packets.append(f'S{syringeType}')
        if info[4] == 'pump':
            volume = int(re.findall(r'\d+', info[5])[0])
        else:
            volume = int(info[4])
        self.packets.append(f'm{volume}') # Pump volume
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' [S{syringeType}] pump {volume}mL'
        return self.assembleCmd()

class PeristalticPump(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        # [sID rID PK2 P m{volume}]
        action = data[0]
        info = data[1]
        if action == 'pump':
            result = self.pumpVolume(info)
            return result
        else:
            raise KeyError
    
    def pumpVolume(self, info):
        self.packets.append(f'P') # Pump module number
        if type(info[3]) == str:
            volume = int(re.findall(r'\d+', info[3])[0])
        else:
            volume = int(info[3])
        self.packets.append(f'm{volume}') # Pump volume
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' pump {volume}mL'
        return self.assembleCmd()

class MixerShutter(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)

    def parseCommand(self, data):
        # [sID rID PK3 M S{speed} D{direction}]
        action = data[0]
        info = data[1]
        if action == 'mix':  
            result = self.setMixer(info)
            return result
        elif action == 'set':
            result = self.setShutter(info)
            return result
        else:
            raise KeyError
    
    def setMixer(self, info):
        mode = info[3]
        self.packets.append(f'M') # Mixer module number
        direction = info[4]
        if direction == 'clockwise':
            dirVal = 1
        else:
            dirVal = 0
        match mode:
            case 'stop':
                speed = 0
            case 'slow':
                speed = 45
            case 'medium':
                speed = 80
            case 'fast':
                speed = 120
            case _:
                speed = 0
                mode = 'stop'
                self.transcript = 'An unexpected mixer speed has been encountered; speed has been set to 0 and mixer' # First half of error transcript
                return
        self.packets.append(f'S{speed}') # Mixer speed
        self.packets.append(f'D{dirVal}')
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' mix {direction} {mode}' # Add to transcript
        return self.assembleCmd()

    def setShutter(self, info):
        self.packets.append(f'I') # Shutter module number
        print(info)
        if info[3] in ['open', 'closed', 'middle']:
            mode = info[3]
        else:
            mode = info[5]
        match mode:
            case 'closed':
                posNum = 0
            case 'open':
                posNum = 1
            case 'partial':
                posNum = 2
            case _:
                posNum = 0
                mode = 'closed'
                self.transcript = 'An unexpected shutter position has been encountered; shutter has been' # First half of error transcript
                return
        self.packets.append(f'S{posNum}')
        self.setCmdBase(info[0], info[1], info[2]) # Cmd1
        self.transcript += f' set to {mode}' # Add to transcript
        return self.assembleCmd()

class Extraction(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        # [sID rID PK2 E S{angle}]
        # [sID rID PK2 P m{volume}]
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
        self.packets.append(f'P') # Extractor pump module number (static)
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
        # [sID rID PK2 V S{valve}]
        # [sID rID PK2 U S{valveCode}]
        action = data[0]
        info = data[1]
        if action == 'set':
            result = self.setValves(info)
            return result
        else:
            raise KeyError
    
    def setValves(self, info):
        output = info[3]
        self.setCmdBase(info[0], info[1], info[2]) # Cmd2  
        if output == "custom":
            self.packets.append(f'U') # Valve module number
            self.transcript += f' set valves to'
            for character in info[4]:
                if character == '0':
                    self.transcript += f' open'
                elif character == '1':
                    self.transcript += f' closed'
                else:
                    self.transcript += f' middle'
            self.packets.append(f'S{info[4]}')
        else:
            self.packets.append(f'V') # Valve module number
            self.transcript += f' set output to {output}' # Add to transcript
            self.packets.append(f'S{output}')      
        return self.assembleCmd()

class Sensor(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
            
    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        if action == 'spect':  
            result = self.takeSpectReading()
            return result
        else:
            raise KeyError
        return

    def takeTempReading(self):
        self.setCmdBase('server', '1000', self.id)
        self.packets.append(f'R') # Ping for temperature reading
        self.transcript += f' take temperature reading'
        return self.assembleCmd()
    
class Spectrometer(Component):
    def __init__(self, id, descriptor):
        super().__init__(id, descriptor)
    
    def parseCommand(self, data):
        action = data[0]
        info = data[1]
        if action == 'spect':  
            result = self.takeSpectReading()
            return result
        else:
            raise KeyError
        return

    def takeSpectReading(self): # To be completed
        try:
            frames = self.source.getSampleSet()
            Analysis.generateSpectGraph(frames)  
            self.setStatus('done')
            return 'filename'
        except Exception as e:
            print(f'Unfortunately, Spectrometer process has failed. Please try again.')
            print(e)
            pass
