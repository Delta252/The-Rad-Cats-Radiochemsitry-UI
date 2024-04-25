### Entry file into the webserver

from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, make_response, send_from_directory
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO
from wtforms import Form, StringField, TextAreaField, PasswordField, SelectField, validators
from dependencies.userhandler import UserHandler
from dependencies.comms import Comms
from dependencies.system import System
import os

app = Flask(__name__) # Create Flask app

uh = UserHandler() # Create object to handle user profiles

socketio = SocketIO(app, cors_allowed_origins="*") #IMPORTANT! Required for university/corporate networks where origin is not identical to host

sys = System(socketio)
comms = Comms(sys, socketio)

from dependencies.sockets import *

# Page routing

# Landing page; todo: determine what page appears depending on logged in status
@app.route('/')
def landing():
    return redirect(url_for('login'))

@app.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
   permitted_directory = './download/'
   return send_from_directory(directory=permitted_directory, path=filename, as_attachment=True)

# Main page to test system functionality
@app.route('/testing', methods=['GET','POST'])
def testing():
    return render_template('testing.html')

@app.route('/manual', methods=['GET','POST'])
def manual():
    return render_template('manual.html')

@app.route('/auto', methods=['GET','POST'])
def auto():
    return render_template('auto.html')

@app.route('/server-logoff', methods=['GET'])
def server_logoff():
    flash('You do not have access to this resource. Please log in.', 'danger')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET','POST'])
def profile():
    if request.method == 'POST':
        user = request.form['username']
        pswd_verification = request.form['oldPassword']
        pswd_candidate = request.form['newPassword']
        pswd_confirm = request.form['confPassword']

        if pswd_candidate != pswd_confirm:
            flash('New password does not match confirmation. Please try again.', 'danger')
            return redirect(url_for('profile'))

        success = uh.verifyUser(user, pswd_verification)

        if not success:
            # No success
            flash('Existing username and password combination not found.', 'danger')
            return redirect(url_for('profile'))
        
        uh.updatePassword(user, pswd_candidate)
        flash('Password successfully updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form fields
        username = request.form['username']
        pswd_candidate = request.form['password']

        success = uh.attemptLogin(username, pswd_candidate)

        if success:
            # Success
            session['logged_in'] = True # Session handling is a placeholder, further functionality to be implemented
            session['username'] = username
            session['sid'] = 'sid' + os.urandom(8).hex()

            flash('Login success', 'success')

            return redirect(url_for('testing'))
            
        else:
            flash('Username and password combination not found.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

#User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.user.data
        password = form.pswd.data

        uh.attemptRegister(username, password)

        flash('You are now registered and can log in.', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Custom validator to check if password is part of the 100k pwned list
def PasswordNotExists(self, field):
    with open('dependencies/100k-pswd.txt', encoding='utf-8') as myfile:
        if field.data in myfile.read():
                raise validators.ValidationError('Password is too common.')

# Form class for registration
class RegisterForm(Form):
    user = StringField('Username', [validators.Length(min=1, max=255, message='Invalid username length.')], render_kw={"placeholder": "Username *"})
    pswd = PasswordField('Password', validators=[validators.DataRequired(), validators.Length(min=8, message='Password too short.'), PasswordNotExists], render_kw={"placeholder": "Password *"},)
    confirm = PasswordField('Confirm Password.', [validators.EqualTo('pswd', message='Passwords do not match.')], render_kw={"placeholder": "Confirm Password *"},)

def main():
    app.secret_key = 'RadCatsRadiochemistry2024' # For sending cookies; required for Flask to run
    uh.logOffAll()
    # Below runs as HTTP, ssl_context required to run as HTTPS
    socketio.run(app, debug=True) #ssl_context=('dependencies/ssl/server.crt', 'dependencies/ssl/server.key')
 
# Core function call
if __name__ == '__main__':
    main()