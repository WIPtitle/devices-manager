import threading

from app.models.camera import Camera


class RecordingThread(threading.Thread):
    def __init__(self, camera: Camera):
        super().__init__()
        self.camera = camera
        self.running = True


    def run(self):
        print("running")


    def stop(self):
        self.running = False
