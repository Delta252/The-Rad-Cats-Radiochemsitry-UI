### Interactions with user database

import os
import sqlite3
from argon2 import PasswordHasher

class UserHandler:

    def __init__(self):
        # Config user database handling
        userdataFilepath = os.path.abspath('userdata.db')
        self.connect = sqlite3.connect(userdataFilepath, check_same_thread=False)

        cursor= self.connect.cursor()

        # Create user database if one does not exist
        # Usernames and passwords cannot be repeated (UNIQUE qualifier)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS userdata (
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL, 
            UNIQUE(username, password)
            )
        """)

        self.connect.commit()

        cursor.close()

        # Definition of password hasher parameters
        self.argon2Hasher = PasswordHasher(time_cost=16, memory_cost=2**15, parallelism=2, hash_len=32, salt_len=16)

    def attemptLogin(self, userCandidate, pswdCandidate):
        cursor = self.connect.cursor()

        # Hash password using Argon2ID
        pswdHash = self.argon2Hasher.hash(pswdCandidate)

        # Find user and extract password
        cursor.execute(f"SELECT password FROM userdata WHERE username='{userCandidate}'")
        
        found = cursor.fetchone()

        if found:
            try:
                self.argon2Hasher.verify(found[0], pswdCandidate) # Verify entered password validity
            except:
                # Argon2ID verify method throws exception if password is not correct
                return False
            cursor.close()
            return True
        else:
            cursor.close()
            return False
        
    def attemptRegister(self, userCandidate, pswdCandidate):
        cursor = self.connect.cursor()

        pswdHash = self.argon2Hasher.hash(pswdCandidate)

        # User/password combination only inserted if both are unique to the existing table
        cursor.execute("""
                       INSERT OR IGNORE INTO userdata(username, password) VALUES(?, ?)
                       """, (userCandidate, pswdHash))
        
        self.connect.commit()

        cursor.close()