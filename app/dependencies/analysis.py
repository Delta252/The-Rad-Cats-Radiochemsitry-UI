# Any data analysis and visualization functions
# This file handles the visualization of results gathered from the sensors
# and spectrometer for the user to view

import os, time, csv

class Analysis:
    def __init__(self):
        self.destinationFolder = os.path.abspath('app/data/')
        self.status = 'offline' # Should be replaced with enums
        self.lastTempReading = time.time()
        self.tempCommand = '[sID1000 rID1005 PK1 R]' # Should be migrated to a sensor module

    def exportToFile(self, data, filename):
        with open(f'app/data/{filename}.csv',"w") as f:
            wr = csv.writer(f,delimiter="\n")
            wr.writerow(data)

