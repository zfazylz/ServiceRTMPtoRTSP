# RTMP to RTSP Converter

A web application for converting RTMP streams to RTSP streams using FastAPI and FFmpeg.

## Features

- Convert RTMP streams to RTSP streams
- Web interface for managing streams
- Add, view, and delete streams
- RESTful API for programmatic access
- Dockerized for easy deployment

## Requirements

- Docker and Docker Compose
- FFmpeg (installed automatically in Docker)
- RTMP source streams

## Quick Start

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd rtmp-to-rtsp-converter
   ```

2. Start the application with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access the web interface at http://localhost:8000

## Usage

### Web Interface

The web interface provides three main pages:

1. **Home Page**: View all active streams with their details
2. **Add Stream Page**: Add a new RTMP stream to convert to RTSP
3. **Delete Stream**: Remove a stream from the converter

### Adding a Stream

To add a new stream:

1. Click "Add New Stream" on the home page
2. Enter the RTMP URL (must start with `rtmp://`)
3. Enter a unique name for the stream (no spaces allowed)
4. Specify the RTSP port (default: 8554)
5. Click "Add Stream"

### Accessing RTSP Streams

Once a stream is added, you can access it using any RTSP-compatible player (like VLC):

```
rtsp://localhost:PORT/STREAM_NAME
```

Where:
- `PORT` is the RTSP port you specified
- `STREAM_NAME` is the name you gave to the stream

Example:
```
rtsp://localhost:8554/my_stream
```

## API Documentation

The application provides a RESTful API for programmatic access:

### Get All Streams

```
GET /api/streams
```

### Get a Specific Stream

```
GET /api/streams/{stream_name}
```

### Add a New Stream

```
POST /api/streams
```

Request body:
```json
{
  "rtmp_url": "rtmp://example.com/live/stream",
  "stream_name": "my_stream",
  "rtsp_port": 8554
}
```

### Delete a Stream

```
DELETE /api/streams/{stream_name}
```

## Troubleshooting

### RTSP Streaming Issues

If you have issues with RTSP streaming, try using host networking mode:

1. Edit `docker-compose.yml`
2. Uncomment the `network_mode: host` line
3. Comment out the `ports` section
4. Restart the application:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### FFmpeg Errors

If you see FFmpeg errors in the logs, check:

1. The RTMP URL is correct and accessible
2. The RTMP stream is active and running
3. The RTSP port is not already in use

## Development

To run the application in development mode:

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.