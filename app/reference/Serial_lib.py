import serial
import serial.tools.list_ports
import csv, datetime, os, requests, cv2, random, time
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import style
from chump import Application
matplotlib.use("TkAgg")

style.use("ggplot")
path = os.path.dirname(os.path.realpath(__file__))


class MyStr(str):
    def __eq__(self, other):
        return self.__contains__(other)

class Comms:
    def __init__(self, Comps):
        self.Comps = Comps
        self.current_command = ''
    
    def ID_PORTS_AVAILABLE(self):
        devices = []
        for port in ['COM%s' % (i + 1) for i in range(256)]:
            try:
                s = serial.Serial(port)
                s.close()
                devices.append(port)
                print('port found: ', port)
            except (OSError, serial.SerialException):
                pass
        
        return devices

    def CLOSE_SERIAL_PORT(self, arduinos):
        try:
            for arduino in arduinos:
                arduino.device.close()
                print('arduino closed ', arduino.device)
        except:
            pass

    def OPEN_SERIAL_PORT(self, DEV):
        try:
            Dev = serial.Serial(port=DEV,baudrate=115200, timeout=.1)
            Dev.isOpen()
        except IOError:
            Dev.close()
            Dev = serial.Serial(port=DEV,baudrate=115200, timeout=.1)
            Dev.isOpen()
        except (OSError, serial.SerialException,ValueError):
            return None
        
        return Dev

    def OPEN_SERIAL_PORTS(self, DEVS):
        DEVICES = []
        try:
            for i in range(len(DEVS)):
                try:
                    Dev = serial.Serial(port=DEVS[i],baudrate=115200, timeout=.1)
                    print(Dev)
                    Dev.isOpen()
                    DEVICES.append(Dev)
                except IOError:
                    Dev.close()
                    Dev = serial.Serial(port=DEVS[i],baudrate=115200, timeout=.1)
                    Dev.isOpen()
                    DEVICES.append(Dev)
                except (OSError, serial.SerialException,ValueError):
                    pass
            
            return DEVICES
        except:
            return []

    def SERIAL_READ_LINE(self, DEV):
        try:
            Incoming_Data = DEV.readlines()
            Incoming_Data = self.DECODE_LINES(Incoming_Data)
            self.FLUSH_PORT(DEV) 
            return Incoming_Data
        except (NameError,IOError,ValueError):
            print('error in Serial_Read_Line')
            pass
        return [-1]

    def DECODE_LINES(self, cmd_list):
        for i in range(0,len(cmd_list)):
            cmd_list[i] = cmd_list[i].decode('UTF-8').replace('\r\n','')
            cmd_list[i] = self.DECODE_LINE(cmd_list[i])
            print(cmd_list[i])
        return cmd_list

    def DECODE_LINE(self, command):
        if command[0]!="[" or command[-1]!="]":
            return "- " + command 
        cmd_strip = command[1:-1]
        cmd_split = cmd_strip.split(" ", 2)
        senderID = cmd_split[0][3:]
        receiveID = cmd_split[1]
        PK = cmd_split[2]
        return self.DECODE_PACKAGE(senderID, PK)

    def PRETTY_LINE(self, command):
        if command[0]!="[" or command[-1]!="]":
            return "- " + command 
        cmd_strip = command[1:-1]
        cmd_split = cmd_strip.split(" ", 2)
        senderID = cmd_split[0][3:]
        receiveID = cmd_split[1]
        PK = cmd_split[2]
        n_pk = int(PK[2:4])
        pk_split = PK.split(" ", n_pk)
        operator = MyStr(pk_split[1])
        out = str(senderID)
        match operator[0]:
            case "P":
                #Pump: [sID... rID PK3 P1 m10.2]
                num = int(pk_split[1][1])
                vol = float(pk_split[2][1:])
                return "Pump {}: volume {} ".format(num, vol)
            
            case "V":
                #Valve: [sID... rID PK2 V1 S]
                num = pk_split[1][1]
                state = pk_split[2][1]
                return "Valve {}: state {} ".format(num, state)
            
            case "I":
                #Shutter: [sID... rID PK2 V1 S]
                num = pk_split[1][1]
                state = pk_split[2][1]
                return "Shutter state {} ".format(state)
            
            case "M":
                #mixer
                num = pk_split[1][1]
                state = pk_split[2][1:]
                return "Mixer state {}".format(state)
            
            case "E":
                num = pk_split[1][1]
                state = pk_split[2][1:]
                return "Extract state {} ".format(state)
            
            case _:
                return out + " unrecognised cmd package: " + PK

    def DECODE_PACKAGE(self, senderID, PK):
        n_pk = int(PK[2:4])
        pk_split = PK.split(" ", n_pk)
        operator = MyStr(pk_split[1])
        senderID = str(senderID)
        out = senderID

        if n_pk==1:
            # single package commands
            match operator:
                case "ERR":
                    out += " ERROR"
                    match operator[3]:
                        case "0":
                            out += " 0: Incorrect packet format"
                        case "1":
                            out += " 1: Packet missing items"
                        case "2":
                            out += " 2: Incorrect Device ID"
                        case "3":
                            out += " 3: Incorrect Sender ID"
                        case "4":
                            out += " 4: System is in error state."
                        case _:
                            out += "Unkown Error number {}".format(operator[3])
                    Log(out)
                    return out

                case "ACK":
                    return (out + " Acknowledge")

                case "BUSY":
                    return (out + " BUSY")

                case "VALID": 
                    # temperature commands do not pass through buffer; Do not pop 
                    # print(self.current_command)
                    if not ('R' in self.current_command):
                        command = self.Comps.buffer.POP()
                        Log(self.DECODE_LINE(command))
                    return (out + " VALID")

                case "FREE":
                    try:
                        self.Comps.arduinos[0].free()
                    except:
                        pass
                    return (out + " FREE")
                
                case "R":
                    return (out + " SEN")
                
                case _:
                    return out + " unrecognised package: " + PK
        else:
            #multi package commands 
            match operator[0]:
                case "P":
                    #Pump: [sID... rID PK3 P1 m10.2]
                    num = int(pk_split[1][1])
                    vol = float(pk_split[2][1:])
                    if num==(1 or 2 or 3):
                        try: 
                            self.Comps.ves_in[num-1].sub(float(vol))
                            self.Comps.ves_main.add(float(vol))
                        except:
                            pass
                    if num==4:
                        self.Comps.ves_main.sub(float(vol))
                        self.Comps.ves_out[self.Comps.valves.output_vessel].add(float(vol))
                    return "Pump {}: volume {} ".format(num, vol)
                
                case "V":
                    #Valve: [sID... rID PK2 V1 S]
                    num = pk_split[1][1]
                    state = pk_split[2][1]
                    print("Valve num {}, state {} ".format(num, state))
                    return "Valve {}: state {} ".format(num, state)
                
                case "I":
                    #Shutter: [sID... rID PK2 V1 S]
                    num = pk_split[1][1]
                    state = pk_split[2][1]
                    self.Comps.shutter.set_state(state)
                    return "Shutter state {} ".format(state)
                
                case "M":
                    #mixer
                    num = pk_split[1][1]
                    state = pk_split[2][1]
                    print("Mixer num {}, state {} ".format(num, state))
                    return "Mixer state {}".format(state)
                
                case "E": 
                    num = pk_split[1][1]
                    state = pk_split[2][1:]
                    self.Comps.extract.current_slot = state
                    return "Extract state {} ".format(state)
                
                case "S": 
                    out += " sensors "

                    for idx in range(len(pk_split)):
                        try:
                            match pk_split[idx][0]:
                                case 'T':
                                    T = float(pk_split[idx+1][1:])
                                    self.Comps.Temp.new_temp(T)
                                    out += "Temp {} °C".format(T)
                                case 'B':
                                    bub_num = int(pk_split[idx][1])
                                    bub_state = pk_split[idx+1][1:]
                                    self.Comps.Bubble[int(pk_split[idx][1])-1] = pk_split[idx+1][1:]
                                    out += "Bubble {}, state {}".format(bub_num, bub_state)
                                case 'L':
                                    lds_num = int(pk_split[idx][1])
                                    lds_state = int(pk_split[idx+1][1])
                                    
                                    for pump in self.Comps.pumps:
                                        try:
                                            if pump.ID == senderID:
                                                pump.LDS.state = lds_state
                                                break
                                        except:
                                            pass
                                    out += " LDS {} state {}".format(lds_num, lds_state)

                                case _:
                                    pass
                        except:
                            print('Sensor polling error')
                    return out

                case _:
                    print("operator ",operator)
                    return out + " unrecognised cmd package: " + PK

    def SERIAL_WRITE_LINE(self, DEV,COMMAND):
        try:
            print("\nSent to Serial ==>", COMMAND)
            DEV.write(COMMAND.encode('UTF-8'))
            return 1
        except:
            return -1

    def WRITE(self, DEV, COMMAND):
        self.current_command = COMMAND
        # print('current com', self.current_command)
        STATE = -1
        TRY = 0
        while(STATE == -1):
            STATE = self.SERIAL_WRITE_LINE(DEV,COMMAND)
            TRY = TRY + 1
            if(TRY>10):
                return -1
        return STATE

    def READ(self, DEV):
        STATE = -1
        TRY = 0
        try:
            while(STATE == -1):
                if (DEV.inWaiting() > 0):
                    STATE = self.SERIAL_READ_LINE(DEV)
                TRY = TRY + 1
                if(TRY>10):
                    return -1
            return STATE
        except:
            pass

    def FLUSH_PORT(self, DEV):
        try:
            for i in range(len(DEV)):
                print('flushed input')
                DEV[i].flushInput()
        except:
            pass

