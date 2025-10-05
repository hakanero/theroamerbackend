import os
import json
import tempfile
from http.server import BaseHTTPRequestHandler
from elevenlabs.client import ElevenLabs
import google.generativeai as genai
import requests
from math import radians, cos, sin, sqrt, atan2

# Configuration
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
MAPS_API_KEY = os.getenv("MAPS_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# Configure Gemini
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")


def distance(lat1, lng1, lat2, lng2):
    """Calculate distance in meters between two coordinates"""
    R = 6371e3
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def get_nearby_places(lat, lng, radius=100, max_radius=200):
    """Get nearby places from Google Maps API"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    while radius <= max_radius:
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": "point_of_interest",
            "key": MAPS_API_KEY
        }
        try:
            response = requests.get(url, params=params).json()
            results = response.get("results", [])
            if results:
                results.sort(key=lambda p: distance(
                    lat, lng,
                    p["geometry"]["location"]["lat"],
                    p["geometry"]["location"]["lng"]
                ))
                return results[:3]
        except Exception as e:
            print(f"Error fetching nearby places: {e}")
        radius += 50
    return []


def describe_places(lat, lng):
    """Generate description of places at given coordinates"""
    places = get_nearby_places(lat, lng)
    if not places:
        prompt = f"""
        You are an information assistant. There are no significant pins or landmarks 
        returned at coordinates ({lat}, {lng}). 

        Still, give a short, factual description of what is most relevant within about 
        50-100 meters. 

        - Do NOT describe weather, trees, skies, or generic scenery.  
        - Only mention meaningful structures: old buildings, museums, universities, 
        statues, memorials, or well-known restaurants.  
        - Keep the language short, factual, and precise.  
        - Talk about the place in its present form, but also add one or two important 
        historical notes if relevant.  
        - Avoid storytelling, no "imagine this," no "alright everyone," no fluff.  
        """
    else:
        place_info = [f"{p.get('name')} ({', '.join(p.get('types', []))})" for p in places]
        prompt = f"""
        You are an information assistant. A person is standing at coordinates ({lat}, {lng}).  
        Here are the closest nearby places:

        Your task:
        - Summarize only the most significant ones (e.g., historic buildings, museums, 
        universities, restaurants with cultural relevance).  
        - Do NOT describe generic shops, hotels, gyms, or residential apartments unless 
        they are historically/culturally important.  
        - Phrase directions as if the person is standing there: 
        "On your left is...", "In front of you is...", etc.  
        - Keep the description short, clear, and precise.  
        - Include a brief history or significance where available, but only in 1–2 sentences.  
        - Avoid fluff, emotions, or storytelling. This is factual guidance only.  
        """ + "\n".join(place_info)

    response = model.generate_content(prompt)
    return response.text


def text_to_speech(text):
    """Convert text to speech using ElevenLabs API"""
    client = ElevenLabs(api_key=ELEVEN_API_KEY)
    
    audio_stream = client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Collect all chunks
    audio_data = b''
    for chunk in audio_stream:
        audio_data += chunk
    
    return audio_data


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            if 'latitude' not in data or 'longitude' not in data:
                self.send_error(400, "Missing latitude or longitude")
                return
            
            lat = float(data['latitude'])
            lng = float(data['longitude'])
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                self.send_error(400, "Invalid coordinates")
                return
            
            # Generate description
            description = describe_places(lat, lng)
            
            # Convert to speech
            audio_data = text_to_speech(description)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(audio_data)))
            self.end_headers()
            self.wfile.write(audio_data)
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_error(500, str(e))
    
    def do_GET(self):
        try:
            # Parse query parameters
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            if 'latitude' not in params or 'longitude' not in params:
                self.send_error(400, "Missing latitude or longitude")
                return
            
            lat = float(params['latitude'][0])
            lng = float(params['longitude'][0])
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                self.send_error(400, "Invalid coordinates")
                return
            
            # Generate description
            description = describe_places(lat, lng)
            
            # Convert to speech
            audio_data = text_to_speech(description)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(audio_data)))
            self.end_headers()
            self.wfile.write(audio_data)
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_error(500, str(e))

