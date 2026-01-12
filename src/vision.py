
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    if not hasattr(mp, 'solutions'):
        raise ImportError("mediapipe.solutions not found")
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False
    logger.warning("MediaPipe not found or broken. Using Mock Vision Engine.")

class VisionEngine:
    def __init__(self, max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5):
        self.mock_mode = not HAS_MEDIAPIPE
        if self.mock_mode:
            logger.warning("Initializing VisionEngine in MOCK MODE.")
            return

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=1
        )
        self.mp_draw = mp.solutions.drawing_utils

    def process(self, frame):
        """
        Process a BGR frame and return a dictionary of landmarks {'Left': lm, 'Right': lm}.
        """
        if self.mock_mode:
            # Return dummy landmarks for testing if needed, or None
            return {}

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        
        results = self.hands.process(rgb_frame)
        
        rgb_frame.flags.writeable = True
        
        hands = {}
        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, hand_handedness in enumerate(results.multi_handedness):
                label = hand_handedness.classification[0].label # "Left" or "Right"
                landmarks = results.multi_hand_landmarks[idx]
                hands[label] = landmarks
                
        return hands

    def get_landmarks_dict(self, landmarks, width, height):
        """
        Convert normalized landmarks to pixel coordinates dictionary.
        Also returns normalized coordinates for logic.
        """
        if self.mock_mode:
             return None

        if not landmarks:
            return None
            
        coords = {}
        # Key points mapping
        # 0: Wrist
        # 4: Thumb Tip
        # 8: Index Tip
        # 12: Middle Tip
        # 16: Ring Tip
        # 20: Pinky Tip
        
        for id, lm in enumerate(landmarks.landmark):
            cx, cy = int(lm.x * width), int(lm.y * height)
            coords[id] = {
                'x': lm.x, 
                'y': lm.y, 
                'z': lm.z, 
                'px': cx, 
                'py': cy
            }
            
        return coords

    def is_finger_up(self, coords, finger_tip_id, finger_dip_id):
        if self.mock_mode: return False
        return coords[finger_tip_id]['y'] < coords[finger_dip_id]['y']
