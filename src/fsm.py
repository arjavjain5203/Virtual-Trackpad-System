
from enum import Enum, auto
import time

class LeftHandMode(Enum):
    NEUTRAL = auto()
    ARMED = auto()
    CLICK_MODE = auto()
    SCROLL_MODE = auto()
    SYSTEM_MODE = auto()
    DRAG_MODE = auto()

class RightHandAction(Enum):
    IDLE = auto()
    CURSOR = auto()
    TAP = auto()
    DRAG = auto()
    SCROLL = auto()
    FLICK = auto()
    CANCEL = auto()

class GestureFSM:
    def __init__(self, debounce_frames=5):
        self.mode = LeftHandMode.NEUTRAL
        self.action = RightHandAction.IDLE
        
        self.debounce_frames = debounce_frames
        
        self.pending_mode = None
        self.pending_mode_frames = 0
        
        self.pending_action = None
        self.pending_action_frames = 0

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

        # 2. Determine Right Hand Action (Allowed by Mode)
        # If Mode is NEUTRAL, Action is forced IDLE
        if self.mode == LeftHandMode.NEUTRAL:
            self.action = RightHandAction.IDLE
            return self.mode, self.action

        target_action = self._detect_right_action(right_landmarks, self.mode)
        
        # Debounce Action? Maybe less debounce needed for responsiveness?
        # For discrete actions (TAP), we might handle it differently (immediate trigger)
        # For continuous (CURSOR), immediate.
        
        self.action = target_action 
        # (Skipping complex debounce for right hand for now to ensure low latency, 
        # unless noise is high. Vision filter handles jitter).
        
        return self.mode, self.action

    def _detect_left_mode(self, coords):
        if not coords:
            return LeftHandMode.NEUTRAL
            
        # Analysis
        fingers = self._get_fingers_up(coords)
        num = len(fingers)
        
        # Left Hand Grammar
        # Fist (0) -> NEUTRAL
        # Open (5) -> ARMED
        # Thumb only -> CLICK_MODE
        # 2 Fingers (Index+Middle) -> SCROLL_MODE
        # 3 Fingers -> SYSTEM_MODE
        # OK Sign (Index touch Thumb) -> DRAG_MODE (or similar)
        
        if num == 0:
            return LeftHandMode.NEUTRAL
        elif num == 5:
            return LeftHandMode.ARMED
        elif num == 1 and 'Thumb' in fingers:
            return LeftHandMode.CLICK_MODE
        elif num == 2 and 'Index' in fingers and 'Middle' in fingers:
            return LeftHandMode.SCROLL_MODE
        elif num == 3 and 'Index' in fingers and 'Middle' in fingers and 'Ring' in fingers:
            return LeftHandMode.SYSTEM_MODE
        
        # OK Sign check: Index Tip close to Thumb Tip
        d_ok = (coords[8]['x']-coords[4]['x'])**2 + (coords[8]['y']-coords[4]['y'])**2
        if d_ok < 0.002: # Threshold
             return LeftHandMode.DRAG_MODE
             
        return self.mode # Hold state if ambiguous?

    def _detect_right_action(self, coords, mode):
        if not coords:
            return RightHandAction.IDLE
            
        fingers = self._get_fingers_up(coords)
        num = len(fingers)
        
        # Right Hand Execution Grammar dependent on Mode
        
        # Common: Fist -> CANCEL/IDLE
        # BUT: If ARMED, Fist might mean CLICK (User Request)
        
        # ARMED -> Index Move (CURSOR) / Fist (CLICK)
        if mode == LeftHandMode.ARMED:
            if num == 0: # Fist
                return RightHandAction.TAP
            if num == 1 and 'Index' in fingers:
                return RightHandAction.CURSOR

        # Default Cancel for other modes
        if num == 0:
            return RightHandAction.CANCEL
        
        # CLICK_MODE -> Micro Tap
        # Tap logic is hard to detect with just static pose. 
        # Usually "Tap" is a motion.
        # Alternative: pinch to click? Or just Index move = cursor, Pinch = click?
        # The prompt says "Micro tap".
        # Let's map "Pinch" (Thumb+Index) to TAP/CLICK for reliability.
        if mode == LeftHandMode.CLICK_MODE:
             # Check pinch
             d_pinch = (coords[8]['x']-coords[4]['x'])**2 + (coords[8]['y']-coords[4]['y'])**2
             if d_pinch < 0.003:
                 return RightHandAction.TAP
        
        # DRAG_MODE -> Pinch Hold (DRAG)
        if mode == LeftHandMode.DRAG_MODE:
             d_pinch = (coords[8]['x']-coords[4]['x'])**2 + (coords[8]['y']-coords[4]['y'])**2
             if d_pinch < 0.003:
                 return RightHandAction.DRAG
        
        # SCROLL_MODE -> Vertical Move (SCROLL)
        if mode == LeftHandMode.SCROLL_MODE:
            # Just tracking hand Y movement
            return RightHandAction.SCROLL
            
        # SYSTEM_MODE -> Horizontal Flick (FLICK)
        if mode == LeftHandMode.SYSTEM_MODE:
            return RightHandAction.FLICK
            
        return RightHandAction.IDLE

    def _get_fingers_up(self, coords):
        fingers = []
        # distance based finger detection (works for any orientation)
        # Check if Tip is further from Wrist(0) than PIP is.
        
        # Fingers MCP, PIP, DIP, TIP indices
        # Index: 5, 6, 7, 8
        # Middle: 9, 10, 11, 12
        # Ring: 13, 14, 15, 16
        # Pinky: 17, 18, 19, 20
        
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
            
            # If tip is significantly further than pip -> Extended
            if d_tip > d_pip * 1.05: # 5% margin
                fingers.append(name)
        
        # Thumb (Simple check)
        # Thumb is complex. Use the existing logic but tune it.
        d_tip = (coords[4]['x']-coords[0]['x'])**2 + (coords[4]['y']-coords[0]['y'])**2
        d_ip = (coords[3]['x']-coords[0]['x'])**2 + (coords[3]['y']-coords[0]['y'])**2
        
        # Also check relative to index finger MCP (5)
        d_tip_index = (coords[4]['x']-coords[5]['x'])**2 + (coords[4]['y']-coords[5]['y'])**2
        
        if d_tip > d_ip * 1.1 and d_tip_index > 0.005: 
             fingers.append('Thumb')
             
        return fingers
