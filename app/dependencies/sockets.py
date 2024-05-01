# Socket.IO server-side functions
# This file handles commands received from user input in the webpages and forwards 
# required actions to corresponding destinations
# The creation of the Socket.IO server-side object is handled in `app.py`
from .. import socketio, comms, sys, uh
from ..core.routes import session, request
from .analysis import Analysis
from pathlib import Path
import os, time

#SocketIO
@socketio.on('connect')
def handle_connect(ip):
    print('Connection established!')
    status = uh.getStatus(session['username'])
    sys.updateFromDB() 
    time.sleep(0.05) # Necessary delay to prevent loss of data as page is rendered
    socketio.emit('after_connect', {'data':status}, room=request.sid)
    socketio.emit('update_cards', {'data':sys.define()})
    socketio.emit('update_cmd_list', {'data':sys.cmds})

@socketio.on('get-user')
def get_user():
    username = session['username']
    allUsers = uh.getAllUsers()
    results = [username, allUsers]
    socketio.emit('set_user', {'data':results}, room=request.sid)

@socketio.on('update-username')
def update_user(data):
    currentUser = session['username']
    oldUsername = data[0]
    newUsername = data[1]
    uh.updateUsername(oldUsername, newUsername)
    allUsers = uh.getAllUsers()
    results = [currentUser, allUsers]
    socketio.emit('set_user', {'data':results}, room=request.sid)

@socketio.on('set-admin-status')
def set_admin_status(data):
    currentUser = session['username']
    username = data[0]
    adminStatus = data[1]
    print(adminStatus)
    uh.updateAdmin(username, adminStatus)
    allUsers = uh.getAllUsers()
    results = [currentUser, allUsers]
    print(results)
    socketio.emit('set_user', {'data':results}, room=request.sid)

@socketio.on('log-off')
def log_off(data):
    username = data
    uh.logOff(username)

@socketio.on('get-theme')
def get_theme():
    user = session['username']
    theme = uh.getUserTheme(user)
    socketio.emit('update_theme', {'data':theme}, room=request.sid)

@socketio.on('send-theme')
def send_theme(data):
    user = session['username']
    theme = data[0]
    uh.updateUserTheme(theme, user)
    socketio.emit('update_theme', {'data':theme}, room=request.sid)

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

@socketio.on('update-server')
def update_server(data):
    sys.updateServerID(data)

@socketio.on('generate-run-command') # Necessary to protect order of operations for manual control
def generate_command(data):
    command = sys.generateCommand(data)
    sys.cmds = []
    print(f'added command {command}')
    sys.q.put(command)

@socketio.on('add-cmd-list')
def add_cmds(data):
    command = sys.generateCommand(data)
    socketio.emit('update_cmd_list', {'data':sys.cmds})

@socketio.on('remove-cmd-number')
def remove_command(number):
    sys.cmds.pop(number-1)
    socketio.emit('update_cmd_list', {'data':sys.cmds})

@socketio.on('update-hold')
def update_hold(data):
    index = data[0]-1
    newHold = data[1]
    sys.cmds[index][1] = newHold

@socketio.on('verify-script')
def verify_script(data):
    result = sys.verifyScript()
    socketio.emit('handle_verify', {'data':result})
    if data:
        username = session['username']
        scriptFilename = sys.compileScript(username)
        socketio.emit('send_script',{'data':scriptFilename},room=request.sid)

@socketio.on('execute-script')
def execute_script():
    success = sys.executeScript()
    socketio.emit('complete_execute', {'data':success})

@socketio.on('run-commands')
def run_commands():
    sys.runCommands()

@socketio.on('upload-file')
def upload_file(file):
    savedir = './upload/'+session['username']
    Path(savedir).mkdir(parents=True, exist_ok=True)
    filepath = savedir+'/'+file[0]
    with open(filepath, 'wb') as binaryFile:
        binaryFile.write(file[1])
    sys.parseScript(filepath)
    socketio.emit('update_cards', {'data':sys.define()})
    socketio.emit('update_cmd_list', {'data':sys.cmds})

# Following commands are demo-specific placeholders, and will be replaced
@socketio.on('pull-syringe')
def get_comms_status():
    command = '[sID1000 rID1008 PK3 Y1 S2000 D1]'
    comms.runCommand(command)

@socketio.on('push-syringe')
def get_comms_status():
    command = '[sID1000 rID1008 PK3 Y1 S0 D0]'
    comms.runCommand(command)