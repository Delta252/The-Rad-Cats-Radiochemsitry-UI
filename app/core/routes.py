from flask import Flask, render_template, flash, redirect, url_for, session, request, send_from_directory, Response
from werkzeug.utils import secure_filename
from . import core
from .forms import RegisterForm
from .. import uh
import app.dependencies.cameras as cameras
import os
# Page routing

# Landing page; todo: determine what page appears depending on logged in status
@core.route('/')
def landing():
    return redirect(url_for('core.login'))

@core.route('/video_feed')
def video_feed():
    return Response(cameras.video_stream(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

@core.route('/spect_feed')
def spect_feed():
    return Response(cameras.spect_stream(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

@core.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
   permitted_directory = './download/'
   return send_from_directory(directory=permitted_directory, path=filename, as_attachment=True)

# Main page to test system functionality
@core.route('/testing', methods=['GET','POST'])
def testing():
    return render_template('testing.html')

@core.route('/manual', methods=['GET','POST'])
def manual():
    return render_template('manual.html')

@core.route('/auto', methods=['GET','POST'])
def auto():
    return render_template('auto.html')

@core.route('/monitor', methods=['GET','POST'])
def monitor():
    return render_template('monitor.html')

@core.route('/server-logoff', methods=['GET'])
def server_logoff():
    flash('You do not have access to this resource. Please log in.', 'danger')
    return redirect(url_for('core.login'))

@core.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

@core.route('/profile', methods=['GET','POST'])
def profile():
    if request.method == 'POST':
        user = request.form['username-select']
        pswd_verification = request.form['oldPassword']
        pswd_candidate = request.form['newPassword']
        pswd_confirm = request.form['confPassword']

        if pswd_candidate != pswd_confirm:
            flash('New password does not match confirmation. Please try again.', 'danger')
            return redirect(url_for('core.profile'))

        success = uh.verifyUser(user, pswd_verification)

        if not success:
            # No success
            flash('Existing username and password combination not found.', 'danger')
            return redirect(url_for('core.profile'))
        
        uh.updatePassword(user, pswd_candidate)
        flash('Password successfully updated.', 'success')
        return redirect(url_for('core.profile'))
    return render_template('profile.html')

# User login
@core.route('/login', methods=['GET', 'POST'])
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

            return redirect(url_for('core.home'))
            
        else:
            flash('Username and password combination not found.', 'danger')
            return redirect(url_for('core.login'))

    return render_template('login.html')

#User registration
@core.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.user.data
        password = form.pswd.data

        uh.attemptRegister(username, password)

        flash('You are now registered and can log in.', 'success')

        return redirect(url_for('core.login'))
    return render_template('register.html', form=form)