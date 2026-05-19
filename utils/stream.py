import cv2
import threading
import time


class StreamReader:
    """
    Lag-free RTSP/video stream reader.

    Problem with naive cv2.VideoCapture in a loop:
        Camera sends 25 FPS. YOLO processes at 7-10 FPS on CPU.
        OpenCV buffers unread frames internally. After 10 seconds,
        the buffer holds ~150 stale frames. Every frame you read
        is several seconds behind reality — visible as severe lag.

    Fix — threaded frame grabber:
        A background thread runs as fast as possible, continuously
        calling cap.read() and discarding every frame except the
        latest one. The processing loop always gets the MOST RECENT
        frame, no matter how slow inference is. Lag is eliminated.
    """

    def __init__(self, source):
        self.source = source
        self.cap    = None

        self._latest_frame = None
        self._lock         = threading.Lock()
        self._running      = False
        self._thread       = None

    def start(self):
        self.cap = cv2.VideoCapture(self.source)

        # Tell OpenCV to keep only 1 frame in its internal buffer.
        # This alone helps but isn't enough without the thread.
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            raise ValueError(f"[Stream] Cannot open source: {self.source}")

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        w   = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h   = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"[Stream] Opened: {self.source}")
        print(f"[Stream] FPS: {fps}")
        print(f"[Stream] Resolution: {w}x{h}")

        self._running = True
        self._thread  = threading.Thread(target=self._grab_loop, daemon=True)
        self._thread.start()

        # Wait until the first frame arrives before returning
        timeout = 5.0
        start   = time.time()
        while self._latest_frame is None:
            if time.time() - start > timeout:
                raise RuntimeError("[Stream] Timed out waiting for first frame.")
            time.sleep(0.05)

    def _grab_loop(self):
        """
        Background thread — runs as fast as possible.
        Reads every frame from the camera and keeps only the latest.
        Old frames are silently discarded, preventing buffer buildup.
        """
        while self._running:
            success, frame = self.cap.read()

            if success:
                with self._lock:
                    self._latest_frame = frame
            else:
                # For MP4 files: loop back to start
                # For RTSP: brief pause then retry
                is_rtsp = str(self.source).startswith("rtsp")
                if not is_rtsp:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                time.sleep(0.01)

    def read(self):
        """Returns (True, latest_frame) or (False, None) if no frame yet."""
        with self._lock:
            frame = self._latest_frame
        if frame is None:
            return False, None
        return True, frame.copy()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self.cap is not None:
            self.cap.release()
            print("[Stream] Released.")

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def __iter__(self):
        """
        Yields the latest available frame on each iteration.
        Naturally throttled by YOLO inference speed — no sleep needed.
        Always returns current frame, never a stale buffered one.
        """
        while self._running:
            success, frame = self.read()
            if not success:
                time.sleep(0.01)
                continue
            yield frame