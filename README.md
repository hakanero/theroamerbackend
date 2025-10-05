# The Roamer Backend

A Flask-based backend API that generates historical audio descriptions based on GPS coordinates. The service uses Google's Gemini AI to generate contextual descriptions and ElevenLabs for text-to-speech conversion.

## Features

- RESTful API endpoint that accepts latitude/longitude coordinates
- Returns MP3 audio files with location-based historical descriptions
- Caching system to avoid regenerating content for the same locations
- Deployable to Fly.io

## API Endpoints

### POST /audio
Generate audio description for given coordinates.

**Request Body:**
```json
{
  "latitude": 41.529146,
  "longitude": -71.418785.
  "place_name": "Harvard Yard"
  "language": "english",
}
```

**Response:** MP3 audio file

### GET /audio
Alternative GET endpoint.

**Query Parameters:**
- `latitude`: float
- `longitude`: float
- `place_name `: string
- `language`: string

**Example:**
```
GET /audio?latitude=41.529146&longitude=-71.418785&place_name=Harvard Yard
```

**Response:** Json File containing Audio Transcript and Base64 MP3 audio file

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. Run the application:
```bash
python app.py
```

The server will start on `http://localhost:8080`


## Architecture

- **Flask**: Web framework
- **Google Gemini AI**: Generates contextual historical descriptions
- **ElevenLabs**: Converts text to natural-sounding speech
- **Google Maps API**: Fetches nearby points of interest
- **Gunicorn**: Production WSGI server