class Buffer:
    '''
    'First In, First Out' buffer \n
    use IN method to add new commands to the list\n
    use OUT method to execute commands from the list
    '''
    def __init__(self, Comms, Comps, size=100):
        self.buffer = []
        self.size = size
        self.blocked=False
        self.Comms = Comms
        self.Comps = Comps
        self.current_device = None
    
    def IN(self, device_command: list):
        '''
        add new command to the buffer list
        '''
        if len(self.buffer)<self.size:
            self.buffer.append(device_command)
        else: 
            print("buffer full")

    def OUT(self):
        '''
        Exectute next command in the buffer List
        3 types : Package, Block, Notification
        '''
        try: 
            if len(self.buffer) and self.Comps.arduinos[0].state==False:
                if (not self.blocked):
                    if self.buffer[0][0]=='WAIT':
                        print('Blocked')
                        self.START_BLOCK()
                    elif self.buffer[0][0]=='NOTIF':
                        self.phone.send(self.buffer[0][1])
                        self.POP()
                        return
                    else:
                        dev, com = [*self.buffer[0]]
                        self.Comms.WRITE(dev, com)
                        self.Comps.arduinos[0].busy()
                        self.current_device = self.buffer[0][0]
                    
                if self.blocked:
                    if datetime.datetime.now().timestamp()>self.time_to_unblock:
                        print('Unblocked')
                        self.blocked=False
                        self.POP()

                        Comms.READ(self.Comps.Temp.device)
                        print('flushed input')
        except:
            pass
            
    def POP(self):
        '''Delete executed/Validated command from list'''
        if len(self.buffer):
            print("pop")
            device, command = self.buffer.pop(0)
            return command
    
    def POP_LAST(self):
        if len(self.buffer):
            device, command = self.buffer.pop(-1)
            print(command)
            return command
        
    def READ(self):
        '''returns the current list of commands in the buffer'''
        command_list=[]
        device_list=[]
        for content in self.buffer: 
            device_list.append(content[0])
            command_list.append(self.Comms.PRETTY_LINE(content[1]))
        return command_list

    def Length(self):
        #print("length of buffer:", len(self.buffer))
        return len(self.buffer)

    def RESET(self):
        self.buffer = []

    def BLOCK(self, seconds: float):
        self.seconds = seconds
        self.buffer.append(['WAIT', str(seconds)])
    
    def START_BLOCK(self):
        start_time = datetime.datetime.now().timestamp()
        self.time_to_unblock = self.seconds + start_time
        self.blocked = True

    def NOTIFY(self, text = 'DONE'):
        self.buffer.append(['NOTIF', text])
        
