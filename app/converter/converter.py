"""
RTMP to RTSP Stream Converter

This module provides functionality to convert RTMP streams to RTSP streams using FFmpeg.
"""

import subprocess
import time
import logging
import os
import signal
from typing import Optional, List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StreamConverter:
    """
    Converts RTMP streams to RTSP streams using FFmpeg.

    Attributes:
        rtmp_url (str): The source RTMP URL
        rtsp_port (int): The port to use for the RTSP server
        stream_name (str): A unique name for the stream
        rtsp_url (str): The URL of the resulting RTSP stream
        process (subprocess.Popen): The FFmpeg process
    """

    def __init__(self, rtmp_url: str, rtsp_port: int, stream_name: str, host: str = "localhost"):
        """
        Initialize the StreamConverter.

        Args:
            rtmp_url (str): The source RTMP URL
            rtsp_port (int): The port to use for the RTSP server
            stream_name (str): A unique name for the stream
            host (str): The hostname to use in the RTSP URL (default: "localhost")
        """
        self.rtmp_url = rtmp_url
        self.rtsp_port = rtsp_port
        self.stream_name = stream_name
        self.host = host
        self.rtsp_url = f"rtsp://{host}:{rtsp_port}/{stream_name}"
        self.process: Optional[subprocess.Popen] = None

    def start(self, max_retries: int = 3, retry_delay: int = 2) -> bool:
        """
        Start the RTMP to RTSP conversion.

        Args:
            max_retries (int): Maximum number of retry attempts if starting fails
            retry_delay (int): Delay in seconds between retry attempts

        Returns:
            bool: True if the conversion started successfully, False otherwise
        """
        if self.process and self.process.poll() is None:
            logger.warning(f"Converter for {self.stream_name} is already running")
            return True

        for attempt in range(max_retries):
            try:
                logger.info(f"Starting converter for {self.rtmp_url} (attempt {attempt+1}/{max_retries})")

                # FFmpeg command to convert RTMP to RTSP
                cmd = [
                    "ffmpeg",
                    "-re",
                    "-i", self.rtmp_url,
                    "-c",
                    "copy",
                    "-f",
                    "rtsp",
                    "-rtsp_transport", "tcp",
                    f"rtsp://rtsp-server:{self.rtsp_port}/{self.stream_name}"
                ]

                # cmd = [
                #     "ffmpeg",
                #     "-i", self.rtmp_url,
                #     "-c:v", "copy",  # Copy video codec
                #     "-c:a", "copy",  # Copy audio codec
                #     "-f", "rtsp",
                #     "-rtsp_transport", "tcp",
                #     f"rtsp://0.0.0.0:{self.rtsp_port}/{self.stream_name}"
                # ]

                # Start the FFmpeg process
                self.process = subprocess.Popen(
                    cmd,
                    stdout=None,
                    stderr=None,
                    universal_newlines=True
                )

                # Wait a bit to see if the process starts successfully
                time.sleep(2)

                # Check if the process is still running
                if self.process.poll() is None:
                    logger.info(f"Converter started successfully for {self.stream_name}")
                    return True
                else:
                    stderr = self.process.stderr.read() if self.process.stderr else "No error output"
                    logger.error(f"Converter failed to start: {stderr}")

                    # Wait before retrying
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error starting converter: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        logger.error(f"Failed to start converter after {max_retries} attempts")
        return False

    def stop(self) -> bool:
        """
        Stop the RTMP to RTSP conversion.

        Returns:
            bool: True if the conversion was stopped successfully, False otherwise
        """
        if not self.process:
            logger.warning(f"No converter process to stop for {self.stream_name}")
            return True

        try:
            logger.info(f"Stopping converter for {self.stream_name}")

            # Try to terminate gracefully first
            self.process.terminate()

            # Wait for the process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If it doesn't terminate in time, kill it
                logger.warning(f"Converter for {self.stream_name} did not terminate gracefully, killing it")
                self.process.kill()
                self.process.wait(timeout=2)

            logger.info(f"Converter for {self.stream_name} stopped successfully")
            self.process = None
            return True
        except Exception as e:
            logger.error(f"Error stopping converter: {str(e)}")
            return False

class StreamManager:
    """
    Manages multiple stream converters.

    Attributes:
        streams (Dict[str, StreamConverter]): Dictionary of active stream converters
    """

    def __init__(self):
        """Initialize the StreamManager."""
        self.streams: Dict[str, StreamConverter] = {}

    def add_stream(self, rtmp_url: str, rtsp_port: int, stream_name: str, host: str = "localhost") -> bool:
        """
        Add and start a new stream converter.

        Args:
            rtmp_url (str): The source RTMP URL
            rtsp_port (int): The port to use for the RTSP server
            stream_name (str): A unique name for the stream
            host (str): The hostname to use in the RTSP URL (default: "localhost")

        Returns:
            bool: True if the stream was added and started successfully, False otherwise
        """
        if stream_name in self.streams:
            logger.warning(f"Stream with name '{stream_name}' already exists")
            return False

        # Create a new converter
        converter = StreamConverter(rtmp_url, rtsp_port, stream_name, host)

        # Try to start the converter
        if converter.start():
            self.streams[stream_name] = converter
            logger.info(f"Stream '{stream_name}' added successfully")
            return True
        else:
            logger.error(f"Failed to add stream '{stream_name}'")
            return False

    def remove_stream(self, stream_name: str) -> bool:
        """
        Remove and stop a stream converter.

        Args:
            stream_name (str): The name of the stream to remove

        Returns:
            bool: True if the stream was removed successfully, False otherwise
        """
        if stream_name not in self.streams:
            logger.warning(f"Stream with name '{stream_name}' does not exist")
            return False

        # Get the converter
        converter = self.streams[stream_name]

        # Stop the converter
        if converter.stop():
            # Remove from the dictionary
            del self.streams[stream_name]
            logger.info(f"Stream '{stream_name}' removed successfully")
            return True
        else:
            logger.error(f"Failed to remove stream '{stream_name}'")
            return False

    def get_all_streams(self, host: str = "localhost") -> List[Dict]:
        """
        Get information about all active streams.

        Args:
            host (str): The hostname to use in the RTSP URL (default: "localhost")

        Returns:
            List[Dict]: List of dictionaries containing stream information
        """
        return [
            {
                "name": name,
                "rtmp_url": converter.rtmp_url,
                "rtsp_url": f"rtsp://{host}:{converter.rtsp_port}/{converter.stream_name}",
                "rtsp_port": converter.rtsp_port
            }
            for name, converter in self.streams.items()
        ]

    def get_stream(self, stream_name: str, host: str = "localhost") -> Optional[Dict]:
        """
        Get information about a specific stream.

        Args:
            stream_name (str): The name of the stream
            host (str): The hostname to use in the RTSP URL (default: "localhost")

        Returns:
            Optional[Dict]: Dictionary containing stream information, or None if not found
        """
        if stream_name not in self.streams:
            return None

        converter = self.streams[stream_name]
        return {
            "name": stream_name,
            "rtmp_url": converter.rtmp_url,
            "rtsp_url": f"rtsp://{host}:{converter.rtsp_port}/{converter.stream_name}",
            "rtsp_port": converter.rtsp_port
        }

    def stop_all_streams(self) -> bool:
        """
        Stop all active stream converters.

        Returns:
            bool: True if all streams were stopped successfully, False otherwise
        """
        success = True
        for name, converter in list(self.streams.items()):
            if not converter.stop():
                logger.error(f"Failed to stop stream '{name}'")
                success = False

        self.streams.clear()
        return success
