### Entry file into the webserver

from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_socketio import SocketIO, emit
from wtforms import Form, StringField, TextAreaField, PasswordField, SelectField, validators
from dependencies.userhandler import UserHandler
from dependencies.comms import Comms
import os

app = Flask(__name__) # Create Flask app

socketio = SocketIO(app)

uh = UserHandler() # Create object to handle user profiles

comms = Comms()

from dependencies.sockets import *

# Page routing

# Landing page; todo: determine what page appears depending on logged in status
@app.route('/')
def landing():
    return redirect(url_for('login'))

# Main page to test system functionality
@app.route('/testing', methods=['GET','POST'])
def testing():
    return render_template('testing.html')

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

            flash('Login success', 'msg')

            return redirect(url_for('testing'))
            
        else:
            flash('Username and password combination not found.', 'error')
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
def PasswordNotExists(field):
    with open('dependencies/100k-pswd.txt', encoding='utf-8') as myfile:
        if field.data in myfile.read():
                raise validators.ValidationError('Password is too common.')

# Form class for registration
class RegisterForm(Form):
    user = StringField('Username', [validators.Length(min=1, max=255, message='Invalid username length.')], render_kw={"placeholder": "Username *"})
    pswd = PasswordField('Password', validators=[validators.DataRequired(), validators.Length(min=8, message='Password too short.'), PasswordNotExists], render_kw={"placeholder": "Password *"},)
    confirm = PasswordField('Confirm Password.', [validators.EqualTo('pswd', message='Passwords do not match.')], render_kw={"placeholder": "Confirm Password *"},)

def main():
    app.secret_key = os.urandom(12).hex() # For sending cookies; required for Flask to run
    # Below runs as HTTP, ssl_context required to run as HTTPS
    socketio.run(app, debug=True) #ssl_context=('dependencies/ssl/server.crt', 'dependencies/ssl/server.key')

# Core function call
if __name__ == '__main__':
    main()