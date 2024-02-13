# Socket.IO server-side functions
# This file handles commands received from user input in the webpages and forwards 
# required actions to corresponding destinations
# The creation of the Socket.IO server-side object is handled in `app.py`
import json
from __main__ import socketio, comms, sys

#SocketIO
@socketio.on('connect')
def handle_connect():
    print('Connection established!')
    sys.updateFromDB()
    socketio.emit('after_connect')
    socketio.emit('update_cards', {'data':sys.define()})

@socketio.on('ping')
def test_ping():
    print('Ping received!')
    socketio.emit('send_ping', {'data':'Test connection'})

@socketio.on('get-comms-status')
def get_comms_status():
    result = comms.isConnected
    socketio.emit('send_comms_status', data=(result))

@socketio.on('toggle-comms')
def toggle_comms():
    connection = comms.isConnected
    if connection:
        result = comms.stop()
    else:
        result = comms.start()
    socketio.emit('send_comms_status', data=(result))
    socketio.emit('toggle_comms', {'data':result})

@socketio.on('remove-device')
def remove_device(data):
    sys.removeFromDB(data)
    socketio.emit('update_cards', {'data':sys.define()})

# Following commands are demo-specific placeholders, and will be replaced
@socketio.on('pull-syringe')
def get_comms_status():
    command = '[sID1000 rID1008 PK3 Y1 S2000 D1]'
    comms.runCommand(command)

@socketio.on('push-syringe')
def get_comms_status():
    command = '[sID1000 rID1008 PK3 Y1 S0 D0]'
    comms.runCommand(command)