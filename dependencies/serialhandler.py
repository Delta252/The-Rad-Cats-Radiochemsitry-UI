# Serial component of obsolete Serial_lib.py
# Contains key commands for serial communication as per project serial definition
# File is currently in intermediate stage of development
# Commands will be re-introduced as their handling functionality is implemented

import serial
import serial.tools.list_ports

# Creates a Serial object to handle the protocol implementation
class Serial:
    def __init__(self):
        self.currentCommand = '' # Stores next command

    # Find which system COM port the chamber is connected to
    def FIND_COM_PORT(self):
        ports = self.AVAILABLE_PORTS()
        for port in ports:
            try:
                result = self.TEST_PORT(port)
                if result:
                    print('COM Port found:',port)
                    return port
            except Exception as error:
                print('Operation failed, please try again')
                print('Error:',error)
                return -1
        return -1

    # List all currently available COM ports
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

    # Test COM port to see if component is connected
    # Todo: Establish a discrete handshake command 
    def TEST_PORT(self, port):
        try:
            print('Testing connection on port ',port)
            self.OPEN_SERIAL_PORT(port)
            if self.connection.isOpen():
                self.READ()
                try:
                    # Following command is incorrect! 
                    # Command has been modified for demo purposes
                    command = 'C'
                    writeSuccess = self.WRITE(command)
                    if writeSuccess != True:
                        return False
                    print('Sent handshake to serial ==> ', command)
                except Exception as error:
                    print('Error:',error)
                    self.connection.close()
                    return False
                
                try:
                    response = self.READ()
                    # Following requires update after handshake command is defined
                    for package in response:
                        if 'CONF' in package:
                            print('Device recognized on port',port)
                            self.comPort = port
                            self.CLOSE_SERIAL_PORT()
                            return True
                except:
                    self.connection.close()
                    return False
                
        except(OSError,serial.SerialException,ValueError):
            return -1

    # Open a connection on a desired port 
    def OPEN_SERIAL_PORT(self, port):
        try:
            self.connection = serial.Serial(port=port,baudrate=115200,write_timeout=1,timeout=1) # Serial setup; should not be modified
            self.connection.isOpen()
        except IOError:
            self.connection.close()
            self.OPEN_SERIAL_PORT(port)
        except (OSError,serial.SerialException,ValueError):
            return None

    # Close COM port
    # This protects the system from receiving rogue commands
    def CLOSE_SERIAL_PORT(self):
        try:
            self.connection.close()
            print('Closed connection on port',self.comPort)
        except:
            pass
    
    # Send a command and ensure success
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

    # Underlying method to send a command via serial
    def WRITE(self, command):
        try:
            self.connection.write(command.encode('utf-8')) # Required encoding for a serial connection
            return True
        except TimeoutError:
            print('Write operation timed out')
            return False
        except Exception as error:
            print('Failed to send command to serial device')
            print('Error:',error)
            return False

    # Underlying method to receive a response
    def READ(self):
        try:
            data = self.connection.read(128)
            response = self.PARSE_LINES(data.decode('utf-8')) # Required encoding for a serial connection
            self.connection.flush()
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