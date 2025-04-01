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

    def process_image(self, image: "cv2.Mat") -> ("cv2.Mat", bool):
        """
        Processes an image with YOLO to detect persons.

        Args:
            image: The image to process.

        Returns:
            A tuple of the processed image and a boolean indicating if a person was found.
        """
        results = self.model(image)
        person_found = False
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 2
        color = (10, 100, 255)
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                if class_id == 0:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
                    label = f"Person: {confidence:.2f}"
                    cv2.putText(image, label, (x1, y1 - 10), font, font_scale, color, thickness)
                    person_found = True
                    logging.info("Person detected: bbox=(%d,%d,%d,%d), confidence=%.2f", x1, y1, x2, y2, confidence)
        return image, person_found

    def save_image(self, image: "cv2.Mat"):
        """
        Saves the original image to disk.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{IMAGE_SAVE_FOLDER}/{timestamp}.jpg"
        cv2.imwrite(filename, image)
        logging.info("Image saved: %s", filename)

    def send_discord_image(self, image: "cv2.Mat"):
        """
        Sends the processed image to Discord via webhook.
        """
        if not DISCORD_WEBHOOK_URL:
            logging.warning("Discord webhook URL not configured; skipping Discord send.")
            return
        success, buffer = cv2.imencode(".jpg", image)
        if not success:
            logging.error("Error encoding image for Discord.")
            return
        files = {"file": ("processed_image.jpg", buffer.tobytes(), "image/jpeg")}
        data = {"content": "Person detected!"}
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            logging.info("Image sent to Discord.")
        except Exception as e:
            logging.error("Error sending image to Discord: %s", e)

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

                processed_image, person_found = self.process_image(image)
                if person_found and (now - self.last_discord_send).total_seconds() >= DISCORD_INTERVAL_MINUTES * 60:
                    self.send_discord_image(processed_image)
                    self.last_discord_send = now

            self.push_kuma(status, msg)
            time.sleep(CAPTURE_INTERVAL_SECONDS)


if __name__ == "__main__":
    monitor = CameraMonitor()
    monitor.run()
