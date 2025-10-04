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
  "longitude": -71.418785
}
```

**Response:** MP3 audio file

### GET /audio
Alternative GET endpoint.

**Query Parameters:**
- `latitude`: float
- `longitude`: float

**Example:**
```
GET /audio?latitude=41.529146&longitude=-71.418785
```

**Response:** MP3 audio file

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

## Testing Locally

```bash
# Using curl with POST
curl -X POST http://localhost:8080/audio \
  -H "Content-Type: application/json" \
  -d '{"latitude": 41.529146, "longitude": -71.418785}' \
  --output test.mp3

# Using curl with GET
curl "http://localhost:8080/audio?latitude=41.529146&longitude=-71.418785" \
  --output test.mp3
```

## Deployment to Fly.io

1. Install the Fly CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

2. Login to Fly.io:
```bash
flyctl auth login
```

3. Launch the app (first time):
```bash
flyctl launch
```
This will detect the Dockerfile and create the app.

4. Set your environment variables as secrets:
```bash
flyctl secrets set GENAI_API_KEY=your_google_genai_api_key
flyctl secrets set MAPS_API_KEY=your_google_maps_api_key
flyctl secrets set ELEVEN_API_KEY=your_elevenlabs_api_key
```

5. Deploy:
```bash
flyctl deploy
```

6. Check the status:
```bash
flyctl status
```

## Environment Variables

- `GENAI_API_KEY`: Google Generative AI API key
- `MAPS_API_KEY`: Google Maps API key
- `ELEVEN_API_KEY`: ElevenLabs API key
- `PORT`: Server port (default: 8080)

## Caching

The application caches both text descriptions and generated audio files to reduce API costs and improve response times. Cache is organized by coordinates rounded to ~100m precision.

- Text cache: `cache/text/`
- Audio cache: `cache/audio/`

## Architecture

- **Flask**: Web framework
- **Google Gemini AI**: Generates contextual historical descriptions
- **ElevenLabs**: Converts text to natural-sounding speech
- **Google Maps API**: Fetches nearby points of interest
- **Gunicorn**: Production WSGI server

## License

MIT
