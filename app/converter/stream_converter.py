"""
Stream converter module.

This module provides functionality to convert RTMP streams to RTSP streams using FFmpeg.
"""

import io
import logging
import os
import subprocess
import threading
import time
from typing import Optional, Dict, Union

# Configure logging
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

        # Health check cache
        self._last_health_check_time = 0.0
        self._cached_health_status = None

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

    def _log_ffmpeg_output(self) -> None:
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
                self.logger.info(f"Starting converter for {self.rtmp_url} (attempt {attempt + 1}/{max_retries})")

                # FFmpeg command to convert RTMP to RTSP
                cmd = [
                    "ffmpeg",
                    "-re",  # Read input at native frame rate
                    "-i", self.rtmp_url,  # Input RTMP URL
                    "-c", "copy",  # Copy codec (no re-encoding)
                    "-bufsize", "5000k",  # Buffer size for smoother streaming
                    "-f", "rtsp",  # Output format RTSP
                    "-rtsp_transport", "tcp",  # Use TCP for RTSP transport
                    "-timeout", "60",  # Connection timeout in seconds
                    f"rtsp://rtsp-server:{self.rtsp_port}/{self.stream_name}",
                ]

                # Start the FFmpeg process with pipes for stdout and stderr
                try:
                    with open(self.log_file_path, "a") as log_file:
                        self.process = subprocess.Popen(
                            cmd,
                            stdout=log_file,
                            stderr=log_file,
                            universal_newlines=True,
                            env={"AV_LOG_FORCE_COLOR": "1"},
                        )
                except FileNotFoundError:
                    self.logger.error("FFmpeg executable not found. Please ensure FFmpeg is installed.")
                    return False
                except PermissionError:
                    self.logger.error(f"Permission denied when writing to log file: {self.log_file_path}")
                    return False

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
                    exit_code = self.process.returncode
                    self.logger.error(f"Converter failed to start (exit code: {exit_code})")

                    # Wait before retrying
                    if attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
            except FileNotFoundError as e:
                self.logger.error(f"FFmpeg executable not found: {str(e)}")
                return False
            except PermissionError as e:
                self.logger.error(f"Permission error: {str(e)}")
                return False
            except OSError as e:
                self.logger.error(f"OS error starting converter: {str(e)}")
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

    def get_health_status(self) -> Dict[str, Union[bool, str]]:
        """
        Check the health status of the stream.

        Returns:
            Dict[str, Union[bool, str]]: A dictionary containing status information:
                - status: True if the stream is healthy, False if not
                - reason: A string explaining the status
        """
        # Cache health status for 5 seconds to reduce CPU usage
        current_time = time.time()
        if current_time - self._last_health_check_time < 5 and self._cached_health_status is not None:
            return self._cached_health_status

        # Check if process is running
        if not self.process or self.process.poll() is not None:
            status = {
                "status": False,
                "reason": "FFmpeg process is not running",
            }
            self._cached_health_status = status
            self._last_health_check_time = current_time
            return status

        # Check for recent errors
        if self.last_error:
            status = {
                "status": False,
                "reason": f"FFmpeg error: {self.last_error}",
            }
            self._cached_health_status = status
            self._last_health_check_time = current_time
            return status

        # Check for recent output (consider stream down if no output for more than 30 seconds)
        if self.last_output_time > 0 and current_time - self.last_output_time > 30:
            status = {
                "status": False,
                "reason": "No output from FFmpeg for more than 30 seconds",
            }
            self._cached_health_status = status
            self._last_health_check_time = current_time
            return status

        # If we got here, the stream is healthy
        status = {
            "status": True,
            "reason": "Stream is running normally",
        }
        self._cached_health_status = status
        self._last_health_check_time = current_time
        return status

    def clear_error(self) -> None:
        """
        Clear the last error message.

        This is useful for resetting the error state after it has been handled.
        """
        self.last_error = ""
        # Reset cached health status
        self._cached_health_status = None

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
