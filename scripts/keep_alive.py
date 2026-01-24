import ctypes
import time
import sys

# Windows API constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def prevent_sleep():
    """
    Tells Windows to keep the system and display active.
    """
    print("Sovereign Spirit: Keep-Alive Active.")
    print("Signals: SYSTEM_REQUIRED | DISPLAY_REQUIRED")
    print("Press Ctrl+C to stop.")
    
    try:
        # Set the state to prevent sleep/lock
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        
        while True:
            time.sleep(60)  # Keep the script running
            
    except KeyboardInterrupt:
        print("\nSovereign Spirit: Keep-Alive Terminated.")
    finally:
        # Restore original state
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        print("Sovereign Spirit: System state restored.")

if __name__ == "__main__":
    prevent_sleep()
