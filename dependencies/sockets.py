# Socket.IO server-side functions
# This file handles commands received from user input in the webpages and forwards 
# required actions to corresponding destinations
# The creation of the Socket.IO server-side object is handled in `app.py`
import json
from __main__ import socketio, comms, sys, uh

#SocketIO
@socketio.on('connect')
def handle_connect():
    print('Connection established!')
    sys.updateFromDB()
    socketio.emit('after_connect')
    socketio.emit('update_cards', {'data':sys.define()})

@socketio.on('get-user')
def get_user():
    username = uh.getUsername()
    print(username)
    socketio.emit('set_user', {'data':username})

@socketio.on('get-theme')
def get_theme():
    theme = uh.getUserTheme()
    socketio.emit('update_theme', {'data':theme})

@socketio.on('send-theme')
def send_theme(data):
    theme = data[0]
    uh.updateUserTheme(theme)
    socketio.emit('update_theme', {'data':theme})

@socketio.on('ping')
def test_ping():
    print('Ping received!')
    socketio.emit('send_ping', {'data':'Test connection'})

@socketio.on('get-comms-status')
def get_comms_status():
    result = comms.isConnected
    socketio.emit('set_comms', data=(result))

@socketio.on('toggle-comms')
def toggle_comms():
    connection = comms.isConnected
    if connection:
        comms.stop()
    else:
        comms.start()
    connection = comms.isConnected
    socketio.emit('set_comms', data=(connection))

@socketio.on('remove-device')
def remove_device(data):
    sys.removeFromDB(data)
    socketio.emit('update_cards', {'data':sys.define()})

@socketio.on('add-device')
def remove_device(data):
    sys.addToDB(data[0], data[1])
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