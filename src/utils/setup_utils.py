import subprocess
import platform

def check_ffmpeg():
    """Check if ffmpeg is installed and install if needed.
    
    Returns:
        bool: True if ffmpeg is available or successfully installed, False otherwise
    """
    try:
        # Try to run ffmpeg
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        system = platform.system().lower()
        try:
            if system == 'darwin':  # macOS
                try:
                    # First try normal install
                    subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
                except subprocess.CalledProcessError:
                    try:
                        # Try installing from source if bottle not available
                        print("Attempting to install ffmpeg from source (this may take a while)...")
                        subprocess.run(['brew', 'install', '--build-from-source', 'ffmpeg'], check=True)
                    except subprocess.CalledProcessError:
                        # If both methods fail, try using conda
                        try:
                            subprocess.run(['conda', 'install', '-y', 'ffmpeg', '-c', 'conda-forge'], check=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            print("Failed to install ffmpeg. Please try one of the following:")
                            print("1. Install using Homebrew: brew install --build-from-source ffmpeg")
                            print("2. Install using Conda: conda install -y ffmpeg -c conda-forge")
                            print("3. Download from https://ffmpeg.org/download.html")
                            return False
            elif system == 'linux':
                try:
                    subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                    subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True)
                except subprocess.CalledProcessError:
                    try:
                        # Try using conda if apt fails
                        subprocess.run(['conda', 'install', '-y', 'ffmpeg', '-c', 'conda-forge'], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print("Failed to install ffmpeg. Please try one of the following:")
                        print("1. Install using apt: sudo apt-get install -y ffmpeg")
                        print("2. Install using Conda: conda install -y ffmpeg -c conda-forge")
                        print("3. Download from https://ffmpeg.org/download.html")
                        return False
            else:
                print("Please install ffmpeg using one of the following methods:")
                print("1. Install using Conda: conda install -y ffmpeg -c conda-forge")
                print("2. Download from https://ffmpeg.org/download.html")
                return False
            
            # Verify installation
            try:
                subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return True
            except FileNotFoundError:
                print("ffmpeg was installed but is not accessible. Please try restarting your terminal.")
                return False
                
        except Exception as e:
            print(f"Failed to install ffmpeg: {str(e)}")
            print("Please install ffmpeg manually using one of the following methods:")
            print("1. Using Homebrew (macOS): brew install --build-from-source ffmpeg")
            print("2. Using apt (Linux): sudo apt-get install -y ffmpeg")
            print("3. Using Conda: conda install -y ffmpeg -c conda-forge")
            print("4. Download from https://ffmpeg.org/download.html")
            return False 