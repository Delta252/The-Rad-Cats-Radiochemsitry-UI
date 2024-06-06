### Definition of system components

import os, csv

class Component:
    def __init__(self):
        self.status = -1 # Uninitialized component

    def set_status(self, value: int):
        self.status = value
        # requires status definition
    
    def get_status(self):
        return self.status
    
    def define_status(self, value: int):
        return 'requires status definition'
    
    def command(self, opt: str):
        return opt

class Chamber(Component):
    # set_cabin_height(cm) > store cabin height (cm) and calculates dosage rate (Gy)
    # get_dose_rate() > returns dose_rate (Gy/min)
    # D2T(dosage) > converts dosage (Gy) to time (s)

    def __init__(self, cabin_height = 58.5):
        self.set_cabin_height(cabin_height)

    def set_cabin_height(self, cabin_height):
        if 41<=cabin_height<=58.5:
            self.cabin_height = cabin_height
            self.dose_rate = round(17745/((cabin_height-11.3)**2.095), 2)
        else:
            print('cabin height selected is out of boundaries (min = 41cm, max=58.5cm)')
    
    def get_dose_rate(self):
        print('dose rate = {} Gy/min', self.dose_rate)
        return self.dose_rate
    
    def D2T(self, dosage): 
        time = 60*dosage/self.dose_rate
        return time

class Pump(Component):
    # pump(volume) > provide a designated volume (uL)
    # poll() > ?
    # set_state(bool) > define if pump is currently functioning (True/False)
    # get_state() > return if pump is currently functioning (True/False)

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
    
    ### Requires definition:
    # def poll(self):
    #     if self.LDS!=None:
    #         self.LDS.poll()
    #         return self.LDS.state
    #     else: 
    #         return 1

    def set_state(self, state: bool):
        self.state = state
    
    def get_state(self):
        return self.state

# Requires clarification
class Valve(Component):
    # close() > close the valve
    # open() > open the valve
    # mid() > place valve in intermediate state
    # set_state(int) > define which state the valve is currently in (?)
    # get_state() > return which state the valve is currently in
    # valve_states() > assign values to valve array output states (?)

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

class Shutter(Component):
    # set_to(int) > set state to defined value (potentially redundant)
    # close() > close the shutter
    # open() > open the shutter
    # mid() > set shutter to partially open
    # set_state(int) > define shutter state
    # get_state() > return current shutter state

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

class Mixer(Component):
    # set_speed(string) > set mixer speed to predefined value
    # set_speed(int) > set mixer to custom value

    def __init__(self, device, ID, component_number: int, buffer):
        self.device = device
        self.ID = ID
        self.num = component_number
        self.buffer = buffer

    def set_speed(self, opt: str):
        speed = 0
        match opt:
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
                return 'error' # Placeholder for further error handling
        return self.buffer.IN([self.device, "[sID1000 rID{} PK3 M{} S{} D1]".format(self.ID, self.num, speed)])
    
    def set_speed(self, speed: int):
        return self.buffer.IN([self.device, "[sID1000 rID{} PK3 M{} S{} D1]".format(self.ID, self.num, speed)])

class Extract(Component):
    # set_slot(num) > set extractor to specified slot
    # get_slot() > return current slot

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

class Vessel(Component): 
    # This is honestly a puzzle to me
    # I'm leaving it here for the time being until I figure out what I'm meant to do with this

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
