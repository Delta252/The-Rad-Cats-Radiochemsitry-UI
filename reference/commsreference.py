import os, time, serial
from multiprocessing import Process, Manager
from serialhandler import Serial
from buffer import Buffer
from queue import Queue


class Comms():
    def __init__(self):
        self.serial = Serial()
        self.buffer = Buffer(self.serial)
        self.ID = 1000
        self.comport = -1 #no valid COM port

    def start(self):
        global arduinos
        self.current_command = ''
        self.buffer.RESET()

        try: 
            self.serial.CLOSE_SERIAL_PORT(arduinos)
        except:
            pass

        ports = self.serial.ID_PORTS_AVAILABLE()

        for p in ports:
            self.comport = self.serial.TEST_SERIAL_PORT(p)
            if self.comport != -1:
                print("COM Port found.")
                with Manager() as manager:
                    q = manager.Queue(-1)
                    t = Executor(q)
                    t.isDaemon = True
                    t.start()
                    return
            
        print("No COM Port found. Unable to start, please try again.")
        return

    def run_commands(self):
        while True:
            if self.buffer.LENGTH != 0:
                self.current_command = self.buffer.OUT()
                print(self.current_command) 
                
        return

    def create_command(self):
        return

    def send_command(self, command, *args):
        match command:
            case "set-position":
                slot = args[1]
                sender = 'sID1000'
                receiver = 'rID1007'
                

            case _:
                print("Error, undefined command")
                return
                
class Executor(Process):
    def __init__(self, q):
        self.queue = q
        Process.__init__(self)
    
    def run(self):
        try:
            run = True
            while run:
                if self.queue.qsize()>0:
                    cmd = self.queue.get()
                    if cmd == 'exit':
                        run = False
                    print('You have entered' + cmd)
                else:
                    print('waiting....')
                    time.sleep(1)
        except BrokenPipeError:
            return
        
if __name__ == '__main__':
    comms = Comms()
    comms.start()