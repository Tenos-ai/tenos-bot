# --- START OF FILE check_libraries.py ---

import sys
import subprocess
import importlib.util
import platform
import os

required_libraries = [
    'discord',
    'GitPython',
    'Pillow',
    'requests',
    'aiohttp', # <-- ADDED for the bot's internal API server
    'psutil',
    'python-dotenv',
    'pandas',
    'ttkthemes'
]

if platform.system() == 'Windows':
    required_libraries.append('pywin32')

built_in_modules = [
    'tkinter',
    'asyncio',
]

def is_library_installed(library):
    try:
        importlib.import_module(library.replace('-', '_'))
        return True
    except ImportError:
        return False

def install(package):
    try:
        print(f"Attempting to install {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", package])
        print(f"Successfully installed {package}.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}. Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during installation of {package}: {e}")
        return False

def main():
    missing = []
    for lib in required_libraries:
        import_name = lib
        if lib == 'GitPython': import_name = 'git'
        elif lib == 'Pillow': import_name = 'PIL'
        elif lib == 'pywin32': import_name = 'win32api'
        elif '-' in lib: import_name = lib.split('-')[0]
        elif lib == 'discord':
             try:
                 importlib.import_module('discord')
                 if not is_library_installed('discord'):
                      missing.append(lib)
             except ImportError:
                 missing.append(lib)
             continue

        if not is_library_installed(import_name):
            missing.append(lib)

    for module in built_in_modules:
        if not is_library_installed(module):
            print(f"Warning: Built-in module {module} not found. This might indicate an issue with your Python installation.")

    if missing:
        print("-" * 30)
        print(f"Missing required libraries: {', '.join(missing)}")
        print("Attempting to install missing libraries...")
        print("-" * 30)

        failed = []
        for lib in missing:
            print(f"\n--- Installing {lib} ---")
            if not install(lib):
                failed.append(lib)
                print(f"--- Failed to install {lib} ---")
            else:
                 print(f"--- Finished installing {lib} ---")

        print("-" * 30)
        if failed:
            print(f"The following libraries failed to install automatically: {', '.join(failed)}")
            print("Please try installing them manually using:")
            for fail in failed:
                 python_exe_name = os.path.basename(sys.executable)
                 print(f"  `{python_exe_name} -m pip install {fail}`")
            print("Then run this script again.")
            print("-" * 30)
        else:
            print("All required libraries seem to be installed now.")
            print("-" * 30)
    else:
        print("All required libraries are already installed.")

if __name__ == "__main__":
    main()