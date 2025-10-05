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
    R = 6371e3
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
            filtered_results = []
            for p in results:
                dist = distance(
                    lat, lng,
                    p["geometry"]["location"]["lat"],
                    p["geometry"]["location"]["lng"]
                )
                if dist <= 50:
                    filtered_results.append((p, dist))
            
            if filtered_results:
                filtered_results.sort(key=lambda x: x[1])
                return [p[0] for p in filtered_results[:3]]
        radius += 20
    return []


def describe_places(lat, lng, place_name, language):
    places = get_nearby_places(lat, lng)

    location_context = f"near coordinates ({lat}, {lng}), at {place_name} street or square"
    
    if not places:
        prompt = f"""
        You are an information assistant. There are no significant pins or landmarks 
        returned for a person standing {location_context}. 

        Give a short, factual description of what is IMMEDIATELY around this exact location 
        within 20-30 meters ONLY. 

        -Give names of specific buildings, entrances, pathways, statues, plaques,
        - point out any historical markers or notable architectural features.
        - Do NOT describe weather, trees, skies, or generic scenery.  
        - Do NOT mention large landmarks or areas unless the person is standing directly at them.
        - Only describe what is in the IMMEDIATE vicinity: specific buildings, entrances, 
        pathways, statues, plaques, or architectural features RIGHT where they're standing.
        - If possible, describe them in terms of direction from the person: 
        "Directly in front of you is...", "To your immediate left is...", etc.  
        - Be HYPERSPECIFIC about the exact spot, not the general area.
        - Keep the language factual, and precise (5 sentences max).  
        - Include historical notes if relevant.  
        - Avoid storytelling, no "imagine this," no "alright everyone," no fluff.  
        - Respond to this prompt in the {language} language
        """
    else:
        place_info = [f"{p.get('name')} ({', '.join(p.get('types', []))})" for p in places]
        prompt = f"""
        You are an information assistant. A person is standing at {location_context}.  
        Here are the closest nearby places (all within 50 meters):

        {chr(10).join(place_info)}

        Your task:
        -Give names of specific buildings, entrances, pathways, statues, plaques,
        - point out any historical markers or notable architectural features.
        - Do NOT describe weather, trees, skies, or generic scenery.  
        - Do NOT mention large landmarks or areas unless the person is standing directly at them.
        - Only describe what is in the IMMEDIATE vicinity: specific buildings, entrances, 
        pathways, statues, plaques, or architectural features RIGHT where they're standing.
        - If possible, describe them in terms of direction from the person: 
        "Directly in front of you is...", "To your immediate left is...", etc.  
        - Be HYPERSPECIFIC about the exact spot, not the general area.
        - Keep the language factual, and precise (5 sentences max).  
        - Include historical notes if relevant.  
        - Avoid storytelling, no "imagine this," no "alright everyone," no fluff.  
        - DO NOT describe generic shops, hotels, gyms, or residential apartments unless
        they are historically/culturally important to THIS EXACT SPOT.
        talk about buildings that have names for example Harvard Law School, the White House etc.
        - Talk in order first talk about buildings exactly beside and near the person and then start further away, be more precise
        you can do it 
        - also dont keep talking about the same area even if we moved away update frequently
        - Respond to this prompt in the {language} language
        """

    response = model.generate_content(prompt)
    return response.text

def speech(msg):
    api_key = os.getenv("ELEVEN_API_KEY")
    if not api_key:
        raise ValueError("Missing ELEVEN_API_KEY!")

    client = ElevenLabs(api_key=api_key)

    print("Tour Guide:", msg)

    audio_stream = client.text_to_speech.convert(
        text=msg,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        for chunk in audio_stream:
            f.write(chunk)
        return f.name

def generate_audio_for_location(lat, lng, place_name, language="English"):
    description = describe_places(lat, lng, place_name, language)
    audio_file_path = speech(description)
    
    return audio_file_path, description

# How do I plug in the language to the describe_places function?
# Still need to define the get_language function and uncomment
# the language variable in the describe_places function