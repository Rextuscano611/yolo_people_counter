"""
utils/line_selector.py

Interactive tripwire line placement.

Usage:
    - A window opens showing the first camera frame
    - Click anywhere on the frame to place the tripwire line at that Y position
    - The line previews live as you move the mouse
    - Press ENTER or SPACE to confirm
    - Press ESC to cancel and fall back to default LINE_Y

Returns the selected LINE_Y integer, or None on cancel.
"""

import cv2


# Text drawn on the selector window
_INSTRUCTIONS = [
    "Click to place tripwire line",
    "ENTER / SPACE  confirm",
    "ESC            cancel (use default)",
]


def _draw_overlay(frame, line_y, confirmed=False):
    """Draw the preview line and instructions onto a copy of the frame."""
    overlay = frame.copy()
    h, w    = overlay.shape[:2]

    line_color = (0, 255, 0) if confirmed else (0, 200, 255)

    # Tripwire line
    cv2.line(overlay, (0, line_y), (w, line_y), line_color, 2)

    # Label next to the line
    label = f"LINE_Y = {line_y}"
    cv2.putText(overlay, label, (10, max(line_y - 8, 18)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, line_color, 1, cv2.LINE_AA)

    # Instruction box (top-right corner)
    for i, text in enumerate(_INSTRUCTIONS):
        y_pos = 22 + i * 22
        cv2.putText(overlay, text, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1, cv2.LINE_AA)

    return overlay


def select_line_y(first_frame, default_line_y=240, window_name="Set Tripwire Line"):
    """
    Show an interactive window for the user to click and set LINE_Y.

    Args:
        first_frame    : First captured frame (numpy array, BGR).
        default_line_y : Fallback value if user presses ESC or closes window.
        window_name    : cv2 window title.

    Returns:
        int  : Selected LINE_Y value.
    """
    h, w  = first_frame.shape[:2]
    state = {
        "line_y":    default_line_y,   # current candidate Y
        "confirmed": False,            # True once user clicks
        "done":      False,            # True when ENTER/ESC pressed
        "result":    None,             # final LINE_Y or None (cancel)
    }

    def on_mouse(event, x, y, flags, param):
        # Update preview line Y as the mouse moves
        if event == cv2.EVENT_MOUSEMOVE:
            state["line_y"] = max(1, min(y, h - 1))

        # Left-click confirms the position
        if event == cv2.EVENT_LBUTTONDOWN:
            state["line_y"]    = max(1, min(y, h - 1))
            state["confirmed"] = True

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, w, h)
    cv2.setMouseCallback(window_name, on_mouse)

    print(f"\n[LineSelector] Click on the frame to place the tripwire line.")
    print(f"[LineSelector] Press ENTER or SPACE to confirm, ESC to use default ({default_line_y}).\n")

    while True:
        display = _draw_overlay(first_frame, state["line_y"], state["confirmed"])
        cv2.imshow(window_name, display)

        key = cv2.waitKey(30) & 0xFF

        if key in (13, 32):                     # ENTER or SPACE — confirm
            state["result"] = state["line_y"]
            print(f"[LineSelector] LINE_Y set to {state['result']}")
            break

        if key == 27:                           # ESC — cancel, use default
            state["result"] = default_line_y
            print(f"[LineSelector] Cancelled. Using default LINE_Y = {default_line_y}")
            break

        # Window closed by user
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            state["result"] = default_line_y
            print(f"[LineSelector] Window closed. Using default LINE_Y = {default_line_y}")
            break

    cv2.destroyWindow(window_name)
    return state["result"]