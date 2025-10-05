from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import check
import base64

load_dotenv()

app = Flask(__name__)

CORS(app)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route('/audio', methods=['POST'])
def generate_audio():
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data or 'place_name' not in data:
            return jsonify({"error": "Missing latitude, longitude, or place_name"}), 400
        
        lat = float(data['latitude'])
        lng = float(data['longitude'])
        place_name = data['place_name']
        language = data.get('language', 'English')
        
        if not place_name or not place_name.strip():
            return jsonify({"error": "place_name cannot be empty"}), 400
        
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        location_display = f"{place_name} ({lat}, {lng})"
        print(f"Generating audio for {location_display} in {language}")
        
        audio_path, transcript = check.generate_audio_for_location(lat, lng, place_name, language)
        
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            return jsonify({
                "transcript": transcript,
                "audio": audio_data,
                "audioFormat": "mp3"
            }), 200
        finally:
            try:
                if os.path.exists(audio_path):
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
    try:
        lat = request.args.get('latitude')
        lng = request.args.get('longitude')
        place_name = request.args.get('place_name')
        language = request.args.get('language', 'English')
        
        if not lat or not lng or not place_name:
            return jsonify({"error": "Missing latitude, longitude, or place_name"}), 400
        
        if not place_name.strip():
            return jsonify({"error": "place_name cannot be empty"}), 400
        
        lat = float(lat)
        lng = float(lng)
        
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        location_display = f"{place_name} ({lat}, {lng})"
        print(f"Generating audio for {location_display} in {language}")
        
        audio_path, transcript = check.generate_audio_for_location(lat, lng, place_name, language)
        
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            return jsonify({
                "transcript": transcript,
                "audio": audio_data,
                "audioFormat": "mp3"
            }), 200
        finally:
            try:
                if os.path.exists(audio_path):
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
