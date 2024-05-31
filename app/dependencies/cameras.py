# This file handles the two discrete camera feeds and provides the 
# individual frames to corresponding applications. 
# The functionality has been sepearated out due to multiple dependencies on the underlying functionality
# Live feed is for the webcam, while the spectrometer is the feed used for spectrum readings

import cv2

defaultCalibration = ((355,532),(577,650))

class LiveVideo:
    def __init__(self):
        self.liveFeed = cv2.VideoCapture(0)

    def videoStream(self):
        while True:
            ret, frame = self.liveFeed.read()
            if not ret:
                break
            else:
                ret, buffer = cv2.imencode('.jpeg',frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n' b'Content-type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

# The following is modified from the spectrometer project by 
# The original code can be found here: 
class SpectrometerVideo:
    def __init__(self):
        self.spectrometerFeed = cv2.VideoCapture(1)

        # Spectrometer-specific video feed setup.
        self.spectrometerFeed.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.spectrometerFeed.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.spectrometerFeed.set(cv2.CAP_PROP_FPS, 25)
        if not self.spectrometerFeed.isOpened():
            raise ValueError("Unable to open video source", self.spectrometerFeed)

        self.width = self.spectrometerFeed.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.spectrometerFeed.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def spectFrameBW(self):
        ret, frame = self.spectrometerFeed.read()
        if not ret:
            return (ret, None)
        else:
            print("SAMPLE TAKEN")
            return (ret, frame)

    def getSampleSet(self):
        frames = []
        for i in range(50):
            ret, frame = self.spectFrameBW()
            if ret:
                frames.append(frame)
        return frames

