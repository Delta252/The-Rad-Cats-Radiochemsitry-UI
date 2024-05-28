# This file handles the two discrete camera feeds and provides the 
# individual frames to corresponding applications. 
# The functionality has been sepearated out due to multiple dependencies on the underlying functionality
# Live feed is for the webcam, while the spectrometer is the feed used for spectrum readings

import cv2, numpy

liveFeed = cv2.VideoCapture(0)
spectrometerFeed = cv2.VideoCapture(1)

def video_stream():
    while(True):
        ret, frame = liveFeed.read()
        if not ret:
            break
        else:
            ret, buffer = cv2.imencode('.jpeg',frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def spect_stream():
    while(True):
        ret, frame = spectrometerFeed.read()
        if not ret:
            break
        else:
            ret, buffer = cv2.imencode('.jpeg',frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def spect_frame():
    ret, frame = spectrometerFeed.read()
    if not ret:
        return None
    else:
        return frame