def Log(command, file_name = "commands.csv"):
    nowTime = datetime.datetime.now()
    time = nowTime.strftime("%H:%M:%S")

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name), mode ="a", newline='') as csvfile:
        writer = csv.writer(csvfile) 
        writer.writerow([time, command])

def delete_file(file_name = "commands.csv"):
    try:os.remove(os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name))
    except:pass

def save_detail(names: list, volumes: list, file_name = "details.csv"):
    try:os.remove(os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name))
    except:pass

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name), mode ="a", newline='') as csvfile:
        for i in range(len(names)):
            writer = csv.writer(csvfile) 
            writer.writerow([names[i], volumes[i]])

def vessel_detail(ent_Rn, ent_Rv):
    names=[]
    volumes=[]
    for i in range(len(ent_Rn)):
        try:
            names.append(ent_Rn[i].get())
            volumes.append(ent_Rv[i].get())
        except:pass
    save_detail(names, volumes)
    return

def read_detail(filename:str):
    try:
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), filename), mode = 'r') as csvfile:
            array = list(csv.reader(csvfile, delimiter = ","))
            n = len(array)
            first_col = [0 for i in range(n)]
            second_col = [0 for i in range(n)]
            for i in range(n):
                first_col[i]= array[i][0]
                second_col[i]= array[i][1]
        return first_col, second_col
    except:
        return ['']*3,['']*3
    
