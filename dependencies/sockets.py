from __main__ import socketio, comms

#SocketIO
@socketio.on('connect')
def handle_connect():
    print('Connection established!')
    socketio.emit('after_connect', {'data':'Test connection'})

@socketio.on('ping')
def test_ping():
    print('Ping received!')
    socketio.emit('send_ping', {'data':'Test connection'})
