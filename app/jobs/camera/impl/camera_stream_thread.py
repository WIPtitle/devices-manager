import os
import subprocess
import threading
import time

from app.models.camera import Camera
from app.models.recording import Recording


class CameraStreamThread(threading.Thread):
    def __init__(self, camera: Camera):
        super().__init__()
        self.camera = camera
        self.running = True


    def run(self):
        command = [
            'ffmpeg', '-fflags', 'nobuffer', '-loglevel', 'quiet', '-rtsp_transport', 'tcp',
            '-i', f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}", '-vsync',
            '0', '-copyts',
            '-vcodec', 'copy', '-movflags', 'frag_keyframe+empty_moov', '-an', '-r', '2', '-b:v', '500k',
            '-cpu-used', '4', '-threads', '4', '-crf', '60', '-hls_flags', 'delete_segments+append_list',
            '-f', 'hls', '-hls_time', '5', '-hls_list_size', '2', '-hls_segment_type', 'mpegts',
            '-hls_segment_filename', f"static/{self.camera.ip}_%d.ts", f"static/{self.camera.ip}.m3u8"
        ]

        proc = None
        is_unreachable = True

        while self.running:
            time.sleep(1) # check every second if process is still running

            try:
                if proc is None or is_unreachable or proc.poll() is not None:
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
                    is_unreachable = False
                else:
                    is_unreachable = True
            except Exception as e:
                is_unreachable = True
                print("Exception on recording thread:", e)

        if proc is not None:
            proc.terminate()


    def stop(self):
        self.running = False

