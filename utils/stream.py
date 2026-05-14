import cv2

class StreamReader:
    def __init__(self, source):
        self.source = source
        self.cap = None

    def start(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open source: {self.source}")
        print(f"[Stream] Opened: {self.source}")
        print(f"[Stream] FPS: {self.cap.get(cv2.CAP_PROP_FPS)}")
        print(f"[Stream] Resolution: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    def read(self):
        """Read one frame. Returns (success, frame)."""
        if self.cap is None:
            raise RuntimeError("Stream not started. Call start() first.")
        return self.cap.read()

    def stop(self):
        if self.cap is not None:
            self.cap.release()
            print("[Stream] Released.")

    def __iter__(self):
        """Allow using stream in a for loop."""
        while True:
            success, frame = self.read()
            if not success:
                break
            yield frame

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()