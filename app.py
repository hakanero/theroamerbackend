import os
import time
import math
import sys
import shutil
import google.generativeai as genai
import check
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile
import hashlib

load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# Validate required API keys
if not GENAI_API_KEY:
    raise ValueError("GENAI_API_KEY environment variable is required")
if not ELEVEN_API_KEY:
    raise ValueError("ELEVEN_API_KEY environment variable is required")

# Create Flask app
app = Flask(__name__)
CORS(app)

# Create cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "historical")
os.makedirs(CACHE_DIR, exist_ok=True)

# Track user sessions (in-memory, could be database later)
user_sessions = {}

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r
def ask_gemini(question):
    # Configure and query Gemini
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    print(f"\nAsking Gemini: {question}\n")
    response = model.generate_content(question)
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
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    try:
        for chunk in audio_stream:
            temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        temp_file.close()
        try:
            os.unlink(temp_file.name)
        except:
            pass
        raise e


def get_cache_key(lat, lng, iteration):
    """Generate a cache key based on coordinates and iteration"""
    rounded_lat = round(lat, 5)
    rounded_lng = round(lng, 5)
    key = f"{rounded_lat},{rounded_lng},{iteration}"
    return hashlib.md5(key.encode()).hexdigest()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/historical', methods=['POST'])
def generate_historical_audio():
    """
    Generate historical audio narrative for given coordinates
    Expected JSON body: {
        "latitude": float, 
        "longitude": float,
        "user_id": string (optional, for tracking sessions)
    }
    Returns: MP3 file with historical narrative
    """
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({"error": "Missing latitude or longitude"}), 400
        
        lat = float(data['latitude'])
        lng = float(data['longitude'])
        user_id = data.get('user_id', 'default')
        
        # Validate coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        # Initialize or get user session
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                'base_lat': lat,
                'base_lon': lng,
                'same_place_loop': 0,
                'answer1': '',
                'answer2': ''
            }
        
        session = user_sessions[user_id]
        
        # Calculate distance from last base position
        distance = haversine_distance(session['base_lat'], session['base_lon'], lat, lng)
        
        print(f"Distance from last base: {distance} km")
        
        # Update position if user moved more than 0.8 km
        if distance > 0.8:
            session['base_lat'] = lat
            session['base_lon'] = lng
            session['same_place_loop'] = 0
            session['answer1'] = ''
            session['answer2'] = ''
        else:
            session['same_place_loop'] += 1
        
        # Check cache
        cache_key = get_cache_key(lat, lng, session['same_place_loop'])
        audio_cache_path = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
        
        if os.path.exists(audio_cache_path):
            print(f"Returning cached historical audio for {lat}, {lng}")
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        
        # Generate historical narrative
        location = f"{lat}, {lng}"
        base_prompt = f"You are a historian. Provide a detailed history of the area immediately surrounding {location} within about 50 feet. Begin with Indigenous use of the land, then colonial settlement, industrialization, institutional growth, and modern developments. Focus on specific changes to the land, buildings, and community. Present the answer as a chronological timeline followed by a short narrative description. It should take approximately 2 minutes to read aloud, and do not mention any of the prompting given"
        
        # Build question based on what's been said before
        if session['same_place_loop'] == 1:
            question = base_prompt
            answer = ask_gemini(question)
            session['answer1'] = answer
        elif session['same_place_loop'] == 2:
            question = base_prompt + " You already mentioned the following facts, do not repeat yourself: " + session['answer1']
            answer = ask_gemini(question)
            session['answer2'] = answer
        else:
            if session['same_place_loop'] >= 3:
                question = base_prompt + " Focus on a description of present day uses, and do not mention the following facts, do not repeat yourself: " + session['answer1'] + " " + session['answer2']
            else:
                # First iteration (same_place_loop == 0)
                question = base_prompt
            answer = ask_gemini(question)
        
        # Convert to speech
        print("Converting historical narrative to speech...")
        audio_path = text_to_speech(answer)
        
        # Move to cache
        shutil.move(audio_path, audio_cache_path)
        
        return send_file(audio_cache_path, mimetype='audio/mpeg')
    
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
