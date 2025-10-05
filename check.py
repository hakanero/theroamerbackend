from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os
import requests
import google.generativeai as genai
import tempfile
from math import radians, cos, sin, sqrt, atan2
from dotenv import load_dotenv

load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
MAPS_API_KEY = os.getenv("MAPS_API_KEY")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def distance(lat1, lng1, lat2, lng2):
    R = 6371e3  # meters
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def get_nearby_places(lat, lng, radius=100, max_radius=200):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    while radius <= max_radius:
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": "point_of_interest",
            "key": MAPS_API_KEY
        }
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
        radius += 50
    return []

def describe_places(lat, lng):
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

def speech(msg):
    #load_dotenv()
    api_key = os.getenv("ELEVEN_API_KEY")
    #if not api_key:
     #   raise ValueError("Missing ELEVEN_API_KEY!")

    client = ElevenLabs(api_key=api_key)

   # msg = describe_places(lat, lng)
    print("Tour Guide:", msg)

    # Convert text → audio stream
    audio_stream = client.text_to_speech.convert(
        text=msg,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        for chunk in audio_stream:
            f.write(chunk)

if __name__ == "__main__":
    # White House, Washington DC
    speech(45.5052287, -73.5775577)