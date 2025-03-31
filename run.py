"""
This script runs the Inbox Genie application.
It properly handles Python import paths so that the app.py
can access the other modules in the src directory.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import and run the Flask application
from src.app import app

if __name__ == '__main__':
    app.run(debug=True)
