import sys
import time

try:
    import select
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

class KeyboardListener:
    """Klasse für non-blocking Keyboard Input"""
    
    def __init__(self):
        self.old_settings = None
        self.available = HAS_TERMIOS
        
    def __enter__(self):
        if not self.available:
            return self
            
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        return self
        
    def __exit__(self, type, value, traceback):
        if self.available and self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        
    def get_key(self):
        """Nicht-blockierender Tastendruck"""
        if not self.available:
            return None
            
        if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None

def format_time(seconds: int) -> str:
    """Formatiert Sekunden zu MM:SS"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def get_simple_input(prompt: str) -> str:
    """Einfache Eingabe mit Fehlerbehandlung"""
    try:
        return input(prompt).strip()
    except KeyboardInterrupt:
        print("\n❌ Eingabe abgebrochen")
        return ""
    except EOFError:
        print("\n❌ Eingabe beendet")
        return ""