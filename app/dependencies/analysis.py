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
    def generateSpectGraph(frames):
        # Constants for further operation
        fileName = f'spectMeas_{round(time.time())}.csv'
        spectCal = ((355,532),(577,650))
        mindist = 50
        thresh = 20
        savpoly = 7
        intensity = [0]*636
        holdPeaks = False
        intensityData = []
        samplewavelengths = []
        wavelengthdata = [[]]
        referenceIntensity = pandas.read_csv('app/dependencies/ReferenceIntensity.csv')['Intensity'].values
        # Core processing loop
        for frame in frames:
            rows, cols = frame.shape
            graph = numpy.zeros([255, 636, 3], dtype=numpy.uint8)
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
                data = frame[halfway, i]
                if holdPeaks:
                    if data > intensity[i]:
                        intensity[i] = data
                else:
                    intensity[i] = data

            if not holdPeaks:
                intensity = savgol_filter(intensity, 17, int(savpoly))
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

            #wavelengthdata.append(samplewavelengths)
            #intensityData.append(intensity)
        means = numpy.mean(intensityData, axis=0)
        ratioValues = numpy.divide(means, referenceIntensity)
        ratioValues = numpy.maximum(ratioValues, numpy.finfo(float).eps)
        logRatioValues = -numpy.log10(ratioValues)

        print(f'size of wavelengths: {len(axisWavelengths)}')
        print(f'size of logratiovalues: {len(logRatioValues)}')

        with open(fileName, 'w') as f:
            f.write('Wavelengths,LogMeanIntensityRatio\r\n')
            for index in range(636):
                f.write(f'{axisWavelengths[index+1]},{logRatioValues[index]}\r\n')
        
        data = pandas.read_csv(fileName)

        meanIntensities = data['LogMeanIntensityRatio']
        refWavelengths = data['Wavelengths']

        plt.figure(figsize=(10, 6))
        plt.plot(refWavelengths, meanIntensities, marker='*', linestyle='-', color='blue')
        plt.title('Log10 of Mean Intensity Ratio vs. Wavelength')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Log10(Mean Intensity Ratio)')
        plt.grid(True)
        plotDir = 'app/static/img'
        plt.savefig(os.path.join(plotDir, 'testSpectPlot.png'), bbox_inches='tight')
        return

