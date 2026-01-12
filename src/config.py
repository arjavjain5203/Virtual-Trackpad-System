
# Configuration for Virtual Trackpad

# Camera
CAMERA_ID = 0
WIDTH = 640
HEIGHT = 480
FPS = 30

# Vision
MAX_NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.8 # Increased for better accuracy
MIN_TRACKING_CONFIDENCE = 0.8  # Increased for better tracking

# Filter
FILTER_MIN_CUTOFF = 0.5   # Controls jitter when slow. Keep low for precision.
FILTER_BETA = 6.0        # Controls lag when moving. Increased for more responsiveness.
FILTER_D_CUTOFF = 1.0

# Input Sensitivity
# Increased to make movement "easier" (less physical distance needed)
SENSITIVITY_X = 4.0 
SENSITIVITY_Y = 4.0
SCROLL_SENSITIVITY = 1.0 # Faster scrolling

# Gesture
DEBOUNCE_FRAMES = 5
