This document describes the key features of the Arcadius Radiochemistry Reactor software system. This system encompasses the top level UI, composed of the front-end interface written in `HTML/CSS`, the underlying server written in `Python` that hosts the interface and interacts with user input, and the base level firmware and communication protocol, likewise written in `Python`.

# Project Overview
## Dependencies

The user interface has a number of key dependencies required to make it run, as listed below:

- `Python 3` >> The minimum requirement is Python version `3.10`; however, the system was built on Python `3.11.6`, so that is the version that is recommended for use. Later version of Python, such as the current latest release `3.12` are not supported due to underlying package dependencies.
- `pip` >> Pip is used for installation and updating of packages. Although not strictly necessary to run the user interface itself, it is recommended to be installed in order to run the `requirements.txt` file, which ensures that all following packages are installed and up-to-date.
- `Flask for Python` >> Flask is the back-end Python package that ensures that the webserver is capable of rendering HTML/CSS files correctly. It is installed as part of `requirements.txt`.
- `WTForms for Flask` >> WTforms is the form handler that interprets user input from the user interface. It is installed as part of `requirements.py`, but can also be updated manually using `pip install -U flask-WTF`
- `Argon2` >> Argon 2 is installed as `argon2-cffi` and is used for password encryption. It is installed as part of `requirements.txt` but can also be added manually.
- `PySerial` >> This is the underlying package for serial communications, and it ensures that the custom serial library implemented as part of this project is functioning. It is likewise installed as part of `requirements.txt`.
- `Flask Socket.IO` >> This package handles the server of socket connections. This is essential to preventing constant page regenerations when interacting with user input. This is installed as the `flask-socketio` package as part of `requirements.txt`. A webpage equivalent file, which handles the other half of a socket connection, is stored under a `JavaScript` file in the project `dependencies/static/js/socket.io.js` file.

This list of dependencies contains the critical packages, but is not exhaustive. It is set to be expanded as the project continues to be developed.

## Installation

In order to run this project, the above dependencies must first be installed. This typically can be represented by the following process:

1. Install `Python 3`. It is recommended that this package is installed from the official Python project web portal, which can be found at `python.org`. As is mentioned in the `Project Dependencies` section, this project currently runs on `Python 3.11.6`, so that is the version that should be installed. If other versions are installed on a given machine, the specific interpreter must first be selected. This can be done by first running the command `python -3.11.6` and then continuing the process.
2. Install `pip`. Typically, `pip` is already installed alongside any existing `Python` installation. If this is not the case, specific instructions can be found at `pip.pypa.io/en/stable/installation/`
3. Run `pip install -r requirements.txt`. This installs the dependency packages as well as the correct versions

## Running The Application

Running the application can either be done from the command line or from a development environment such as Visual Studio Code. 

To run it from the command line, navigate to the directory where the project is located and run `python app.py`.

To run it from a development environment, open the project folder, open `app.py` and set the desired `Debug` value, found at the bottom in the `main()` function, and click run.

Once either of these two options has been completed, the web host will launch and the command prompt should show a message saying `Serving Flask App 'app'; Running on http://XXX.XXX.XXX.XXX:XXXX`. Once this message appears, navigate to the address listed in your preferred web browser and utilise the system.

Currently, the second option is recommended, since the options to enable SSL encryption and debugging mode are only controlled through the `app.py` script. 

## A Note On Security

User information is currently stored in the `dependencies/userdata.db` file. Although the database itself is not currently encrypted, the information contained therein is secure. All passwords are salted and hashed using the `Argon2` process, winner of the 2015 Password Hashing competition. This package is implemented on the server side via the open-source `argon2-cffi` library, distributed under the `MIT License`.

`Argon2` takes several parameters, including salt length, hash length, time cost (how long it takes to run a single iteration), memory cost (how much memory is utilized to run a single iteration), and parallelism (how many threads can call `Argon2`). All of these are set within the `dependencies/userhandler.py` file, and can be adjusted depending on available hardware and security needs. The default version used is `Argon2id`, which protects against the two major attack vectors this algorithm has been subjected to thus far, and is considered the main version as a result. More information can be found at the `Argon2` project source: `argon2.online`

It should be noted that, in the case of SSL encryption, enabling an encrypted connection will result in most browsers warning the user of an insecure connection. This is due to self-signed security certificates, which are characteristic of a locally-hosted web application without access to the Internet and corresponding security authorities; however, SSL encryption will still be active as can be noted by the `https` label in the address bar, and the user can safely continue using the system.