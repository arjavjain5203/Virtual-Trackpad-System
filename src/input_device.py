import platform
import logging

logger = logging.getLogger(__name__)

class VirtualMouse:
    def __init__(self):
        self.os = platform.system()
        self.impl = None
        
        if self.os == 'Linux':
            try:
                import evdev
                from evdev import UInput, ecodes as e
                self.evdev = evdev
                self.e = e
                # Add Keyboard Capabilities
                cap = {
                    e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
                    e.EV_KEY: (e.BTN_LEFT, e.BTN_RIGHT, 
                               e.KEY_LEFT, e.KEY_RIGHT, e.KEY_UP, e.KEY_DOWN, e.KEY_SPACE),
                }
                self.impl = UInput(cap, name="Virtual Trackpad", version=0x3)
                logger.info("Initialized Linux evdev Input")
            except Exception as ex:
                logger.error(f"Failed to init Linux Input: {ex}")
                
        elif self.os == 'Windows' or self.os == 'Darwin': # Darwin is MacOS
            try:
                import pyautogui
                self.pyautogui = pyautogui
                self.pyautogui.FAILSAFE = False # Prevent fail-safe for now
                self.impl = "pyautogui"
                logger.info(f"Initialized {self.os} pyautogui Input")
            except ImportError:
                 logger.error("pyautogui not installed. Run 'pip install pyautogui'")

    def move(self, dx, dy):
        """Move mouse relative by dx, dy."""
        if not self.impl: return

        if self.os == 'Linux':
            self.impl.write(self.e.EV_REL, self.e.REL_X, int(dx))
            self.impl.write(self.e.EV_REL, self.e.REL_Y, int(dy))
            self.impl.syn()
        else:
            # PyAutoGUI moveRel
            self.pyautogui.moveRel(dx, dy, _pause=False)

    def scroll(self, dy):
        """Scroll wheel."""
        if not self.impl: return
        
        if self.os == 'Linux':
            self.impl.write(self.e.EV_REL, self.e.REL_WHEEL, int(dy))
            self.impl.syn()
        else:
             # PyAutoGUI scroll (amount varies by OS, usually 10 clicks)
             self.pyautogui.scroll(int(dy * 10), _pause=False)

    def click(self, button, value):
        """
        button: e.BTN_LEFT or e.BTN_RIGHT (Mapped manually for windows)
        value: 1 for press, 0 for release
        """
        if not self.impl: return

        if self.os == 'Linux':
             self.impl.write(self.e.EV_KEY, button, value)
             self.impl.syn()
        else:
            # Map button
            btn_str = 'left'
            # Assuming button check from main.py passes evdev constants
            # Simple Hack: We know main.py uses evdev.ecodes.BTN_LEFT (272)
            if button == 272: btn_str = 'left'
            elif button == 273: btn_str = 'right'
            
            if value == 1:
                self.pyautogui.mouseDown(button=btn_str, _pause=False)
            else:
                self.pyautogui.mouseUp(button=btn_str, _pause=False)
                
    def press_key(self, key_code):
        """
        Press and release a key.
        key_code: evdev key code (e.g., e.KEY_LEFT)
        """
        if not self.impl: return
        
        if self.os == 'Linux':
            self.impl.write(self.e.EV_KEY, key_code, 1) # Down
            self.impl.syn()
            self.impl.write(self.e.EV_KEY, key_code, 0) # Up
            self.impl.syn()
        else:
            # Map evdev key codes to pyautogui strings
            # This requires knowing the integer values of evdev keys if we import them in main
            # KEY_LEFT=105, KEY_RIGHT=106, KEY_UP=103, KEY_DOWN=108, KEY_SPACE=57
            # We will use a simple mapping or pass strings from main if we refactor.
            # For now, let's assume we receive evdev ints.
            
            key_map = {
                105: 'left',
                106: 'right',
                103: 'up',
                108: 'down',
                57: 'space'
            }
            
            k = key_map.get(key_code)
            if k:
                self.pyautogui.press(k)
    def close(self):
        if self.os == 'Linux' and self.impl and hasattr(self.impl, 'close'):
            self.impl.close()
        # Windows/Mac PyAutoGUI doesn't need explicit close
