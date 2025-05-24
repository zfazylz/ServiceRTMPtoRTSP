"""
Stream manager module.

This module provides functionality to manage multiple stream converters.
"""

import logging
from typing import Dict, List, Optional, Union

from app.converter.stream_converter import StreamConverter
from app.db import save_stream, delete_stream, get_all_streams as db_get_all_streams

# Configure logging
logger = logging.getLogger(__name__)


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

    def get_all_streams(self, host: str = "localhost") -> List[Dict[str, Union[str, int, bool]]]:
        """
        Get information about all active streams.

        Args:
            host (str): The hostname to use in the RTSP URL (default: "localhost")

        Returns:
            List[Dict[str, Union[str, int, bool]]]: List of dictionaries containing stream information
                with keys for name, rtmp_url, rtsp_url, rtsp_port, logs_url, logs_file_url,
                status, and status_reason
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
                "status_reason": converter.get_health_status()["reason"],
            }
            for name, converter in self.streams.items()
        ]

    def get_stream(self, stream_name: str, host: str = "localhost") -> Optional[Dict[str, Union[str, int, bool]]]:
        """
        Get information about a specific stream.

        Args:
            stream_name (str): The name of the stream
            host (str): The hostname to use in the RTSP URL (default: "localhost")

        Returns:
            Optional[Dict[str, Union[str, int, bool]]]: Dictionary containing stream information
                with keys for name, rtmp_url, rtsp_url, rtsp_port, logs_url, logs_file_url,
                status, and status_reason, or None if the stream is not found
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
            "status_reason": health_status["reason"],
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

    def clear_stream_error(self, stream_name: str) -> bool:
        """
        Clear the error state for a specific stream.

        Args:
            stream_name (str): The name of the stream

        Returns:
            bool: True if the error was cleared, False if the stream was not found
        """
        if stream_name not in self.streams:
            logger.warning(f"Stream with name '{stream_name}' does not exist")
            return False

        converter = self.streams[stream_name]
        converter.clear_error()
        logger.info(f"Cleared error state for stream '{stream_name}'")
        return True

    def clear_all_errors(self) -> None:
        """
        Clear the error state for all streams.
        """
        for name, converter in self.streams.items():
            converter.clear_error()
            logger.info(f"Cleared error state for stream '{name}'")

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
        logs = converter.log_buffer.getvalue()

        # If the buffer is empty, try to read from the log file
        if not logs:
            try:
                with open(converter.log_file_path, 'r') as f:
                    logs = f.read()
            except Exception as e:
                logger.error(f"Error reading log file for stream '{stream_name}': {str(e)}")
                return f"Error reading logs: {str(e)}"

        return logs
