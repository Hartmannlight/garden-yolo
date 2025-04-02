import time
import datetime
import logging
import requests
import cv2
import numpy as np
from config import (
    KUMA_URL,
    DISCORD_WEBHOOK_URL,
    CAMERA_CAPTURE_URL,
    CAMERA_ROTATION,
    IMAGE_SAVE_FOLDER,
    YOLO_MODEL_PATH,
    CAPTURE_INTERVAL_SECONDS,
    SAVE_INTERVAL_MINUTES,
    DISCORD_INTERVAL_MINUTES,
    REQUEST_TIMEOUT,
    LOG_FILE,
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class CameraMonitor:
    """
    Monitors an ESP32-CAM, processes images with YOLO, pings Kuma and sends Discord notifications.

    Attributes:
        model (YOLO): The YOLO model for object detection.
        last_save_minute (int): The minute value when the last image was saved.
        last_discord_send (datetime): Timestamp of the last Discord notification.
    """

    def __init__(self):
        self.model = YOLO(YOLO_MODEL_PATH)
        self.last_discord_send = datetime.datetime.min

    def capture_image(self) -> "cv2.Mat or None":
        """
        Retrieves an image from the camera and optionally rotates it.

        Returns:
            OpenCV image matrix if successful, else None.
        """
        try:
            response = requests.get(CAMERA_CAPTURE_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if CAMERA_ROTATION == 90:
                image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            elif CAMERA_ROTATION == 180:
                image = cv2.rotate(image, cv2.ROTATE_180)
            elif CAMERA_ROTATION == 270:
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

            return image
        except Exception as e:
            logging.error("Error capturing image: %s", e)
            return None

    def push_kuma(self, status: str, msg: str):
        """
        Pings the Kuma service. Skips if KUMA_URL is not configured.

        Args:
            status (str): "up" or "down".
            msg (str): Status message.
        """
        if not KUMA_URL:
            return
        try:
            url = f"{KUMA_URL.split('?')[0]}?status={status}&msg={msg}"
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except Exception as e:
            logging.error("Error sending Kuma ping: %s", e)

    def save_image(self, image: "cv2.Mat"):
        """
        Saves the original image to disk.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{IMAGE_SAVE_FOLDER}/{timestamp}.jpg"
        cv2.imwrite(filename, image)
        logging.info("Image saved: %s", filename)

    def run(self):
        """
        Main loop of the monitor.
        """
        while True:
            now = datetime.datetime.now()
            image = self.capture_image()
            if image is None:
                status = "down"
                msg = "Image capture failed"
            else:
                status = "up"
                msg = "OK"

                self.save_image(image)

            self.push_kuma(status, msg)
            time.sleep(CAPTURE_INTERVAL_SECONDS)


if __name__ == "__main__":
    monitor = CameraMonitor()
    monitor.run()
