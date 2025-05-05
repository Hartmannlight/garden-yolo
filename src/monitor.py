import os
import time
import datetime
import logging
import requests
import cv2
import numpy as np
from ultralytics import YOLO

from config import (
    KUMA_URL,
    DISCORD_WEBHOOK_URL,
    CAMERA_CAPTURE_URL,
    CAMERA_ROTATION,
    IMAGE_SAVE_FOLDER,
    YOLO_MODEL_PATH,
    CAPTURE_INTERVAL_SECONDS,
    YOLO_PROCESS_EVERY_N,
    FAILURE_THRESHOLD,
    REQUEST_TIMEOUT,
    LOG_FILE,
)

# Ensure LOG_FILE is a file path, not a directory
if os.path.isdir(LOG_FILE):
    # create the directory if it doesn't exist, then point to monitor.log inside it
    os.makedirs(LOG_FILE, exist_ok=True)
    log_path = os.path.join(LOG_FILE, "monitor.log")
else:
    # ensure parent directory exists
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    log_path = LOG_FILE

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class CameraMonitor:
    """
    Monitors an ESP32-CAM, saves each capture in daily folders,
    processes every N-th frame with YOLO, and pings Kuma after failures.
    """

    def __init__(self):
        self.image_counter = 0
        self.consecutive_failures = 0
        self.model = YOLO(YOLO_MODEL_PATH)

    def capture_image(self):
        """
        Fetches an image from the camera and applies rotation if configured.
        Returns the OpenCV image matrix, or None on error.
        """
        try:
            response = requests.get(CAMERA_CAPTURE_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            img_array = np.frombuffer(response.content, dtype=np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if CAMERA_ROTATION == 90:
                image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            elif CAMERA_ROTATION == 180:
                image = cv2.rotate(image, cv2.ROTATE_180)
            elif CAMERA_ROTATION == 270:
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

            return image
        except Exception as e:
            logging.error("Capture error: %s", e)
            return None

    def save_image(self, image):
        """
        Saves the image in a folder named YYYY-MM-DD under IMAGE_SAVE_FOLDER.
        """
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        folder = os.path.join(IMAGE_SAVE_FOLDER, date_str)
        os.makedirs(folder, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(folder, f"{timestamp}.jpg")
        cv2.imwrite(filename, image)
        logging.info("Saved image: %s", filename)

    def process_yolo(self, image):
        """
        Runs the YOLO model on the image.
        """
        _ = self.model(image)
        logging.info("YOLO processed image #%d", self.image_counter)

    def push_kuma(self, status, msg):
        """
        Sends a status ping to Kuma if KUMA_URL is set.
        """
        if not KUMA_URL:
            return
        try:
            base_url = KUMA_URL.split("?", 1)[0]
            url = f"{base_url}?status={status}&msg={msg}"
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except Exception as e:
            logging.error("Kuma ping error: %s", e)

    def _handle_failure(self):
        """
        Increments failure counter and pushes 'down' if threshold reached.
        """
        self.consecutive_failures += 1
        if self.consecutive_failures >= FAILURE_THRESHOLD:
            self.push_kuma("down", f"Failed {self.consecutive_failures} captures")
            self.consecutive_failures = 0

    def _handle_success(self, image):
        """
        Resets failure counter, pushes 'up', saves image, and processes YOLO as configured.
        """
        self.consecutive_failures = 0
        self.push_kuma("up", "OK")

        # Always save each captured image
        self.save_image(image)

        # Process YOLO every N-th image
        self.image_counter += 1
        if self.image_counter % YOLO_PROCESS_EVERY_N == 0:
            self.process_yolo(image)

    def run(self):
        """
        Main loop: capture → success/failure handling → sleep.
        """
        while True:
            image = self.capture_image()

            if image is None:
                self._handle_failure()
            else:
                self._handle_success(image)

            time.sleep(CAPTURE_INTERVAL_SECONDS)


if __name__ == "__main__":
    CameraMonitor().run()
