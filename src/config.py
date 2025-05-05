import os

KUMA_URL = os.getenv("KUMA_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CAMERA_CAPTURE_URL = os.getenv(
    "CAMERA_CAPTURE_URL",
    "https://images.bergfex.at/webcams/?id=17250&format=4"
)
CAMERA_ROTATION = int(os.getenv("CAMERA_ROTATION", "0"))

IMAGE_SAVE_FOLDER = os.getenv("IMAGE_SAVE_FOLDER", "/opt/webcam/images")
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolo11x.pt")
LOG_FILE = os.getenv("LOG_FILE", "/opt/webcam/monitor.log")

# seconds between capture AND save
CAPTURE_INTERVAL_SECONDS = int(os.getenv("CAPTURE_INTERVAL_SECONDS", "30"))
# process every Nth image through YOLO
YOLO_PROCESS_EVERY_N = int(os.getenv("YOLO_PROCESS_EVERY_N", "1"))
# consecutive failures before pushing 'down'
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", "3"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "5"))
DISCORD_INTERVAL_MINUTES = int(os.getenv("DISCORD_INTERVAL_MINUTES", "20"))
