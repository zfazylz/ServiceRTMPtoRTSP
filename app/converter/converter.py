"""
RTMP to RTSP Stream Converter

This module provides functionality to convert RTMP streams to RTSP streams using FFmpeg.
"""

import subprocess
import time
import logging
import os
import signal
import io
import threading
from typing import Optional, List, Dict, TextIO

from app.db import save_stream, delete_stream, get_all_streams as db_get_all_streams, get_stream as db_get_stream

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LoggerWriter(io.TextIOBase):
    """
    A file-like object that writes to a logger.

    This class is used to redirect subprocess output directly to a logger.
    """

    def __init__(self, logger, prefix=""):
        """
        Initialize the LoggerWriter.

        Args:
            logger: The logger to write to
            prefix (str): A prefix to add to each log message
        """
        self.logger = logger
        self.prefix = prefix
        self.buffer = ""

    def write(self, data):
        """
        Write data to the logger.

        Args:
            data: The data to write

        Returns:
            int: The number of characters written
        """
        if data:
            # Buffer the data until we get a newline
            self.buffer += data
            if '\n' in self.buffer:
                lines = self.buffer.splitlines()
                # Keep the last line if it doesn't end with a newline
                if self.buffer.endswith('\n'):
                    self.buffer = ""
                    for line in lines:
                        if line:  # Skip empty lines
                            self.logger.info(f"{self.prefix}{line}")
                else:
                    self.buffer = lines[-1]
                    for line in lines[:-1]:
                        if line:  # Skip empty lines
                            self.logger.info(f"{self.prefix}{line}")
            return len(data)
        return 0

    def flush(self):
        """Flush the buffer."""
        if self.buffer:
            self.logger.info(f"{self.prefix}{self.buffer}")
            self.buffer = ""

