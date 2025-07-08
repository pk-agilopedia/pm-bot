import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the app instance directly from app.py
from app import app

if __name__ == "__main__":
    app.run()