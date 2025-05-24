"""
Application configuration and setup.
"""

import logging
import os

# Create necessary directories
static_dir = os.path.join(os.getcwd(), 'app/static')
logs_dir = os.path.join(static_dir, 'logs')

if not os.path.exists(static_dir):
    os.makedirs(static_dir)

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
