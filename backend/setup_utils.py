import subprocess
import platform
import shutil

def check_ffmpeg() -> bool:
    """Check if ffmpeg is available in the system"""
    try:
        # First try using shutil which is more reliable
        if shutil.which('ffmpeg'):
            return True
            
        # Fallback to subprocess
        if platform.system().lower() == 'windows':
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
        else:
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        
        return result.returncode == 0
    except Exception:
        return False 