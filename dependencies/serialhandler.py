# Serial component of obsolete Serial_lib.py
# Contains key commands for serial communication as per project serial definition
# File is currently in intermediate stage of development
# Commands will be re-introduced as their handling functionality is implemented

import serial, re, time
import serial.tools.list_ports

# Creates a Serial object to handle the protocol implementation
class Serial:
    def __init__(self):
        self.connections = []

    # Find which system COM port the chamber is connected to
    def FIND_COM_PORTS(self):
        successPorts = []
        ports = self.AVAILABLE_PORTS() # [COM1, COM2, etc]
        for port in ports:
            try:
                result = self.TEST_PORT(port)
                if result:
                    print('COM Port found:',port)
                    device = int(re.findall(r'sID(\d+) ', result)[0])
                    successPorts.append([port, device])
            except Exception as error:
                print('Operation failed, please try again')
                print('Error:',error)
                return False
        self.CLOSE_SERIAL_PORTS(successPorts)
        print(successPorts)
        return successPorts

    # List all currently available COM ports
    def AVAILABLE_PORTS(self):
        ports = []
        for port in ['COM%s' % (i+1) for i in range(255)]:
            try:
                s = serial.Serial(port)
                s.close()
                ports.append(port)
                print(ports)
            except (OSError, serial.SerialException):
                pass
        return ports       

    # Test COM port to see if component is connected
    # Todo: Establish a discrete handshake command 
    def TEST_PORT(self, port):
        try:
            print('Testing connection on port ',port)
            openSuccess = self.OPEN_SERIAL_PORT(port)
            print(openSuccess)
            if openSuccess:
                self.READ(port)
                try:
                    # Following command is incorrect! 
                    # Command has been modified for demo purposes
                    command = 'C'
                    writeSuccess = self.WRITE(port, command)
                    if writeSuccess != True:
                        return False
                    print('Sent handshake to serial ==> ', command)
                except Exception as error:
                    print('Error:',error)
                    self.connections[-1][1].close()
                    return False
                
                try:
                    response = self.READ(port)
                    print(response)
                    # Following requires update after handshake command is defined
                    for package in response:
                        if 'CONF' in package:
                            print('Device recognized on port',port)
                            self.CLOSE_SERIAL_PORT(port)
                            return package
                        else:
                            self.CLOSE_SERIAL_PORT(port)
                except:
                    self.connections[-1][1].close()
                    return False
                
        except(OSError,serial.SerialException,ValueError):
            return -1

    # Open a connection on a desired port 
    def OPEN_SERIAL_PORT(self, port):
        try:
            self.connections.append([port, serial.Serial(port=port,baudrate=115200,write_timeout=0.2,timeout=0.2)]) # Serial setup; should not be modified
            return self.connections[-1][1].isOpen()
        except IOError:
            print('Attempting to rectify IO Error')
            for connection in self.connections:
                if connection[0] == port:
                    print(connection)
                    connection[1].close()
                    self.OPEN_SERIAL_PORT(port)
                    break
        except (OSError,serial.SerialException,ValueError) as error:
            print('Encountered an error')
            print('Error: ' + repr(error))
            return None


    def OPEN_SERIAL_PORTS(self, ports):
        for port in ports:
            result = self.OPEN_SERIAL_PORT(port)
            if result:
                print(f'Success {port}')
            else:
                print(f'No success {port}')
            
    # Close COM port
    # This protects the system from receiving rogue commands
    def CLOSE_SERIAL_PORT(self, port):
        try:
            for index, connection in enumerate(self.connections):
                if connection[0] == port[0]:
                    connection[1].close()
                    print('Closed connection on port', port[0])
                    self.connections.pop(index)
                    break
        except:
            pass
    
    def CLOSE_SERIAL_PORTS(self, portList):
        for entry in portList:
            self.CLOSE_SERIAL_PORT(entry)
        self.connections = []

    # Send a command and ensure success
    def RUN_COMMAND(self, command):
        try:
            for connection in self.connections:
                writeSuccss = self.WRITE(connection[0], command)
                if writeSuccss == False:
                    raise Exception('Command write not successful')
                readSuccess = self.READ(connection[0])
                if readSuccess == False:
                    raise Exception('Failed to read response')
            return True
        except Exception as error:
            print('Failed to execute command')
            print('Error:',error)
            return False

    # Underlying method to send a command via serial
    def WRITE(self, port, command):
        try:
            for connection in self.connections:
                if connection[0] == port:
                    connection[1].write(command.encode('utf-8')) # Required encoding for a serial connection
                    break
            return True
        except TimeoutError:
            print('Write operation timed out')
            return False
        except Exception as error:
            print('Failed to send command to serial device')
            print('Error:',error)
            return False

    # Underlying method to receive a response
    def READ(self, port):
        try:
            for connection in self.connections:
                if connection[0] == port:
                    data = connection[1].read(128)
                    response = self.PARSE_LINES(data.decode('utf-8')) # Required encoding for a serial connection
                    connection[1].flush()
                    break
            return response
        except Exception as error:
            print('Failed to read response')
            print('Error:',error)
            return False

    # Parsing method
    # Identifies content within a response; further action not currently implemented
    def PARSE_LINES(self, s):
        result = []
        lines = s.splitlines()
        for entry in lines:
            result.append(entry[entry.find('['):entry.find(']')+1])
            if result == None:
                result = entry
        return lines