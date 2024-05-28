# Interactions with user database

import os, sys
import sqlite3
from argon2 import PasswordHasher

# Creates an object to handle user information
class UserHandler:

    def __init__(self):
        # Config user database handling
        databaseFilepath = 'userdata.db'
        if getattr(sys, 'frozen', False):
            applicationPath = os.path.dirname(sys.executable)
        elif __file__:
            applicationPath = os.path.dirname(__file__)
        userdataFilepath = os.path.join(applicationPath, databaseFilepath)
        self.connect = sqlite3.connect(userdataFilepath, check_same_thread=False)

        cursor= self.connect.cursor()

        # Create user database if one does not exist
        # Usernames and passwords cannot be repeated (UNIQUE qualifier)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS userdata (
                username VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                status VARCHAR(7) NOT NULL,
                theme VARCHAR(7) NOT NULL,
                admin BOOLEAN, 
                UNIQUE(username, password)
                )
            """)

        self.connect.commit()

        cursor.close()

        # Definition of password hasher parameters
        self.argon2Hasher = PasswordHasher(time_cost=16, memory_cost=2**15, parallelism=2, hash_len=32, salt_len=16)

    def attemptLogin(self, userCandidate, pswdCandidate):
        cursor = self.connect.cursor()

        # Find user and extract password
        cursor.execute(f"""
            SELECT password FROM userdata WHERE username='{userCandidate}'
            """)
        
        found = cursor.fetchone()

        if found:
            try:
                self.argon2Hasher.verify(found[0], pswdCandidate) # Verify entered password validity
            except:
                # Argon2ID verify method throws exception if password is not correct
                cursor.close()
                return False
            
            cursor.execute(f"""
            UPDATE userdata SET status='active' WHERE username='{userCandidate}'
            """)
            
            self.connect.commit()

            cursor.close()
            return True
        else:
            cursor.close()
            return False
        
    def logOff(self, user):
        cursor = self.connect.cursor()

        # Set user status accordingly (requires future updates)
        cursor.execute(f"""
            UPDATE userdata SET status='offline' WHERE username='{user}'
            """)
        
        self.connect.commit()

        cursor.close()

    def logOffAll(self):
        cursor = self.connect.cursor()

        # Set user status accordingly (requires future updates)
        cursor.execute(f"""
            UPDATE userdata SET status='offline'
            """)
         
        self.connect.commit()

        cursor.close() 
        
    def attemptRegister(self, userCandidate, pswdCandidate):
        cursor = self.connect.cursor()

        pswdHash = self.argon2Hasher.hash(pswdCandidate)

        # User/password combination only inserted if both are unique to the existing table
        cursor.execute("""
            INSERT OR IGNORE INTO userdata(username, password, status, theme, admin) VALUES(?, ?, ?, ?, ?)
            """, (userCandidate, pswdHash, 'offline', 'theme1', 'False'))
        
        self.connect.commit()

        cursor.close()

    def getUsername(self):
        cursor = self.connect.cursor()

        # Return single active user (requires rework for multiple users)
        cursor.execute(f"""
            SELECT username FROM userdata WHERE status='active'
            """)
        
        found = cursor.fetchone()

        cursor.close()

        return found
    
    def getAllUsers(self):
        cursor = self.connect.cursor()
        allUsers = []

        cursor.execute(f"""
            SELECT * FROM userdata
        """)

        found = cursor.fetchall()
        for row in found:
            allUsers.append([row[0], row[4]])

        cursor.close()

        return allUsers

    def updateUsername(self, oldUsername, newUsername):
        cursor = self.connect.cursor()

        # Update username to new value
        cursor.execute(f"""
            UPDATE userdata SET username='{newUsername}' WHERE username='{oldUsername}'
            """)
        
        self.connect.commit()

        cursor.close()

    def updateAdmin(self, username, adminStatus):
        cursor = self.connect.cursor()

        # Update username to new value
        cursor.execute(f"""
            UPDATE userdata SET admin='{adminStatus}' WHERE username='{username}'
            """)

        self.connect.commit()

        cursor.close()

    def verifyUser(self, username, pswd):
        cursor = self.connect.cursor()

        cursor.execute(f"""
                SELECT password FROM userdata WHERE username='{username}'
                """)
            
        found = cursor.fetchone()

        if found:
            try:
                self.argon2Hasher.verify(found[0], pswd) # Verify entered password validity
            except:
                # Argon2ID verify method throws exception if password is not correct
                cursor.close()
                return False
            
            cursor.close()
            return True
        else:
            cursor.close()
            return False
        
    def updatePassword(self, username, pswd):
        cursor = self.connect.cursor()

        pswdHash = self.argon2Hasher.hash(pswd)
 
        # Update username to new value
        cursor.execute(f"""
            UPDATE userdata SET password='{pswdHash}' WHERE username='{username}'
            """)
        
        self.connect.commit()

        cursor.close()

    def getUserTheme(self, username):
        cursor = self.connect.cursor()

        # User/password combination only inserted if both are unique to the existing table
        cursor.execute(f"""
            SELECT theme FROM userdata WHERE username='{username}'
            """)
        
        found = cursor.fetchone()

        cursor.close()

        return found
    
    def updateUserTheme(self, newTheme, username):
        cursor = self.connect.cursor()

        # User/password combination only inserted if both are unique to the existing table
        cursor.execute(f"""
            UPDATE userdata SET theme='{newTheme}' WHERE username='{username}'
            """)
        
        self.connect.commit()

        cursor.close()

    def getStatus(self, username):
        cursor = self.connect.cursor()

        # User/password combination only inserted if both are unique to the existing table
        cursor.execute(f"""
            SELECT status FROM userdata WHERE username='{username}'
            """)
        
        found = cursor.fetchone()

        cursor.close()

        return found