def WASH(Comps, n=1, volume = 20):
    for i in range(n):
        #close the shutter, put water solution in the reactor, mix, extract to waste
        try:
            Comps.shutter.close()
            Comps.mixer.slow() 
            Comps.pumps[3].pump(volume)
            Comps.buffer.BLOCK(5)
            Comps.mixer.stop()
            valve_states(Comps.valves, 0)
            Comps.pumps[4].pump(-(volume*2))
            Comps.extract.set_slot(5)
            Comps.pumps[5].pump((volume*2))
            Comps.buffer.BLOCK(15)
        except:
            print('WASHING ERROR')
            pass

class Cabin():
    """
    set_cabin_height(cm): store cabin height and calculates dosage rate
    get_dose_rate: returns dose_rate
    D2T(dosage): converts dosage to time
    """
    def __init__(self, cabin_height = 58.5):
        self.set_cabin_height(cabin_height)

    def set_cabin_height(self, cabin_height):
        """Update cabinet height and Calculate dosage rate (Gy/min)"""
        if 41<=cabin_height<=58.5:
            self.cabin_height = cabin_height
            self.dose_rate = round(17745/((cabin_height-11.3)**2.095), 2)
        else:
            print('cabin height selected is out of boundaries')
    
    def get_dose_rate(self):
        """return Dosage rate for specified cabinet height (Gy/min) """
        print('dose rate = {} Gy/min', self.dose_rate)
        return self.dose_rate
    
    def D2T(self, dosage): 
        """Convert Dosage (Gy) to radiation time (s)"""
        time = 60*dosage/self.dose_rate
        return time

class notif():
    def __init__(self, app_token = 'aobomapmrh4rmprq1mpy3wza5efsfs', user_key = 'umrzw8s6div1ucpe2getdb9ucaz1f9'):
        self.app_token=app_token
        self.user_key=user_key
        try:
            self.app = Application(self.app_token)
            self.user = self.app.get_user(self.user_key)
            print('App: ', self.app.is_authenticated,', User: ', self.user.is_authenticated, '\nName = ', self.user.devices)
        except:
            print('No Phone detected: check apptoken / user key / wifi connection')
        # self.send('MVP loading')
    
    def set_token(self, app_token, user_key):
        self.app_token=app_token
        self.user_key=user_key
        self.app = Application(self.app_token)
        self.user = self.app.get_user(self.user_key)
    
    def send(self, text: str):
        try:
            message = self.user.send_message(text)
            # print(message.is_sent, message.id, str(message.sent_at))
        except:
            pass

    def image(self, image, text= 'camera'):
        cv2.imshow(image)
        r=requests.post("https://api.pushover.net/1/messages.json", data = {
        "token": self.app_token,
        "user": self.user_key,
        "message": text
        },
        files = {
        "attachment": ("image.jpg", image, "image/jpeg")
        })
