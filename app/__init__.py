from flask import Flask
from flask_socketio import SocketIO
from .dependencies.userhandler import UserHandler
from .dependencies.system import System
from .dependencies.comms import Comms

socketio = SocketIO()

uh = UserHandler() # Create object to handle user profiles
sys = System(socketio)
comms = Comms(sys, socketio)

def create_app(debug=False):
    app = Flask(__name__) # Create Flask app
    app.debug = debug
    app.secret_key = 'RadCatsRadiochemistry2024' # For sending cookies; required for Flask to run

    from .core import core as core_blueprint
    app.register_blueprint(core_blueprint) 

    socketio.init_app(app, cors_allowed_origins="*")

    return app