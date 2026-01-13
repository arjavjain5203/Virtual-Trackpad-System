
from enum import Enum, auto
import time

class LeftHandMode(Enum):
    NEUTRAL = auto()
    ARMED = auto()
    CLICK_MODE = auto()
    SCROLL_MODE = auto()
    NAVIGATION_MODE = auto()
    DRAG_MODE = auto()

class RightHandAction(Enum):
    IDLE = auto()
    CURSOR = auto()
    TAP = auto()
    DRAG = auto()
    SCROLL = auto()
    FLICK = auto() # Actually SWIPE
    PUSH = auto()
    CANCEL = auto()

class GestureFSM:
    def __init__(self, debounce_frames=5):
        self.mode = LeftHandMode.NEUTRAL
        self.action = RightHandAction.IDLE
        
        self.debounce_frames = debounce_frames
        
        self.pending_mode = None
        self.pending_mode_frames = 0
        
        # Swipe Logic
        self.rh_history = [] # List of (timestamp, x, y)
        self.HISTORY_LENGTH = 10 # Frames to keep for analysis (approx 300ms at 30fps)
        self.last_swipe_time = 0
        self.SWIPE_COOLDOWN = 0.5 # Seconds
        self.pending_push_frames = 0

    def update(self, left_landmarks, right_landmarks):
        """
        Update state based on both hands.
        Returns (mode, action)
        """
        # 1. Determine Left Hand Mode
        target_mode = self._detect_left_mode(left_landmarks)
        
        if target_mode != self.mode:
            if target_mode == self.pending_mode:
                self.pending_mode_frames += 1
            else:
                self.pending_mode = target_mode
                self.pending_mode_frames = 1
            
            if self.pending_mode_frames >= self.debounce_frames:
                self.mode = target_mode
                self.pending_mode_frames = 0
        else:
            self.pending_mode_frames = 0

        # Update History for Swipe
        if right_landmarks:
            cx, cy = right_landmarks[9]['px'], right_landmarks[9]['py'] # Use MCP/Palm center for stability
            self.rh_history.append((time.time(), cx, cy))
            if len(self.rh_history) > self.HISTORY_LENGTH:
                self.rh_history.pop(0)
        else:
            self.rh_history = []

        # 2. Determine Right Hand Action (Allowed by Mode)
        # If Mode is NEUTRAL, Action is forced IDLE
        if self.mode == LeftHandMode.NEUTRAL:
            self.action = RightHandAction.IDLE
            return self.mode, self.action

        target_action = self._detect_right_action(right_landmarks, self.mode)
        
        self.action = target_action 
        
        return self.mode, self.action

    def _detect_left_mode(self, coords):
        if not coords:
            return LeftHandMode.NEUTRAL
            
        fingers = self._get_fingers_up(coords)
        num = len(fingers)
        
        if num == 0:
            return LeftHandMode.NEUTRAL
        elif num == 5:
            return LeftHandMode.ARMED
        elif num == 1 and 'Thumb' in fingers:
            return LeftHandMode.CLICK_MODE
        elif num == 2 and 'Index' in fingers and 'Middle' in fingers:
            # Check if ring is down (redundant but safe)
            return LeftHandMode.SCROLL_MODE
        elif num == 3 and 'Index' in fingers and 'Middle' in fingers and 'Ring' in fingers:
            return LeftHandMode.NAVIGATION_MODE
        
        # OK Sign check
        d_ok = (coords[8]['x']-coords[4]['x'])**2 + (coords[8]['y']-coords[4]['y'])**2
        if d_ok < 0.002: # Threshold
             return LeftHandMode.DRAG_MODE
             
        return self.mode

    def _detect_right_action(self, coords, mode):
        if not coords:
            return RightHandAction.IDLE
            
        fingers = self._get_fingers_up(coords)
        num = len(fingers)
        
        # Common: Fist -> CANCEL
        if mode == LeftHandMode.ARMED:
            if num == 0: return RightHandAction.TAP # Fist Click
            if num == 1 and 'Index' in fingers: return RightHandAction.CURSOR

        if num == 0:
            return RightHandAction.CANCEL
        
        if mode == LeftHandMode.CLICK_MODE:
             # Pinch
             d_pinch = (coords[8]['x']-coords[4]['x'])**2 + (coords[8]['y']-coords[4]['y'])**2
             if d_pinch < 0.003: return RightHandAction.TAP
        
        if mode == LeftHandMode.DRAG_MODE:
             d_pinch = (coords[8]['x']-coords[4]['x'])**2 + (coords[8]['y']-coords[4]['y'])**2
             if d_pinch < 0.003: return RightHandAction.DRAG
        
        if mode == LeftHandMode.SCROLL_MODE:
            return RightHandAction.SCROLL
            
        if mode == LeftHandMode.NAVIGATION_MODE:
            # Check Swipe / Push
            # 1. Palm Push (Open Hand 5 fingers moving forward? Hard to detect Z w/o depth)
            # Or just Open Palm static? user said "Palm push forward" -> "Space". 
            # Let's map "Open Palm (5)" to PUSH for now, maybe with Z check if possible.
            # Using simple "5 fingers" for now.
            # 1. PUSH (Space) - Debounced (5 frames)
            if num == 5:
                self.pending_push_frames += 1
                if self.pending_push_frames > 4:
                    return RightHandAction.PUSH
            else:
                self.pending_push_frames = 0

            # 2. Swipe (Two fingers: Index+Middle)
            if num == 2 and 'Index' in fingers and 'Middle' in fingers:
                # Check Swipe Logic
                swipe = self._check_swipe()
                if swipe:
                    return swipe # Returns FLICK (we need to pass direction info, maybe stored separately?)
                    # Wait, Enum only has FLICK. We need to distinguish direction.
                    # We can store swipe direction in a member var and read it in main logic.
                    
                # If no swipe detected yet, keep idle or tracking?
                # Ideally we don't want to trigger FLICK constantly.
                pass

        return RightHandAction.IDLE # FLICK is handled via internal check return

    def _check_swipe(self):
        if len(self.rh_history) < 3: return None
        if time.time() - self.last_swipe_time < self.SWIPE_COOLDOWN: return None
        
        # Get start and end
        t_start, x_start, y_start = self.rh_history[0]
        t_end, x_end, y_end = self.rh_history[-1]
        
        dt = t_end - t_start
        if dt > 0.5: return None # Too slow (>500ms). Relaxed from 0.2
        if dt < 0.05: return None # Too fast/noise
        
        dx = x_end - x_start
        dy = y_end - y_start
        
        dist = (dx**2 + dy**2)**0.5
        
        # User said > 60px. 
        if dist < 40: return None # Be lenient (40px)
        
        # Direction Consistency (check middle point)
        # Simply check if major axis movement > minor axis movement ratio
        ratio_threshold = 1.3 # Relaxed from 2.0 (Allows more effective diagonal swipes)
        
        if abs(dx) > abs(dy):
            # Horizontal
            if abs(dx) / (abs(dy) + 1) < ratio_threshold: return None 
            
            # Valid Swipe
            self.last_swipe_time = time.time()
            # Invert Left/Right? Camera is mirrored?
            # Main.py mirrors frame: frame = cv2.flip(frame, 1)
            # So Left on screen is Left in world.
            # If user swipes Right (move hand right), dx > 0.
            self.swipe_direction = "RIGHT" if dx > 0 else "LEFT"
            return RightHandAction.FLICK
        else:
            # Vertical
            if abs(dy) / (abs(dx) + 1) < ratio_threshold: return None
            
            self.last_swipe_time = time.time()
            self.swipe_direction = "DOWN" if dy > 0 else "UP"
            return RightHandAction.FLICK

    def _get_fingers_up(self, coords):
        # ... (Existing logic same)
        fingers = []
        finger_indices = {
            'Index': (6, 8),
            'Middle': (10, 12),
            'Ring': (14, 16),
            'Pinky': (18, 20)
        }
        
        wrist = coords[0]
        
        for name, (pip_idx, tip_idx) in finger_indices.items():
            tip = coords[tip_idx]
            pip = coords[pip_idx]
            d_tip = (tip['x']-wrist['x'])**2 + (tip['y']-wrist['y'])**2
            d_pip = (pip['x']-wrist['x'])**2 + (pip['y']-wrist['y'])**2
            if d_tip > d_pip * 1.05: 
                fingers.append(name)
        
        d_tip = (coords[4]['x']-coords[0]['x'])**2 + (coords[4]['y']-coords[0]['y'])**2
        d_ip = (coords[3]['x']-coords[0]['x'])**2 + (coords[3]['y']-coords[0]['y'])**2
        d_tip_index = (coords[4]['x']-coords[5]['x'])**2 + (coords[4]['y']-coords[5]['y'])**2
        
        if d_tip > d_ip * 1.1 and d_tip_index > 0.005: 
             fingers.append('Thumb')
             
        return fingers
