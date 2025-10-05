from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import tempfile
import hashlib
import shutil
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import google.generativeai as genai
import requests
from math import radians, cos, sin, sqrt, atan2

load_dotenv()

app = Flask(__name__)

# Simple, permissive CORS - allow all origins
CORS(app)

# Configuration
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
MAPS_API_KEY = os.getenv("MAPS_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# Validate required API keys
if not GENAI_API_KEY:
    raise ValueError("GENAI_API_KEY environment variable is required")
if not MAPS_API_KEY:
    raise ValueError("MAPS_API_KEY environment variable is required")
if not ELEVEN_API_KEY:
    raise ValueError("ELEVEN_API_KEY environment variable is required")

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


def get_nearby_places(lat, lng, radius=20, max_radius=100):
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
                # Filter to only include places within 50 meters for hyperspecific results
                filtered_results = []
                for p in results:
                    dist = distance(
                        lat, lng,
                        p["geometry"]["location"]["lat"],
                        p["geometry"]["location"]["lng"]
                    )
                    if dist <= 50:  # Only include places within 50 meters
                        filtered_results.append((p, dist))
                
                if filtered_results:
                    # Sort by distance from exact (lat, lng)
                    filtered_results.sort(key=lambda x: x[1])
                    return [p[0] for p in filtered_results[:3]]  # pick top 3 closest
        except Exception as e:
            print(f"Error fetching nearby places: {e}")
        radius += 20  # Smaller increments for more precision
    return []


def describe_places(lat, lng, place_name=None):
    """Generate description of places at given coordinates"""
    places = get_nearby_places(lat, lng)
    
    # Add place_name context if provided
    location_context = f"at {place_name}" if place_name else f"at coordinates ({lat}, {lng})"
    
    if not places:
        prompt = f"""
        You are an information assistant. There are no significant pins or landmarks 
        returned for a person standing {location_context}. 

        Give a short, factual description of what is IMMEDIATELY around this exact location 
        within 20-30 meters ONLY. 

        - Do NOT describe weather, trees, skies, or generic scenery.  
        - Do NOT mention large landmarks or areas unless the person is standing directly at them.
        - Only describe what is in the IMMEDIATE vicinity: specific buildings, entrances, 
        pathways, statues, plaques, or architectural features RIGHT where they're standing.
        - If possible, describe them in terms of direction from the person: 
        "Directly in front of you is...", "To your immediate left is...", etc.  
        - Be HYPERSPECIFIC about the exact spot, not the general area.
        - Keep the language short, factual, and precise (2-3 sentences max).  
        - Include one brief historical note if relevant.  
        - Avoid storytelling, no "imagine this," no "alright everyone," no fluff.  
        """
    else:
        place_info = [f"{p.get('name')} ({', '.join(p.get('types', []))})" for p in places]
        prompt = f"""
        You are an information assistant. A person is standing {location_context}.  
        Here are the closest nearby places (all within 50 meters):

        {chr(10).join(place_info)}

        Your task:
        - Describe ONLY what is in the IMMEDIATE vicinity (within 20-30 meters).
        - Be HYPERSPECIFIC about this exact location, not the general area.
        - Do NOT mention large landmarks or campuses unless the person is standing directly at them.
        - Focus on specific buildings, entrances, architectural features, monuments, or notable 
        structures at THIS EXACT SPOT.
        - Phrase directions precisely: "Directly in front of you is...", 
        "To your immediate left/right is...", "You are standing at..."  
        - Keep it short and precise (2-4 sentences max).  
        - Include brief history or significance where available, but only in 1 sentence.  
        - Avoid fluff, emotions, or storytelling. This is factual guidance only.
        - DO NOT describe generic shops, hotels, gyms, or residential apartments unless 
        they are historically/culturally important to THIS EXACT SPOT.
        """

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
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    try:
        for chunk in audio_stream:
            temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        temp_file.close()
        # Clean up temp file on error
        try:
            os.unlink(temp_file.name)
        except:
            pass
        raise e


def get_cache_key(lat, lng):
    """Generate a cache key based on coordinates (rounded to ~10m precision)"""
    # Round to 4 decimal places (~11m precision) to avoid caching too broadly
    # but still catch very nearby requests
    rounded_lat = round(lat, 4)
    rounded_lng = round(lng, 4)
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
    Expected JSON body: {"latitude": float, "longitude": float, "place_name": string (optional)}
    Returns: MP3 file
    """
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({"error": "Missing latitude or longitude"}), 400
        
        lat = float(data['latitude'])
        lng = float(data['longitude'])
        place_name = data.get('place_name')  # Optional place name from frontend
        
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
        location_display = f"{place_name} ({lat}, {lng})" if place_name else f"{lat}, {lng}"
        print(f"Generating description for {location_display}")
        description = describe_places(lat, lng, place_name)
        
        # Save text to cache
        with open(text_cache_path, 'w') as f:
            f.write(description)
        
        # Convert to speech
        print("Converting to speech...")
        audio_path = None
        try:
            audio_path = text_to_speech(description)
            
            # Move to cache (use shutil.move for cross-filesystem compatibility)
            shutil.move(audio_path, audio_cache_path)
            audio_path = None  # Successfully moved, no cleanup needed
            
            # Verify file exists before sending
            if not os.path.exists(audio_cache_path):
                raise FileNotFoundError(f"Audio file not found at {audio_cache_path}")
            
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        finally:
            # Clean up temp file if it still exists (error occurred before move)
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to cleanup temp file {audio_path}: {cleanup_error}")
    
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
        audio_path = None
        try:
            audio_path = text_to_speech(description)
            
            # Move to cache (use shutil.move for cross-filesystem compatibility)
            shutil.move(audio_path, audio_cache_path)
            audio_path = None  # Successfully moved, no cleanup needed
            
            # Verify file exists before sending
            if not os.path.exists(audio_cache_path):
                raise FileNotFoundError(f"Audio file not found at {audio_cache_path}")
            
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        finally:
            # Clean up temp file if it still exists (error occurred before move)
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to cleanup temp file {audio_path}: {cleanup_error}")
    
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