#components
class Pump:
    def __init__(self, device, ID, component_number: int, buffer, LDS=None):
        self.device = device
        self.ID = ID
        self.buffer = buffer
        self.num = component_number
        self.state = False
        self.LDS = LDS
    
    def pump(self, volume: float):
        if volume==0.0:
            return -1
        else:
            self.buffer.IN([self.device, "[sID1000 rID{} PK2 P{} m{:.3f}]".format(self.ID, self.num, volume)])
            return 1
    
    def poll(self):
        if self.LDS!=None:
            self.LDS.poll()
            return self.LDS.state
        else: 
            return 1

    def set_state(self, state: bool):
        """Param bool state: set False->idle, True->used"""
        self.state = state
    
    def get_state(self):
        return self.state

class Valve:
    output_vessel = 0
    def __init__(self, device, ID, component_number: int, buffer):
        self.device = device
        self.ID = ID
        self.num = component_number
        self.buffer = buffer
        self.state = False
         
    def close(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK2 V{} S0]".format(self.ID, self.num)])

    def open(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK2 V{} S1]".format(self.ID, self.num)])

    def mid(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK2 V{} S2]".format(self.ID, self.num)])

    def set_state(self, state: int):
        """Param bool state: set False->closed, True->open"""
        self.state = state
    
    def get_state(self):
        return self.state
    
def valve_states(Valves, out: int):
    Valves[0].output_vessel = out
    match out:
        case 0: states = '02222'
        case 1: states = '10222'
        case 2: states = '11022'
        case 3: states = '11102'
        case 4: states = '11110'
        case 5: states = '11111'
        case _: 
            print("error unknown valve state")
            return
    for idx in range(0, len(states)):
        match int(states[idx]):
            case 0: Valves[idx].close()
            case 1: Valves[idx].open()
            case 2: Valves[idx].mid()
            case _: pass

class Shutter:
    def __init__(self, device, ID, component_number: int, buffer):
        self.device = device
        self.ID = ID
        self.num = component_number
        self.buffer = buffer
        self.state = 0
    
    def set_to(self, state: int):
        if 0<=state<=2:
            self.buffer.IN([self.device, "[sID1000 rID{} PK2 I{} S{}]".format(self.ID, self.num, state)])

    def close(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK2 I{} S1]".format(self.ID, self.num)])

    def open(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK2 I{} S0]".format(self.ID, self.num)])

    def mid(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK2 I{} S2]".format(self.ID, self.num)])

    def set_state(self, state: int):
        self.state = state
    
    def get_state(self):
        return self.state

class Mixer:
    def __init__(self, device, ID, component_number: int, buffer):
        self.device = device
        self.ID = ID
        self.num = component_number
        self.buffer = buffer

    def slow(self):
        return self.buffer.IN([self.device, "[sID1000 rID{} PK3 M{} S{} D1]".format(self.ID, self.num, 45)])
    
    def mix(self):
        return self.buffer.IN([self.device, "[sID1000 rID{} PK3 M{} S{} D1]".format(self.ID, self.num, 60)])
    
    def fast(self):
        self.buffer.IN([self.device, "[sID1000 rID{} PK3 M{} S{} D1]".format(self.ID, self.num, 200)])

    def stop(self):
        return self.buffer.IN([self.device, "[sID1000 rID{} PK3 M{} S{} D1]".format(self.ID, self.num, 0)])

class Extract:
    def __init__(self, device, ID, component_number: int, buffer, n_slots, angle=180):
        self.device = device
        self.ID = ID
        self.num = component_number
        self.buffer = buffer
        self.n_slots = n_slots
        self.step_angle = angle/(n_slots-1)
        self.current_slot = 0

    def set_slot(self, slot):
        if slot<=self.n_slots and slot>0:
            angle = (slot-1)*self.step_angle
            self.buffer.IN([self.device, "[sID1000 rID{} PK2 E{} S{}]".format(self.ID, self.num, angle)])
        else:
            print('Slot number', slot, 'is out of scope')

    def get_slot(self):
        return self.current_slot

