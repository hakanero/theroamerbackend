from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import hashlib
import shutil
from dotenv import load_dotenv
import check  # Import the check module with all the core logic

load_dotenv()

app = Flask(__name__)

# Simple, permissive CORS - allow all origins
CORS(app)

# Create cache directories
AUDIO_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "audio")
TEXT_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "text")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEXT_CACHE_DIR, exist_ok=True)


def get_cache_key(lat, lng, place_name=None):
    """Generate a cache key based on coordinates and place name"""
    # Round to 4 decimal places (~11m precision) to avoid caching too broadly
    # but still catch very nearby requests
    rounded_lat = round(lat, 4)
    rounded_lng = round(lng, 4)
    # Include place_name in cache key if provided
    if place_name:
        key = f"{rounded_lat},{rounded_lng},{place_name}"
    else:
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
        
        # Check cache (include place_name in cache key)
        cache_key = get_cache_key(lat, lng, place_name)
        audio_cache_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")
        
        # If cached audio exists, return it
        if os.path.exists(audio_cache_path):
            location_display = f"{place_name} ({lat}, {lng})" if place_name else f"{lat}, {lng}"
            print(f"Returning cached audio for {location_display}")
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        
        # Generate audio using check.py
        location_display = f"{place_name} ({lat}, {lng})" if place_name else f"{lat}, {lng}"
        print(f"Generating description for {location_display}")
        
        # Call the main function from check.py
        temp_audio_path = check.generate_audio_for_location(lat, lng, place_name)
        
        try:
            # Move to cache (use shutil.move for cross-filesystem compatibility)
            shutil.move(temp_audio_path, audio_cache_path)
            
            # Verify file exists before sending
            if not os.path.exists(audio_cache_path):
                raise FileNotFoundError(f"Audio file not found at {audio_cache_path}")
            
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        finally:
            # Clean up temp file if it still exists (error occurred before move)
            if os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to cleanup temp file {temp_audio_path}: {cleanup_error}")
    
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/audio', methods=['GET'])
def generate_audio_get():
    """
    Generate audio description for given coordinates (GET version)
    Query parameters: ?latitude=float&longitude=float&place_name=string (optional)
    Returns: MP3 file
    """
    try:
        lat = request.args.get('latitude')
        lng = request.args.get('longitude')
        place_name = request.args.get('place_name')  # Optional
        
        if not lat or not lng:
            return jsonify({"error": "Missing latitude or longitude"}), 400
        
        lat = float(lat)
        lng = float(lng)
        
        # Validate coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        # Check cache (include place_name in cache key)
        cache_key = get_cache_key(lat, lng, place_name)
        audio_cache_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")
        
        # If cached audio exists, return it
        if os.path.exists(audio_cache_path):
            location_display = f"{place_name} ({lat}, {lng})" if place_name else f"{lat}, {lng}"
            print(f"Returning cached audio for {location_display}")
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        
        # Generate audio using check.py
        location_display = f"{place_name} ({lat}, {lng})" if place_name else f"{lat}, {lng}"
        print(f"Generating description for {location_display}")
        
        # Call the main function from check.py
        temp_audio_path = check.generate_audio_for_location(lat, lng, place_name)
        
        try:
            # Move to cache (use shutil.move for cross-filesystem compatibility)
            shutil.move(temp_audio_path, audio_cache_path)
            
            # Verify file exists before sending
            if not os.path.exists(audio_cache_path):
                raise FileNotFoundError(f"Audio file not found at {audio_cache_path}")
            
            return send_file(audio_cache_path, mimetype='audio/mpeg')
        finally:
            # Clean up temp file if it still exists (error occurred before move)
            if os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to cleanup temp file {temp_audio_path}: {cleanup_error}")
    
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
