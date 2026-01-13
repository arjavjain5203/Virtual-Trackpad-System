import cv2
import time
import sys
import numpy as np
import logging
import evdev # Added missing import
from vision import VisionEngine
from filter import SignalFilter
from fsm import GestureFSM, LeftHandMode, RightHandAction
try:
    from input_device import VirtualMouse
except ImportError:
    VirtualMouse = None # Handle testing without uinput privileges logic
    
import config

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Virtual Trackpad System...")
    
    # Initialize Components
    try:
        vision = VisionEngine(
            max_num_hands=config.MAX_NUM_HANDS,
            min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE
        )
        f_filter = SignalFilter(
            min_cutoff=config.FILTER_MIN_CUTOFF,
            beta=config.FILTER_BETA,
            d_cutoff=config.FILTER_D_CUTOFF
        )
        fsm = GestureFSM(debounce_frames=config.DEBOUNCE_FRAMES)
        
        if VirtualMouse:
            try:
                mouse = VirtualMouse()
                logger.info("Virtual Mouse Device Created.")
            except Exception as e:
                logger.error(f"Failed to create VirtualMouse: {e}")
                logger.error("HINT: Run 'sudo ./scripts/install.sh' to install permissions.")
                logger.error("      OR run with 'sudo' for temporary testing.")
                logger.warning("Running in DRY-RUN mode (No Input Output)")
                mouse = None
        else:
            logger.error("Could not import VirtualMouse (evdev/uinput issue?). Running in dry-run mode.")
            mouse = None
            
    except Exception as e:
        logger.error(f"Initialization Failed: {e}")
        return

    # Open Camera
    cap = cv2.VideoCapture(config.CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.FPS)
    
    if not cap.isOpened():
        logger.error("Could not open camera.")
        return

    logger.info("System Ready. Use 'q' to quit.")

    # Filter State
    prev_x, prev_y = 0, 0
    
    # Track previous action to handle state changes (like Click Down/Up)
    last_action = RightHandAction.IDLE
    is_dragging = False # For drag handling
    
    # Open Log File
    log_file = open("gesture_logs.txt", "w")
    log_file.write("Timestamp,Mode,Action,Left_X,Left_Y,Right_X,Right_Y\n")
    
    try:
        while True:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                break
            
            # mirror frame
            frame = cv2.flip(frame, 1)
            
            # Vision Process (Returns dict {'Left': lm, 'Right': lm})
            hands = vision.process(frame)
            
            # Extract coordinates
            left_coords = None
            right_coords = None
            
            if 'Left' in hands:
                left_coords = vision.get_landmarks_dict(hands['Left'], config.WIDTH, config.HEIGHT)
            if 'Right' in hands:
                right_coords = vision.get_landmarks_dict(hands['Right'], config.WIDTH, config.HEIGHT)
            
            # FSM Update (Pass both)
            mode, action = fsm.update(left_coords, right_coords)
            
            # Logging
            lx, ly = (left_coords[8]['x'], left_coords[8]['y']) if left_coords else (0,0)
            rx, ry = (right_coords[8]['x'], right_coords[8]['y']) if right_coords else (0,0)
            log_line = f"{time.time()},{mode.name},{action.name},{lx:.3f},{ly:.3f},{rx:.3f},{ry:.3f}\n"
            log_file.write(log_line)
            
            # Visual Overlay
            cv2.putText(frame, f"Mode: {mode.name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Action: {action.name}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if left_coords:
                 cv2.circle(frame, (left_coords[8]['px'], left_coords[8]['py']), 5, (0, 255, 0), -1)
            if right_coords:
                 cv2.circle(frame, (right_coords[8]['px'], right_coords[8]['py']), 5, (0, 0, 255), -1)
            
            cv2.imshow("Virtual Trackpad Debug", frame)
            
            # Debug: Print detected hands
            print(f"Hands: {list(hands.keys())} | Mode: {mode.name} | Action: {action.name}      ", end='\r')
            
            # --- ACTION HANDLING ---
            
            # 1. State Transition / One-shot triggers
            if action != last_action:
                pass 
                
                # Handle FLICK (Swipe)
                if action == RightHandAction.FLICK:
                    # Determine direction from FSM
                    # We need to access fsm.swipe_direction which we set in fsm._check_swipe
                    # BUT fsm object in main loop is generic.
                    # We should probably return data from FSM or access attribute.
                    # Let's assume we can access fsm.swipe_direction
                    direction = getattr(fsm, 'swipe_direction', None)
                    if mouse and direction:
                        logger.info(f"Swipe Detected: {direction}")
                        if direction == "RIGHT":
                            mouse.press_key(evdev.ecodes.KEY_RIGHT)
                        elif direction == "LEFT":
                            mouse.press_key(evdev.ecodes.KEY_LEFT)
                        elif direction == "UP":
                            mouse.press_key(evdev.ecodes.KEY_UP)
                        elif direction == "DOWN":
                            mouse.press_key(evdev.ecodes.KEY_DOWN)

                # Handle PUSH
                if action == RightHandAction.PUSH:
                    if mouse:
                         logger.info("Push Detected (Space)")
                         mouse.press_key(evdev.ecodes.KEY_SPACE)
                         # Add delay to prevent spam? One-shot is handled by state transition.
                         # PUSH state might persist if hand stays open?
                         # Ideally PUSH should be a momentary trigger or we need debouncing.
                         # Since this block is `if action != last_action`, it only fires ONCE on entry.
                         # So holding PUSH will not spam space. Correct.

                # Handle DRAG Start/End (Pinch)
                if action == RightHandAction.DRAG:
                    if mouse and not is_dragging:
                        mouse.click(evdev.ecodes.BTN_LEFT, 1)
                        is_dragging = True
                        if right_coords:
                             f_filter.reset(right_coords[8]['x'], right_coords[8]['y'])
                             prev_x = right_coords[8]['x']
                             prev_y = right_coords[8]['y']
                             
                elif last_action == RightHandAction.DRAG:
                   if mouse and is_dragging:
                       mouse.click(evdev.ecodes.BTN_LEFT, 0)
                       is_dragging = False

                # Handle TAP (Micro Tap OR Fist Click)
                if action == RightHandAction.TAP:
                    if mouse:
                        mouse.click(evdev.ecodes.BTN_LEFT, 1)
                        time.sleep(0.05) 
                        mouse.click(evdev.ecodes.BTN_LEFT, 0)
                        
                # Handle Cursor Start (reset filter)
                if action == RightHandAction.CURSOR and last_action != RightHandAction.CURSOR:
                    if right_coords:
                         f_filter.reset(right_coords[8]['x'], right_coords[8]['y'])
                         prev_x = right_coords[8]['x']
                         prev_y = right_coords[8]['y']
                
                # Update track
                last_action = action

            # 2. Continuous Actions
            
            if action in [RightHandAction.CURSOR, RightHandAction.DRAG]:
                # Move Cursor (Index Tip 8)
                if right_coords:
                    raw_x = right_coords[8]['x']
                    raw_y = right_coords[8]['y']
                    
                    dt = time.time() - f_filter.last_time if f_filter.last_time else 1.0/config.FPS
                    f_filter.last_time = time.time()
                    
                    sx, sy = f_filter.process(raw_x, raw_y, dt)
                    
                    if prev_x != 0 and prev_y != 0:
                        dx = (sx - prev_x) * 1000 * config.SENSITIVITY_X
                        dy = (sy - prev_y) * 1000 * config.SENSITIVITY_Y
                        
                        if mouse:
                            mouse.move(dx, dy)
                    
                    prev_x, prev_y = sx, sy
                else:
                    prev_x, prev_y = 0, 0
            
            elif action == RightHandAction.SCROLL:
                # Vertical Scroll
                if right_coords:
                    raw_y = right_coords[8]['y']
                    
                    if prev_y != 0:
                         dy = (raw_y - prev_y) * 1000
                         if abs(dy) > 2.0: # threshold
                             if mouse:
                                 # Invert? usually up hand = scroll up
                                 mouse.scroll(dy * config.SCROLL_SENSITIVITY)
                    
                    prev_y = raw_y
                    # Reset X
                    prev_x = right_coords[8]['x']
                else:
                    prev_y = 0

            elif action == RightHandAction.FLICK:
                pass # Handled in state transition
            
            elif action == RightHandAction.PUSH:
                pass # Handled in state transition
                # IDLE / CANCEL
                prev_x, prev_y = 0,0
                # Filter reset on re-entry handle by state transition check above
            
            # Check key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
    except KeyboardInterrupt:
        logger.info("Stopping...")
    except Exception as e:
        logger.error(f"Runtime Error: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        log_file.close()
        if mouse:
            mouse.close()
        logger.info("Clean Exit.")

if __name__ == "__main__":
    main()
