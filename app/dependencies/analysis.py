# Any data analysis and visualization functions
# This file handles the visualization of results gathered from the sensors
# and spectrometer for the user to view

import os, time, csv
import matplotlib.pyplot as plt
import numpy as np


class Analysis:
    def __init__(self):
        self.destinationFolder = os.path.abspath('app/data')
        self.status = 'offline' # Should be replaced with enums

    def exportToFile(self, data, filename):
        with open(f'{self.destinationFolder}/{filename}.csv',"w") as f:
            wr = csv.writer(f,delimiter="\n")
            wr.writerow(data)

    def generateTempGraph(self, data):
        plotDir = 'app/static/img'
        for fname in os.listdir(plotDir):
            if fname.startswith("tempGraph"):
                os.remove(os.path.join(plotDir, fname))
        plotData = data[-30:]
        plt.plot(plotData)
        filename = f'tempGraph_{round(time.time())}.png'
        plt.savefig(os.path.join(plotDir, filename), bbox_inches='tight')
        return filename

