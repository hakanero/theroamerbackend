from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import tempfile
import hashlib
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import google.generativeai as genai
import requests
from math import radians, cos, sin, sqrt, atan2

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
MAPS_API_KEY = os.getenv("MAPS_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Create cache directories
AUDIO_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "audio")
TEXT_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "text")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEXT_CACHE_DIR, exist_ok=True)


def distance(lat1, lng1, lat2, lng2):
    """Calculate distance in meters between two coordinates"""
    R = 6371e3  # meters
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
                # sort by distance from exact (lat, lng)
                results.sort(key=lambda p: distance(
                    lat, lng,
                    p["geometry"]["location"]["lat"],
                    p["geometry"]["location"]["lng"]
                ))
                return results[:3]  # pick top 3 closest
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
        - If possible, describe them in terms of direction from the person: 
        "On your left is...", "In front of you is...", etc.  
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

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        for chunk in audio_stream:
            f.write(chunk)
        audio_path = f.name
    
    return audio_path


def get_cache_key(lat, lng):
    """Generate a cache key based on coordinates (rounded to ~100m precision)"""
    # Round to 3 decimal places (~111m precision)
    rounded_lat = round(lat, 3)
    rounded_lng = round(lng, 3)
    key = f"{rounded_lat},{rounded_lng}"
    return hashlib.md5(key.encode()).hexdigest()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/audio', methods=['POST'])
def generate_audio():
    """
    Generate audio description for given coordinates
    Expected JSON body: {"latitude": float, "longitude": float}
    Returns: MP3 file
    """
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({"error": "Missing latitude or longitude"}), 400
        
        lat = float(data['latitude'])
        lng = float(data['longitude'])
        
        # Validate coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        # Check cache
        cache_key = get_cache_key(lat, lng)
        audio_cache_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")
        text_cache_path = os.path.join(TEXT_CACHE_DIR, f"{cache_key}.txt")
        
        # If cached audio exists, return it
        if os.path.exists(audio_cache_path):
            print(f"Returning cached audio for {lat}, {lng}")
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        
        # Generate description
        print(f"Generating description for {lat}, {lng}")
        description = describe_places(lat, lng)
        
        # Save text to cache
        with open(text_cache_path, 'w') as f:
            f.write(description)
        
        # Convert to speech
        print("Converting to speech...")
        audio_path = text_to_speech(description)
        
        # Move to cache
        os.rename(audio_path, audio_cache_path)
        
        return send_file(audio_cache_path, mimetype='audio/mpeg')
    
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/audio', methods=['GET'])
def generate_audio_get():
    """
    Generate audio description for given coordinates (GET version)
    Query parameters: ?latitude=float&longitude=float
    Returns: MP3 file
    """
    try:
        lat = request.args.get('latitude')
        lng = request.args.get('longitude')
        
        if not lat or not lng:
            return jsonify({"error": "Missing latitude or longitude"}), 400
        
        lat = float(lat)
        lng = float(lng)
        
        # Validate coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        # Check cache
        cache_key = get_cache_key(lat, lng)
        audio_cache_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")
        text_cache_path = os.path.join(TEXT_CACHE_DIR, f"{cache_key}.txt")
        
        # If cached audio exists, return it
        if os.path.exists(audio_cache_path):
            print(f"Returning cached audio for {lat}, {lng}")
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        
        # Generate description
        print(f"Generating description for {lat}, {lng}")
        description = describe_places(lat, lng)
        
        # Save text to cache
        with open(text_cache_path, 'w') as f:
            f.write(description)
        
        # Convert to speech
        print("Converting to speech...")
        audio_path = text_to_speech(description)
        
        # Move to cache
        os.rename(audio_path, audio_cache_path)
        
        return send_file(audio_cache_path, mimetype='audio/mpeg')
    
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
