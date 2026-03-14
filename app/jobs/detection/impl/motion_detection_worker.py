import json
import threading
import time
from datetime import datetime, timedelta

import cv2
import numpy as np

from app.clients.alarm_events_client import AlarmEventsClient
from app.jobs.detection.impl.detection_model_provider import DetectionModelProvider
from app.jobs.detection.impl.notification_scheduler import NotificationScheduler
from app.models.camera import Camera

DIFF_BLUR_KERNEL = 21
DIFF_BINARY_THRESHOLD = 25


class MotionDetectionWorker:
    DETECTION_WIDTH = 640
    DETECTION_HEIGHT = 360

    @staticmethod
    def _sensitivity_to_threshold(sensitivity: int) -> float:
        """Convert 1-100 sensitivity to motion threshold. Higher sensitivity = lower threshold."""
        # 1% -> 0.05 (very insensitive), 50% -> 0.015 (medium), 100% -> 0.001 (very sensitive)
        return 0.05 * (0.02 ** (sensitivity / 100.0))

    # Global cooldown shared across all workers
    _global_last_warning: datetime | None = None
    _global_lock = threading.Lock()

    def __init__(self, camera: Camera, frame_buffer, alarm_events_client: AlarmEventsClient,
                 detection_manager=None,
                 group_id: int = 0,
                 notification_scheduler: NotificationScheduler = None,
                 detection_confidence: int = 50, motion_sensitivity: int = 50,
                 warning_cooldown_seconds: int = 60):
        self.camera = camera
        self.frame_buffer = frame_buffer
        self.alarm_events_client = alarm_events_client
        self.detection_manager = detection_manager
        self.group_id = group_id
        self.notification_scheduler = notification_scheduler
        self.running = False
        self._thread = None

        # Motion detection (frame-to-frame diff)
        self.roi_mask = self._build_roi_mask(camera.detection_roi, self.DETECTION_WIDTH, self.DETECTION_HEIGHT)
        self.threshold = self._sensitivity_to_threshold(motion_sensitivity)
        self.prev_gray = None

        # Person detection (YOLO, only if motion+person)
        self.use_person = camera.detection_mode == "motion+person"
        self.confidence = detection_confidence / 100.0
        self.model = DetectionModelProvider.get_model() if self.use_person else None

        self.cooldown = timedelta(seconds=warning_cooldown_seconds)

    @staticmethod
    def _build_roi_mask(roi_json: str | None, w: int, h: int) -> np.ndarray | None:
        if not roi_json:
            return None
        try:
            polygons = json.loads(roi_json)
            if not polygons or not isinstance(polygons, list):
                return None

            # Format: array of polygons [[[x,y],[x,y],...], ...]
            all_pixel_polys = []
            for polygon in polygons:
                if not polygon or len(polygon) < 3:
                    continue
                pixel_points = np.array(
                    [[int(p[0] * w), int(p[1] * h)] for p in polygon],
                    dtype=np.int32,
                )
                all_pixel_polys.append(pixel_points)

            if not all_pixel_polys:
                return None

            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, all_pixel_polys, 255)
            return mask
        except Exception as e:
            print(f"Error building ROI mask: {e}")
            return None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[Detection] Started for camera {self.camera.ip} (mode={self.camera.detection_mode}, "
              f"sensitivity={self.threshold:.6f}, confidence={self.confidence:.2f}, cooldown={self.cooldown.total_seconds()}s)")

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        print(f"[Detection] Stopped for camera {self.camera.ip}")

    def _box_in_roi(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if any part of bounding box overlaps with ROI mask."""
        if self.roi_mask is None:
            return True
        # Check corners and center — if any point is inside ROI, the person overlaps
        points = [
            (x1, y1), (x2, y1), (x1, y2), (x2, y2),
            ((x1 + x2) // 2, (y1 + y2) // 2),
        ]
        for px, py in points:
            px = max(0, min(px, self.DETECTION_WIDTH - 1))
            py = max(0, min(py, self.DETECTION_HEIGHT - 1))
            if self.roi_mask[py, px] > 0:
                return True
        return False

    def _run(self):
        frame_count = 0
        last_seq = -1
        while self.running:
            frame = self.frame_buffer.get_latest()
            if frame is None:
                time.sleep(1)
                continue

            current_seq = self.frame_buffer.seq
            if current_seq == last_seq:
                time.sleep(1)
                continue
            last_seq = current_seq
            frame_count += 1

            if frame_count == 1:
                roi_coverage = f"{np.count_nonzero(self.roi_mask)}/{self.roi_mask.size} px" if self.roi_mask is not None else "full frame"
                print(f"[Detection] {self.camera.ip}: first frame received, shape={frame.shape}, roi={roi_coverage}")

            # Apply ROI mask
            if self.roi_mask is not None:
                if self.roi_mask.shape[:2] != frame.shape[:2]:
                    print(f"[Detection] {self.camera.ip}: ROI mask shape {self.roi_mask.shape} != frame shape {frame.shape[:2]}, skipping mask")
                    masked = frame
                else:
                    masked = cv2.bitwise_and(frame, frame, mask=self.roi_mask)
            else:
                masked = frame

            # Convert to grayscale and blur for noise reduction
            gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (DIFF_BLUR_KERNEL, DIFF_BLUR_KERNEL), 0)

            # First frame: store and wait for next
            if self.prev_gray is None:
                self.prev_gray = gray
                print(f"[Detection] {self.camera.ip}: baseline frame stored, waiting for next")
                time.sleep(1)
                continue

            # Frame-to-frame diff (previous frame = background)
            diff = cv2.absdiff(self.prev_gray, gray)
            _, diff_thresh = cv2.threshold(diff, DIFF_BINARY_THRESHOLD, 255, cv2.THRESH_BINARY)
            self.prev_gray = gray

            # Count motion pixels
            motion_pixels = np.count_nonzero(diff_thresh)
            if self.roi_mask is not None:
                total_pixels = np.count_nonzero(self.roi_mask)
            else:
                total_pixels = frame.shape[0] * frame.shape[1]

            if total_pixels == 0:
                time.sleep(1)
                continue

            motion_ratio = motion_pixels / total_pixels

            if frame_count % 30 == 0:
                print(f"[Detection] {self.camera.ip}: alive, frame #{frame_count}, motion_ratio={motion_ratio:.6f}, threshold={self.threshold:.6f}")

            if motion_ratio <= self.threshold:
                time.sleep(1)
                continue

            print(f"[Detection] {self.camera.ip}: motion detected (ratio={motion_ratio:.4f}, threshold={self.threshold:.6f})")

            # Person detection (only if configured)
            detection_boxes = None
            if self.use_person:
                results = self.model(frame, classes=[0], conf=self.confidence, verbose=False)
                all_boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                # Filter boxes: only keep persons whose center is inside ROI
                filtered = [box for box in all_boxes if self._box_in_roi(box[0], box[1], box[2], box[3])]
                if len(filtered) == 0:
                    print(f"[Detection] {self.camera.ip}: YOLO found {len(all_boxes)} person(s) but none in ROI, skipping")
                    time.sleep(1)
                    continue
                print(f"[Detection] {self.camera.ip}: YOLO found {len(filtered)} person(s) in ROI")
                detection_boxes = np.array(filtered)

            # Check if warnings are still enabled (only in LISTENING state)
            if self.detection_manager and not self.detection_manager.is_warning_enabled():
                time.sleep(1)
                continue

            # Global cooldown check
            now = datetime.now()
            with MotionDetectionWorker._global_lock:
                if (MotionDetectionWorker._global_last_warning
                        and (now - MotionDetectionWorker._global_last_warning) < self.cooldown):
                    print(f"[Detection] {self.camera.ip}: in global cooldown, skipping")
                    time.sleep(1)
                    continue
                MotionDetectionWorker._global_last_warning = now

            # Draw detection rectangles on snapshot
            snapshot_frame = frame.copy()
            try:
                if detection_boxes is not None:
                    # YOLO person boxes
                    for box in detection_boxes:
                        cv2.rectangle(snapshot_frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                else:
                    # Motion-only: bounding rect around motion contours
                    contours, _ = cv2.findContours(diff_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        for cnt in contours:
                            if cv2.contourArea(cnt) < 100:
                                continue
                            x, y, w, h = cv2.boundingRect(cnt)
                            cv2.rectangle(snapshot_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            except Exception as e:
                print(f"[Detection] {self.camera.ip}: error drawing detection rects: {e}")

            # Encode snapshot as JPEG
            snapshot_jpeg = None
            try:
                _, buf = cv2.imencode('.jpg', snapshot_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                snapshot_jpeg = buf.tobytes()
            except Exception as e:
                print(f"[Detection] {self.camera.ip}: error encoding snapshot: {e}")

            # Trigger WARNING: audio immediately, notification via scheduler (with delay)
            try:
                self.alarm_events_client.notify_motion_warning_audio(self.camera.name)
            except Exception as e:
                print(f"[Detection] {self.camera.ip}: error sending audio warning: {e}")

            try:
                self.notification_scheduler.schedule(self.group_id, self.camera.name, snapshot_jpeg)
                print(f"[Detection] {self.camera.ip}: WARNING triggered")
            except Exception as e:
                print(f"[Detection] {self.camera.ip}: error scheduling notification: {e}")

            time.sleep(1)
