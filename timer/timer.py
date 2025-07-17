import time
import threading
import sys
from typing import Optional

class LiveTimer:
    def __init__(self):
        self.start_time: Optional[float] = None
        self.pause_time: float = 0
        self.is_running: bool = False
        self.is_paused: bool = False
        self.total_paused_time: float = 0
        self.timer_thread: Optional[threading.Thread] = None
        self.stop_timer: bool = False
        
    def start(self):
        """Startet den Timer"""
        self.start_time = time.time()
        self.is_running = True
        self.is_paused = False
        self.stop_timer = False
        self.total_paused_time = 0
        
        # Starte Timer-Thread
        self.timer_thread = threading.Thread(target=self._display_timer)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
    def pause(self):
        """Pausiert den Timer"""
        if self.is_running and not self.is_paused:
            self.pause_time = time.time()
            self.is_paused = True
            
    def resume(self):
        """Setzt den Timer fort"""
        if self.is_running and self.is_paused:
            self.total_paused_time += time.time() - self.pause_time
            self.is_paused = False
            
    def stop(self) -> int:
        """Stoppt den Timer und gibt verstrichene Zeit zurück"""
        if self.is_running:
            if self.is_paused:
                self.total_paused_time += time.time() - self.pause_time
            self.is_running = False
            self.stop_timer = True
            
            # Warte auf Thread-Ende
            if self.timer_thread:
                self.timer_thread.join(timeout=1)
                
        return int(self.get_elapsed_time())
        
    def get_elapsed_time(self) -> float:
        """Gibt die verstrichene Zeit zurück"""
        if not self.start_time:
            return 0.0
            
        current_time = time.time()
        if self.is_paused:
            elapsed = self.pause_time - self.start_time - self.total_paused_time
        else:
            elapsed = current_time - self.start_time - self.total_paused_time
            
        return max(0.0, elapsed)
        
    def _display_timer(self):
        """Zeigt den Timer live an"""
        while self.is_running and not self.stop_timer:
            elapsed = self.get_elapsed_time()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            status = "⏸️  PAUSIERT" if self.is_paused else "⏱️  LÄUFT"
            
            # Cursor an Anfang der Zeile, überschreibe vorherige Ausgabe
            sys.stdout.write(f"\r   {status} - Zeit: {minutes:02d}:{seconds:02d}")
            sys.stdout.flush()
            
            time.sleep(1)
            
        # Finale Zeit anzeigen
        if not self.stop_timer:
            elapsed = self.get_elapsed_time()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            sys.stdout.write(f"\r   ⏰ Fertig! - Zeit: {minutes:02d}:{seconds:02d}\n")
            sys.stdout.flush()