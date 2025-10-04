import os
import time
import math
import sys
import google.generativeai as genai
import check
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
# Distance is currently about 5 city blocks apart. 


Base_lat = 41.529146
Base_lon = -71.418785
End_lat = 41.529146
End_lon = -71.418785

load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

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

if __name__ == "__main__":
    

    max_iterations = 0  # Set your limit
    same_place_loop = 0
    iteration = 0
    update_interval = 0  # seconds
    initial_delay = 30
    

    try:

        while True:
            
            #End_lat += .01 #Just for testing purposes
            #End_lon += .01 #Just for testing purposes

            iteration += 1
            distance = haversine_distance(Base_lat, Base_lon, End_lat, End_lon)
            
            print(distance)
             #Just for testing purposes
            if distance > .8: 
                Base_lat = End_lat
                Base_lon = End_lon
                same_place_loop = 0
            else:
                same_place_loop += 1


            location = f"{Base_lat}, {Base_lon}"
            base_prompt = f"You are a historian. Provide a detailed history of the area immediately surrounding" + location + "within about 50 feet. Begin with Indigenous use of the land, then colonial settlement, industrialization, institutional growth, and modern developments. Focus on specific changes to the land, buildings, and community. Present the answer as a chronological timeline followed by a short narrative description. It should take approximately 2 minutes to read aloud, and do not mention any of the prompting given"
            
            # Build question based on what's been said before
            if same_place_loop == 1:
                question1 = base_prompt
                answer1 = ask_gemini(question1)
            elif same_place_loop == 2:
                question2 = base_prompt + " You already mentioned the following facts, do not repeat yourself: " + answer1
                answer2 = ask_gemini(question2)
            else:
                # For same_place_loop == 0 or >= 3
                if same_place_loop >= 3:
                    question3 = base_prompt + " Focus on a description of present day uses, and do not mention the following facts, do not repeat yourself: " + answer1 + " " + answer2
                else:
                    # First iteration (same_place_loop == 0)
                    question3 = base_prompt
                answer3 = ask_gemini(question3)

            if iteration == 1:
                time.sleep(initial_delay) #Delays the first output by 30 seconds

            if same_place_loop == 1:
                check.speech(answer1)
            elif same_place_loop == 2:
                check.speech(answer2)
            else:
                check.speech(answer3)

            #Output code for audio

            time.sleep(update_interval)

            if iteration > max_iterations:
                break  # Exits the while loop
    
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)