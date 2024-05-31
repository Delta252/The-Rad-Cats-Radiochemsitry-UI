# Any data analysis and visualization functions
# This file handles the visualization of results gathered from the sensors
# and spectrometer for the user to view

import os, time, csv
import matplotlib.pyplot as plt
import numpy, peakutils, pandas, cv2
from scipy.signal import savgol_filter

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
    
    # The following is modified from the pocket spectroscope project
    # The original code can be found here:
    def generateSpectGraph(self, frame):
        print("Generating Spectrogram")
        # Constants for further operation
        fileName = f'spectMeas_{round(time.time())}.csv'
        spectCal = ((355, 532), (577, 650))
        mindist = 50
        thresh = 20
        savpoly = 7
        intensity = [0] * 636
        holdPeaks = False
        wavelengthdata = []
        
        # Core processing
        bwimage = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rows, cols = bwimage.shape
        graph = np.zeros([255, 636, 3], dtype=np.uint8)
        graph.fill(255)

        pxrange = abs(spectCal[0][0] - spectCal[1][0])
        nmrange = abs(spectCal[0][1] - spectCal[1][1])        
        pxpernm = pxrange / nmrange
        nmperpx = nmrange / pxrange
        zero = spectCal[0][1] - (spectCal[0][0] / pxpernm)
        scalezero = zero
        prevposition = 0
        textoffset = 12
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(636):
            position = round(zero)
            if position != prevposition:
                if position % 10 == 0:
                    cv2.line(graph, (i, 15), (i, 255), (200, 200, 200), 1)
                if position % 50 == 0:
                    cv2.line(graph, (i, 15), (i, 255), (0, 0, 0), 1)
                    cv2.putText(graph, str(position) + 'nm', (i - textoffset, 12), font, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            zero += nmperpx
            prevposition = position

        for i in range(255):
            if i != 0 and i % 51 == 0:
                cv2.line(graph, (0, i), (636, i), (100, 100, 100), 1)

        halfway = int(rows / 2)
        for i in range(cols - 4):
            data = bwimage[halfway, i]
            if holdPeaks:
                if data > intensity[i]:
                    intensity[i] = data
            else:
                intensity[i] = data

        if not holdPeaks:
            window_length = min(17, len(intensity) // 2 * 2 + 1)  # Ensure window_length is an odd number
            intensity = savgol_filter(intensity, window_length, int(savpoly))
        intensity = intensity.astype(int)

        index = 0
        for i in intensity:
            wavelength = (scalezero + (index / pxpernm))
            wavelengthdata.append(round(wavelength, 1))
            wavelength = round(wavelength)
            cv2.line(graph, (index, 255), (index, 255 - i), 1, 1)
            cv2.line(graph, (index, 254 - i), (index, 255 - i), (0, 0, 0), 1, cv2.LINE_AA)
            index += 1

        indexes = peakutils.indexes(intensity, thres=thresh / max(intensity), min_dist=mindist)
        for i in indexes:
            height = intensity[i]
            height = 245 - height
            wavelength = int(scalezero + (i / pxpernm))
            cv2.rectangle(graph, ((i - textoffset) - 2, height + 3), ((i - textoffset) + 45, height - 11), (255, 255, 0), -1)
            cv2.rectangle(graph, ((i - textoffset) - 2, height + 3), ((i - textoffset) + 45, height - 11), (0, 0, 0), 1)
            cv2.putText(graph, str(wavelength) + 'nm', (i - textoffset, height), font, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

        axisWavelengths = wavelengthdata
        intensityData = intensity
        pd.DataFrame({'Wavelength': axisWavelengths, 'Intensity': intensityData}).to_csv('graphdata.csv', index=False)
        return intensityData
            
    def findmean(self, frames):
        referenceIntensity = pd.read_csv('ReferenceIntensity.csv')['Intensity'].values
        wavelengtharray = pd.read_csv('ReferenceIntensity.csv')['Wavelength'].values
        intensities = np.zeros((100, 636))
        print("Processing frames")
        for i in range(100):
            intensities[i] = self.generateSpectGraph(frames[i])

        means = np.mean(intensities, axis=0)
        ratioValues = np.divide(means, referenceIntensity)
        ratioValues = np.maximum(ratioValues, np.finfo(float).eps)
        logRatioValues = -np.log10(ratioValues)
    
        csv_filename = f"log10_ratio_{round(time.time())}.csv"
        with open(csv_filename, 'w') as f:
            f.write('Wavelength,Log10MeanIntensityRatio\r\n')
            for wavelength, logRatioValue in zip(wavelengtharray, logRatioValues):
                f.write(f"{wavelength},{logRatioValue}\r\n")
        print("Log10 of mean intensity ratio data saved to:", csv_filename)
    
        plt.figure(figsize=(10, 6))
        plt.plot(wavelengtharray, logRatioValues, marker='*', linestyle='-', color='blue')
        plt.title('Log10 of Mean Intensity Ratio vs. Wavelength')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('-Log10(Mean Intensity Ratio)')
        plt.grid(True)
        plotDir = 'app/static/img'
        for fname in os.listdir(plotDir):
            if fname.startswith("spectGraph"):
                os.remove(os.path.join(plotDir, fname))
        plotData = data[-30:]
        plt.plot(plotData)
        filename = f'spectGraph_{round(time.time())}.png'
        plt.savefig(os.path.join(plotDir, filename), bbox_inches='tight')
        return filename

