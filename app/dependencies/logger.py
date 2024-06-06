# File for the creation of a log file
# Logs should contain typically not required diagnostic information about system performance
# NOT CURRENTLY IMPLEMENTED

import os, csv, datetime

def Log(command, file_name = "commands.csv"):
    nowTime = datetime.datetime.now()
    time = nowTime.strftime("%H:%M:%S")

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name), mode ="a", newline='') as csvfile:
        writer = csv.writer(csvfile) 
        writer.writerow([time, command])
