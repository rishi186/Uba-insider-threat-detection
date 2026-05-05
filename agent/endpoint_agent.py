"""
UBA Endpoint Agent — System-wide Mouse Biometric Tracker.

This agent runs in the background on an employee's workstation,
capturing ALL mouse events system-wide (not just in the browser)
and streaming them to the UBA backend for real-time anomaly detection.

Architecture:
  - Captures mouse move/click/scroll at ~60Hz via pynput
  - Buffers events locally
  - Flushes to backend every 1 second as summarized batches
  - Auto-authenticates with employee credentials
  - Runs as a background process (no GUI)

Usage:
  python agent/endpoint_agent.py --username rishi --password rishi123

Requirements:
  pip install pynput requests
"""

import argparse
import logging
import signal
import sys
import threading
import time
import getpass
import platform
import socket
import json
import hmac
import hashlib

import requests
from pynput import mouse, keyboard
from collections import deque
from datetime import datetime

# ── Optional: Try importing pynput, provide helpful error if missing ──
try:
    from pynput import mouse, keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# =============================================================================
# CONFIGURATION
# =============================================================================
DEFAULT_API_URL = "http://localhost:8000"
FLUSH_INTERVAL = 1.0        # seconds between batch uploads
MAX_BUFFER_SIZE = 500        # max events before forced flush
SCREEN_WIDTH = 1920          # will be detected automatically
SCREEN_HEIGHT = 1080
LOG_FORMAT = "%(asctime)s │ %(levelname)-5s │ %(message)s"


# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%H:%M:%S")
logger = logging.getLogger("uba.agent")


