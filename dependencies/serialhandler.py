# Serial component of obsolete Serial_lib.py
# Contains key commands for serial communication as per project serial definition
# File is currently in intermediate stage of development
# Commands will be re-introduced as their handling functionality is implemented

import serial
import serial.tools.list_ports

class Serial:
    def __init__(self):
        self.currentCommand = ''
        self.comPort = ''

    def FIND_COM_PORT(self):
        ports = self.AVAILABLE_PORTS()
        for port in ports:
            try:
                result = self.TEST_PORT(port)
                if result:
                    print('COM Port found:',self.comPort)
                    return True
            except Exception as error:
                print('Operation failed, please try again')
                print('Error:',error)
                return False
        return False 

    def AVAILABLE_PORTS(self):
        ports = []
        for port in ['COM%s' % (i+1) for i in range(256)]:
            try:
                s = serial.Serial(port)
                s.close()
                ports.append(port)
                print(ports)
            except (OSError, serial.SerialException):
                pass
        return ports       

    def TEST_PORT(self, port):
        try:
            print('Testing connection on port ',port)
            self.OPEN_SERIAL_PORT(port)
            if self.connection.isOpen():
                try:
                    # Following command is incorrect! 
                    # Command has been modified for demo purposes
                    command = '[sID1000 rID1008 PK3 Y1 S2000 D1]'
                    writeSuccess = self.WRITE(command)
                    if writeSuccess != True:
                        return False
                    print('Sent to serial ==> ', command)
                except Exception as error:
                    print('Error:',error)
                    self.connection.close()
                    return False
                
                try:
                    response = self.READ()
                    # Following requires update after handshake command is defined
                    if response.__contains__('FREE'):
                        print('Device recognized on port',port)
                        self.comPort = port
                        self.CLOSE_SERIAL_PORT()
                        return True
                except:
                    self.connection.close()
                    return False
                
        except(OSError,serial.SerialException,ValueError):
            return -1
        
    def OPEN_SERIAL_PORT(self, port):
        try:
            self.connection = serial.Serial(port=port,baudrate=115200,write_timeout=1,timeout=1)
            self.connection.isOpen()
        except IOError:
            self.connection.close()
            self.OPEN_SERIAL_PORT(port)
        except (OSError,serial.SerialException,ValueError):
            return None

    def CLOSE_SERIAL_PORT(self):
        try:
            self.connection.close()
            print('Closed connection on port',self.comPort)
        except:
            pass

    def RUN_COMMAND(self, command):
        try:
            writeSuccss = self.WRITE(command)
            if writeSuccss == False:
                raise Exception('Command write not successful')
            readSuccess = self.READ()
            if readSuccess == False:
                raise Exception('Failed to read response')
            return True
        except Exception as error:
            print('Failed to execute command')
            print('Error:',error)
            return False

    def WRITE(self, command):
        try:
            print('Sending command to serial:',command,flush=True)
            self.connection.write(command.encode('utf-8'))
            return True
        except TimeoutError:
            print('Write operation timed out')
            return False
        except Exception as error:
            print('Failed to send command to serial device')
            print('Error:',error)
            return False

    def READ(self):
        try:
            data = self.connection.read(128)
            response = self.PARSE_LINE(data.decode('utf-8'))
            print('Response:',response)
            return response
        except Exception as error:
            print('Failed to read response')
            print('Error:',error)
            return False

    def PARSE_LINE(self, s):
        result = s[s.find('['):s.find(']')+1]
        if result == None:
            return s
        return result