class StreamConverter:
    """
    Converts RTMP streams to RTSP streams using FFmpeg.

    Attributes:
        rtmp_url (str): The source RTMP URL
        rtsp_port (int): The port to use for the RTSP server
        stream_name (str): A unique name for the stream
        rtsp_url (str): The URL of the resulting RTSP stream
        process (subprocess.Popen): The FFmpeg process
        log_buffer (io.StringIO): Buffer to store logs for this stream
        last_error (str): The last error message from FFmpeg, if any
        last_output_time (float): The timestamp of the last output from FFmpeg
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
        self.log_buffer = io.StringIO()
        self.log_thread = None
        self.stop_log_thread = False
        self.last_error = ""
        self.last_output_time = 0.0

        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'app', 'static', 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # Set up log file path
        self.log_file_path = os.path.join(logs_dir, f"{stream_name}.log")

        # Create a stream-specific logger
        self.logger = logging.getLogger(f"{__name__}.{stream_name}")

        # Add a handler to write to the buffer
        buffer_handler = logging.StreamHandler(self.log_buffer)
        buffer_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(buffer_handler)

        # Add a handler to write to a file in append mode
        file_handler = logging.FileHandler(self.log_file_path, mode='a')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)


    def _log_ffmpeg_output(self):
        """
        Read and log the output from the ffmpeg process.
        This method is intended to be run in a separate thread.
        """
        while not self.stop_log_thread and self.process and self.process.poll() is None:
            try:
                # Read from stdout
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        self.logger.info(f"FFmpeg stdout: {line.strip()}")
                        # Update last output time
                        self.last_output_time = time.time()

                # Read from stderr
                if self.process.stderr:
                    line = self.process.stderr.readline()
                    if line:
                        self.logger.info(f"FFmpeg stderr: {line.strip()}")
                        # Check for error messages
                        error_line = line.strip().lower()
                        if "error" in error_line or "fatal" in error_line:
                            self.last_error = line.strip()
                        # Update last output time even for errors
                        self.last_output_time = time.time()

                # Small sleep to avoid high CPU usage
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error reading ffmpeg output: {str(e)}")
                self.last_error = str(e)
                break


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
            self.logger.warning(f"Converter for {self.stream_name} is already running")
            return True

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Starting converter for {self.rtmp_url} (attempt {attempt+1}/{max_retries})")

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
                    f"rtsp://rtsp-server:{self.rtsp_port}/{self.stream_name}",
                    # "-stats",
                    # "-stats_period 5",
                    # "-loglevel info",
                ]

                # Start the FFmpeg process with pipes for stdout and stderr
                with open(self.log_file_path, "a") as log_file:
                    self.process = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=log_file,
                        universal_newlines=True,
                        env={"AV_LOG_FORCE_COLOR": "1"},
                    )

                # Start a thread to read from the pipes and log the output
                self.stop_log_thread = False
                self.log_thread = threading.Thread(target=self._log_ffmpeg_output)
                self.log_thread.daemon = True
                self.log_thread.start()

                # Wait a bit to see if the process starts successfully
                time.sleep(2)

                # Check if the process is still running
                if self.process.poll() is None:
                    self.logger.info(f"Converter started successfully for {self.stream_name}")

                    return True
                else:
                    self.logger.error(f"Converter failed to start")

                    # Wait before retrying
                    if attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
            except Exception as e:
                self.logger.error(f"Error starting converter: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        self.logger.error(f"Failed to start converter after {max_retries} attempts")
        return False

    def get_health_status(self) -> dict:
        """
        Check the health status of the stream.

        Returns:
            dict: A dictionary containing status information:
                - status: True if the stream is healthy, False if not
                - reason: A string explaining the status (only for False status)
        """
        # Check if process is running
        if not self.process or self.process.poll() is not None:
            return {
                "status": False,
                "reason": "FFmpeg process is not running"
            }

        # Check for recent errors
        if self.last_error:
            return {
                "status": False,
                "reason": f"FFmpeg error: {self.last_error}"
            }

        # Check for recent output (consider stream down if no output for more than 30 seconds)
        if self.last_output_time > 0 and time.time() - self.last_output_time > 30:
            return {
                "status": False,
                "reason": "No output from FFmpeg for more than 30 seconds"
            }

        # If we got here, the stream is healthy
        return {
            "status": True,
            "reason": "Stream is running normally"
        }

    def stop(self) -> bool:
        """
        Stop the RTMP to RTSP conversion.

        Returns:
            bool: True if the conversion was stopped successfully, False otherwise
        """
        if not self.process:
            self.logger.warning(f"No converter process to stop for {self.stream_name}")
            return True

        try:
            self.logger.info(f"Stopping converter for {self.stream_name}")

            # Stop the log thread if it's running
            if self.log_thread and self.log_thread.is_alive():
                self.stop_log_thread = True
                self.log_thread.join(timeout=2)  # Wait for the thread to terminate
                self.log_thread = None

            # Try to terminate gracefully first
            self.process.terminate()

            # Wait for the process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If it doesn't terminate in time, kill it
                self.logger.warning(f"Converter for {self.stream_name} did not terminate gracefully, killing it")
                self.process.kill()
                self.process.wait(timeout=2)

            self.logger.info(f"Converter for {self.stream_name} stopped successfully")
            self.process = None
            return True
        except Exception as e:
            self.logger.error(f"Error stopping converter: {str(e)}")
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

    def load_streams_from_db(self, host: str = "localhost") -> int:
        """
        Load streams from the database and start them.

        Args:
            host (str): The hostname to use in the RTSP URL (default: "localhost")

        Returns:
            int: The number of streams successfully loaded and started
        """
        streams = db_get_all_streams()
        count = 0

        for stream in streams:
            stream_name = stream['stream_name']
            rtmp_url = stream['rtmp_url']
            rtsp_port = stream['rtsp_port']

            # Skip if stream already exists
            if stream_name in self.streams:
                logger.warning(f"Stream '{stream_name}' already exists, skipping")
                continue

            # Create and start the converter
            converter = StreamConverter(rtmp_url, rtsp_port, stream_name, host)
            if converter.start():
                self.streams[stream_name] = converter
                logger.info(f"Stream '{stream_name}' loaded and started successfully")
                count += 1
            else:
                logger.error(f"Failed to start stream '{stream_name}' from database")

        return count

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
            # Save to database
            save_stream(stream_name, rtmp_url, rtsp_port)
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
            # Delete from database
            delete_stream(stream_name)
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
                "rtsp_port": converter.rtsp_port,
                "logs_url": f"/logs/{name}",
                "logs_file_url": f"/static/logs/{name}.log",
                "status": converter.get_health_status()["status"],
                "status_reason": converter.get_health_status()["reason"]
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
        health_status = converter.get_health_status()
        return {
            "name": stream_name,
            "rtmp_url": converter.rtmp_url,
            "rtsp_url": f"rtsp://{host}:{converter.rtsp_port}/{converter.stream_name}",
            "rtsp_port": converter.rtsp_port,
            "logs_url": f"/logs/{stream_name}",
            "logs_file_url": f"/static/logs/{stream_name}.log",
            "status": health_status["status"],
            "status_reason": health_status["reason"]
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

    def get_stream_logs(self, stream_name: str) -> Optional[str]:
        """
        Get logs for a specific stream.

        Args:
            stream_name (str): The name of the stream

        Returns:
            Optional[str]: The logs for the stream, or None if the stream is not found
        """
        if stream_name not in self.streams:
            return None

        converter = self.streams[stream_name]

        # Get logs from the buffer
        buffer_logs = converter.log_buffer.getvalue()

        # Get logs from the file if it exists
        file_logs = ""
        if hasattr(converter, 'log_file_path') and os.path.exists(converter.log_file_path):
            try:
                with open(converter.log_file_path, 'r') as f:
                    file_logs = f.read()
            except Exception as e:
                logger.error(f"Error reading log file for stream '{stream_name}': {str(e)}")

        # If both sources have logs, return the file logs (which should be more complete)
        # Otherwise, return whichever has logs, or an empty string if neither has logs
        if file_logs:
            return file_logs
        return buffer_logs
