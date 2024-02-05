import serial
import serial.tools.list_ports
from logger import Log

class Serial:
    def __init__(self):
        self.current_command = ''
        self.comport = -1
    
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

    def TEST_SERIAL_PORT(self, port):
        try:
            self.conn = serial.Serial(port=port,baudrate=115200,write_timeout=1,timeout=1)
            if self.conn.isOpen():
                try:
                    command = "[sID1000 rID1007 PK2 E1 S0]"
                    self.conn.write(command.encode('UTF-8'))
                    print("\nSent to Serial ==>", command)
                except:
                    self.conn.close()
                    return -1

                try:
                    data = self.conn.read(128)
                    response = data.decode('utf-8')
                    answer = self.DECODE_LINE(response)
                    if "FREE" in answer:
                        return port #success
                except:
                    self.conn.close()
                    return -1

        except (OSError,serial.SerialException,ValueError):
            return -1

    def SEND_COMMAND(self, command):
        try:
            self.conn.write(command.encode('utf-8'))

        except (OSError,serial.SerialException,ValueError):
            return -1

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
        if command[0]!="[" or command[-1]!="\n":
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
        operator = str(pk_split[1])
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
        operator = str(pk_split[1])
        senderID = str(senderID)
        out = senderID

        if n_pk==1:
            # single package commands
            match operator.split():
                case PK if "ERR" in operator:
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

                case PK if "ACK" in operator:
                    return (out + " Acknowledge")

                case PK if "BUSY" in operator:
                    return (out + " BUSY")

                case PK if "VALID" in operator: 
                    # temperature commands do not pass through buffer; Do not pop 
                    # print(self.current_command)
                    if not ('R' in self.current_command):
                        command = self.Comps.buffer.POP()
                        Log(self.DECODE_LINE(command))
                    return (out + " VALID")

                case PK if "FREE" in operator:
                    try:
                        self.Comps.arduinos[0].free()
                    except:
                        pass
                    return (out + " FREE")
                
                case PK if "R" in operator:
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
