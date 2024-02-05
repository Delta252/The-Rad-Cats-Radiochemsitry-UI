import datetime
from serialhandler import Serial

class Buffer:
    '''
    'First In, First Out' buffer \n
    use IN method to add new commands to the list\n
    use OUT method to execute commands from the list
    '''
    def __init__(self, Serial, size=100):
        self.buffer = []
        self.size = size
        self.blocked=False
        self.Serial = Serial
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

                        Serial.READ(self.Comps.Temp.device)
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

    def LENGTH(self):
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
