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

def get_nearby_places(lat, lng, radius=20, max_radius=100):
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
        radius += 20  # Smaller increments for more precision
    return []

def describe_places(lat, lng):
    places = get_nearby_places(lat, lng)
    if not places:
        prompt = f"""
        You are an information assistant. There are no significant pins or landmarks 
        returned at coordinates ({lat}, {lng}). 

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
        You are an information assistant. A person is standing at EXACT coordinates ({lat}, {lng}).  
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