class Vessel: 
    def __init__(self, volume = 10.0, liquid_name = 'none'):
        self.vol = volume
        self.name = liquid_name
        self.path = os.path.dirname(os.path.realpath(__file__))

    def save_detail(self, names: list, volumes: list, file_name = "details.csv"):
        try:
            os.remove(os.path.join(self.path, 'static\\', file_name))
        except:
            pass

        with open(os.path.join(self.path, 'static\\', file_name), mode ="a", newline='') as csvfile:
            for i in range(len(names)):
                writer = csv.writer(csvfile) 
                writer.writerow([names[i], volumes[i]])
    
    def vessel_detail(self, ent_Rn, ent_Rv):
        names=[]
        volumes=[]
        for i in range(len(ent_Rn)):
            try:
                names.append(ent_Rn[i].get())
                volumes.append(ent_Rv[i].get())
            except:pass
        self.save_detail(names, volumes)
        return
    
    def new_label(self, label):
        self.labels.append(label)

    def sub(self, volume: float):
        self.vol = self.vol - volume
    
    def add(self, volume: float):
        self.vol = self.vol + volume

class LDS:
    def __init__(self, device, ID, Comms):
        self.device = device
        self.ID = ID
        self.Comms = Comms
        self.state=False
        self.tk = tk

    def poll(self):
        try:
            self.Comms.WRITE(self.device, "[sID1000 rID{} PK1 R]".format(self.ID))
        except:
            pass
        time.sleep(0.01)
        self.Comms.READ(self.device)
    
    def get_state(self):
        return self.state
   
class Temp:
    def __init__(self, device, ID, Comms):
        self.device = device
        self.ID = ID
        self.Comms = Comms
        self.graphs = []
        self.labels = []
        # self.get_all()
        self.xar = []
        self.yar = []
        self.blocked = True
        now = datetime.datetime.now()
        current_time = now.strftime("%H_%M_%S")
        name = 'Temperature' + current_time +'.csv'
        self.path = os.path.join(path, 'results\\', name)
        f = open(self.path, 'w')
        writer = csv.writer(f)
        writer.writerow(["Time", "temperature"])
        f.close()
    
    def poll(self):
        
        try:
            self.Comms.WRITE(self.device, "[sID1000 rID{} PK1 R]".format(self.ID))
        except:
            pass
        time.sleep(0.01)

    def new_temp(self, Temp = 0.0):
        f = open(self.path, 'a')
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        try:
            writer = csv.writer(f)
            writer.writerow([current_time, Temp])
        except:
            pass
        f.close()
        self.xar.append(current_time)
        self.yar.append(Temp)
        self.update_graphs()
        self.update_labels()

    def get_last(self):
        # print(self.yar[-1])
        return self.yar[-1]
    
    def new_label(self, label):
        self.labels.append(label)

    def update_labels(self):
        for label in self.labels:
            try:
                label.configure(text='T = {} °C'.format(self.yar[-1]), font = ("Consolas", 18, "normal"))
            except:
                print('label not updated')

    def new_graph(self, graph):
        # Add new graph object instance to list of graphs
        self.graphs.append(graph)
        self.update_graphs()
    
    def update_graphs(self):
        # update all the graphs at once
        for graph in self.graphs:
            graph.animate(self.yar)

class Graph:
    '''
    Add instance of a graph in a Tkinter frame
    with MatplotLib package
    '''
    def __init__(self, frame, visible=20):
        self.visible=visible
        self.f = Figure(figsize=(5,5), dpi=100)
        self.a = self.f.add_subplot(111)
        canvas = FigureCanvasTkAgg(self.f, frame)
        canvas.draw()
        canvas.get_tk_widget().place(relx=0.5, rely=0.5, relwidth=1, relheight=1, anchor='center')
        self.canvas=canvas
        self.animate()
    
    def animate(self, yar=[0]):
        if len(yar)>self.visible:
            yar = yar[-self.visible:]
        self.a.clear()
        self.a.plot(yar)
        self.canvas.draw()

class Components:
    def __init__(self):
        self.modules = ['no arduino connected']
    pass
    
class Nano:
    state = False
    def __init__(self, device, ID, port='', pump = None):
        self.device = device
        self.ID = ID
        self.components = ""
        self.message = ""
        self.port=port
        self.pump = pump
    
    def get_id(self):
        #print(self.ID)
        return self.ID

    def get_device(self):
        return self.device

    def add_component(self, components: str):
        self.components = components
    
    def get_components(self):
        return self.components
        
    def toggle_state(self):
        self.state = not self.state
    
    def free(self):
        self.state = False

    def busy(self):
        self.state = True
    
    def add_message(self, message):
        self.message = message
    
    def read_last(self):
        return self.message