# =============================================================================
# ENDPOINT AGENT
# =============================================================================
class EndpointAgent:
    """
    System-wide mouse biometric tracking agent.
    
    Captures all mouse events from the OS, buffers them, and uploads
    to the UBA backend in real-time batches.
    """

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        
        # Auth state
        self.token = None
        self.user_info = None
        self.user_id = None
        self.pc_id = None
        
        # Session state
        self.session_id = None
        self.is_tracking = False
        
        # Event buffer (thread-safe)
        self.event_buffer = deque(maxlen=MAX_BUFFER_SIZE * 2)
        self.buffer_lock = threading.Lock()
        
        # Keystroke tracking
        self.total_keystrokes = 0
        self.keystrokes_since_flush = 0
        self.key_press_times = {}
        self.dwell_times = []
        self.flight_times = []
        self.deletions_since_flush = 0
        self.last_key_release_time = 0.0

        # Stats
        self.total_events_sent = 0
        self.total_flushes = 0
        self.errors = 0
        self.start_time = None
        
        # Screen dimensions
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        self._detect_screen_size()

    def _detect_screen_size(self):
        """Detect screen resolution."""
        try:
            if platform.system() == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                self.screen_width = user32.GetSystemMetrics(0)
                self.screen_height = user32.GetSystemMetrics(1)
                logger.info("Screen detected: %dx%d", self.screen_width, self.screen_height)
        except Exception:
            logger.warning("Could not detect screen size, using defaults")

    # ── Authentication ───────────────────────────────────────────────────────

    def authenticate(self) -> bool:
        """Login to the UBA backend and get JWT token."""
        try:
            logger.info("Authenticating as '%s'...", self.username)
            resp = requests.post(
                f"{self.api_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.error("Auth failed: %s", resp.json().get("detail", "Unknown error"))
                return False
            
            data = resp.json()
            self.token = data["token"]
            self.user_info = data["user"]
            self.user_id = data["user"]["user_id"]
            self.pc_id = data["user"].get("pc_id", platform.node())
            
            logger.info("✓ Authenticated: %s (%s)", self.user_info["name"], self.user_id)
            return True
            
        except requests.ConnectionError:
            logger.error("Cannot connect to backend at %s", self.api_url)
            return False
        except Exception as e:
            logger.error("Auth error: %s", e)
            return False

    def _headers(self) -> dict:
        """Get auth headers for API calls."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ── Session Management ───────────────────────────────────────────────────

    def start_session(self) -> bool:
        """Start a mouse tracking session on the backend."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/mouse/session/start",
                json={
                    "user_id": self.user_id,
                    "pc_id": self.pc_id,
                    "application": "System-wide Agent",
                    "screen_width": self.screen_width,
                    "screen_height": self.screen_height,
                },
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code != 200:
                logger.error("Session start failed: %s", resp.text)
                return False
            
            data = resp.json()
            self.session_id = data["session_id"]
            logger.info("✓ Session started: %s", self.session_id)
            return True
            
        except Exception as e:
            logger.error("Session start error: %s", e)
            return False

    def end_session(self):
        """End the current tracking session."""
        if not self.session_id:
            return
        try:
            # Flush remaining events first
            self._flush_events()
            
            resp = requests.post(
                f"{self.api_url}/api/mouse/session/end",
                json={
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                },
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                anomaly = data.get("anomaly_scores", {}).get("overall", 0)
                logger.info("✓ Session ended. Anomaly Score: %.1f", anomaly)
            else:
                logger.warning("Session end returned %d", resp.status_code)
                
        except Exception as e:
            logger.error("Session end error: %s", e)
        finally:
            self.session_id = None

    # ── Event Capture ────────────────────────────────────────────────────────

    def _on_move(self, x, y):
        """Callback for mouse movement."""
        if not self.is_tracking:
            return
        with self.buffer_lock:
            self.event_buffer.append({
                "x": float(x),
                "y": float(y),
                "timestamp": time.time() * 1000,  # ms
                "event_type": "move",
                "button": None,
                "scroll_delta": None,
            })

    def _on_click(self, x, y, button, pressed):
        """Callback for mouse clicks."""
        if not self.is_tracking or not pressed:
            return
        btn_map = {
            mouse.Button.left: 0,
            mouse.Button.middle: 1,
            mouse.Button.right: 2,
        }
        with self.buffer_lock:
            self.event_buffer.append({
                "x": float(x),
                "y": float(y),
                "timestamp": time.time() * 1000,
                "event_type": "click",
                "button": btn_map.get(button, 0),
                "scroll_delta": None,
            })

    def _on_scroll(self, x, y, dx, dy):
        """Callback for mouse scrolling."""
        if not self.is_tracking:
            return
        with self.buffer_lock:
            self.event_buffer.append({
                "x": float(x),
                "y": float(y),
                "timestamp": time.time() * 1000,
                "event_type": "scroll",
                "button": None,
                "scroll_delta": float(dy),
            })

    def _on_key_press(self, key):
        """Callback for keystrokes."""
        if not self.is_tracking:
            return
        now = time.time() * 1000
        
        with self.buffer_lock:
            self.total_keystrokes += 1
            self.keystrokes_since_flush += 1
            
            # Flight time (time since last key release)
            if self.last_key_release_time > 0 and (now - self.last_key_release_time) < 2000:
                self.flight_times.append(now - self.last_key_release_time)
                
            try:
                # Store press time for dwell calculation
                k = key.char
            except AttributeError:
                k = str(key)
                if key in (keyboard.Key.backspace, keyboard.Key.delete):
                    self.deletions_since_flush += 1
                    
            if k not in self.key_press_times:
                self.key_press_times[k] = now

    def _on_key_release(self, key):
        """Calculate dwell time on release."""
        if not self.is_tracking:
            return
        now = time.time() * 1000
        self.last_key_release_time = now
        
        try:
            k = key.char
        except AttributeError:
            k = str(key)
            
        with self.buffer_lock:
            if k in self.key_press_times:
                dwell = now - self.key_press_times.pop(k)
                if dwell < 2000: # sanity check
                    self.dwell_times.append(dwell)

    # ── Event Flushing ───────────────────────────────────────────────────────

    def _flush_events(self):
        """Send buffered events to the backend."""
        with self.buffer_lock:
            if not self.event_buffer:
                return
            events = list(self.event_buffer)
            self.event_buffer.clear()

        if not self.session_id or not events:
            return

        try:
            keyboard_metrics = None
            with self.buffer_lock:
                if self.keystrokes_since_flush > 0:
                    avg_dwell = sum(self.dwell_times) / max(len(self.dwell_times), 1)
                    avg_flight = sum(self.flight_times) / max(len(self.flight_times), 1)
                    del_ratio = self.deletions_since_flush / self.keystrokes_since_flush
                    
                    keyboard_metrics = {
                        "total_strokes": self.keystrokes_since_flush,
                        "avg_dwell_time_ms": avg_dwell,
                        "avg_flight_time_ms": avg_flight,
                        "delete_ratio": del_ratio
                    }
                    
                    self.keystrokes_since_flush = 0
                    self.deletions_since_flush = 0
                    self.dwell_times.clear()
                    self.flight_times.clear()
        
            payload = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "events": events,
                "screen_width": self.screen_width,
                "screen_height": self.screen_height,
                "keyboard_metrics": keyboard_metrics
            }
            body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            
            # HMAC Signature for payload integrity
            secret = b"SUPER_SECRET_HMAC_KEY"
            signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
            
            headers = self._headers()
            headers["Content-Type"] = "application/json"
            headers["X-HMAC-Signature"] = signature

            resp = requests.post(
                f"{self.api_url}/api/mouse/events",
                data=body,
                headers=headers,
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.total_events_sent += len(events)
                self.total_flushes += 1
                anomaly = data.get("current_anomaly", 0)
                
                # Print status every 10 flushes
                if self.total_flushes % 10 == 0:
                    elapsed = time.time() - self.start_time
                    rate = self.total_events_sent / max(elapsed, 1)
                    logger.info(
                        "📊 %d events sent (%.0f/s) │ anomaly: %.1f │ flushes: %d",
                        self.total_events_sent, rate, anomaly, self.total_flushes,
                    )
            else:
                self.errors += 1
                if self.errors <= 5:
                    logger.warning("Flush failed (%d): %s", resp.status_code, resp.text[:100])
                    
        except requests.ConnectionError:
            self.errors += 1
            if self.errors <= 3:
                logger.warning("Backend unreachable, buffering events...")
        except Exception as e:
            self.errors += 1
            logger.error("Flush error: %s", e)

    def _flush_loop(self):
        """Background thread that flushes events at regular intervals."""
        while self.is_tracking:
            time.sleep(FLUSH_INTERVAL)
            self._flush_events()

    # ── Main Run Loop ────────────────────────────────────────────────────────

    def run(self):
        """
        Main entry point. Authenticates, starts session, and begins tracking.
        Runs until interrupted with Ctrl+C.
        """
        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║     UBA Endpoint Agent — Mouse Biometric Tracker    ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        # Authenticate
        if not self.authenticate():
            logger.error("Authentication failed. Exiting.")
            sys.exit(1)

        # Start session
        if not self.start_session():
            logger.error("Could not start tracking session. Exiting.")
            sys.exit(1)

        self.is_tracking = True
        self.start_time = time.time()

        # Start flush thread
        flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        flush_thread.start()

        # Start mouse and keyboard listener
        logger.info("🖱  Tracking ALL mouse activity system-wide...")
        logger.info("⌨  Tracking keystroke dynamics (dwell/flight time)...")
        logger.info("    Press Ctrl+C to stop.\n")

        m_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        m_listener.start()
        
        k_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        k_listener.start()

        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print()
            logger.info("Stopping agent...")
        finally:
            self.is_tracking = False
            m_listener.stop()
            k_listener.stop()
            time.sleep(0.5)  # Let flush thread finish
            self.end_session()
            
            elapsed = time.time() - (self.start_time or time.time())
            print()
            print("┌─────────────────── Session Summary ────────────────────┐")
            print(f"│  User:       {self.user_info['name']:<39} │")
            print(f"│  Duration:   {elapsed:.0f} seconds{' '*(32-len(f'{elapsed:.0f} seconds'))} │")
            print(f"│  Events:     {self.total_events_sent:<39} │")
            print(f"│  Flushes:    {self.total_flushes:<39} │")
            print(f"│  Errors:     {self.errors:<39} │")
            print(f"│  Rate:       {self.total_events_sent/max(elapsed,1):.1f} events/sec{' '*(28-len(f'{self.total_events_sent/max(elapsed,1):.1f} events/sec'))} │")
            print("└────────────────────────────────────────────────────────┘")
            print()


# =============================================================================
# CLI
# =============================================================================
def main():
    if not HAS_PYNPUT:
        print("ERROR: pynput is required. Install with:")
        print("  pip install pynput")
        sys.exit(1)
    
    if not HAS_REQUESTS:
        print("ERROR: requests is required. Install with:")
        print("  pip install requests")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="UBA Endpoint Agent — System-wide Mouse Biometric Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Demo credentials:
  --username rishi   --password rishi123  (Admin)
  --username priya   --password priya123
  --username alex    --password alex123
  --username marcus  --password marcus123
  --username sarah   --password sarah123
        """,
    )
    parser.add_argument(
        "--username", "-u", required=True,
        help="Employee username for authentication",
    )
    parser.add_argument(
        "--password", "-p", required=True,
        help="Employee password",
    )
    parser.add_argument(
        "--api-url", default=DEFAULT_API_URL,
        help=f"Backend API URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    agent = EndpointAgent(
        api_url=args.api_url,
        username=args.username,
        password=args.password,
    )
    agent.run()


if __name__ == "__main__":
    main()
