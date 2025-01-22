from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate("firebase/creds.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://weatherapp-27614-default-rtdb.firebaseio.com/"
})

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Helper function to validate dates
def validate_date_range(start_date, end_date):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            return False, "Start date must be before end date."
        return True, None
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD."

# Homepage route
@app.route("/")
def home():
    return render_template("index.html")

# CREATE endpoint
@app.route("/create", methods=["POST"])
def create_weather_request():
    data = request.json
    location = data.get("location")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    # Validate dates
    valid, message = validate_date_range(start_date, end_date)
    if not valid:
        return jsonify({"error": message}), 400

    # Load API key from .env
    api_key = os.getenv("API_KEY")
    if not api_key:
        return jsonify({"error": "API key is missing. Check your environment configuration."}), 500

    # Determine if input is a zip code or city name
    if location.isdigit():  # Likely a zip code
        geo_url = f"http://api.openweathermap.org/geo/1.0/zip?zip={location},US&appid={api_key}"
    else:  # Assume city name
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"

    # Validate location using Geocoding API
    geo_response = requests.get(geo_url)
    if geo_response.status_code != 200 or not geo_response.json():
        return jsonify({"error": "Invalid location or location not found."}), 400

    # Extract latitude and longitude
    if location.isdigit():  # Zip code response
        geo_data = geo_response.json()
        lat, lon = geo_data["lat"], geo_data["lon"]
    else:  # City name response
        geo_data = geo_response.json()[0]
        lat, lon = geo_data["lat"], geo_data["lon"]

    # Fetch weather data for the date range
    weather_data = []
    for single_date in (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=n)
                        for n in range((datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1)):
        unix_time = int(single_date.timestamp())
        weather_url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={unix_time}&appid={api_key}&units=imperial"
        weather_response = requests.get(weather_url)
        if weather_response.status_code == 200:
            weather_data.append(weather_response.json())
        else:
            return jsonify({"error": f"Error fetching weather for {single_date.strftime('%Y-%m-%d')}."}), 500

    # Format the location name to be used as the key
    location_key = location.replace(" ", "_").lower()

    # Store in Firebase using the location name as the key
    ref = db.reference(f"weather_requests/{location_key}")
    ref.set({
        "location": location,
        "date_range": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "weather_data": weather_data,
    })

    # Log and return the response
    response = {
        "message": "Weather request successfully created.",
        "location": location,
        "weather_data": weather_data
    }
    return jsonify(response), 201


@app.route("/current-weather", methods=["GET"])
def current_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    api_key = os.getenv("API_KEY")

    if not lat or not lon:
        return jsonify({"error": "Latitude and longitude are required."}), 400

    # Fetch current weather data
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
    response = requests.get(weather_url)

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch weather data."}), response.status_code

    weather_data = response.json()

    # Prepare data to send back to the frontend
    return jsonify({
        "location": weather_data["name"],
        "temp": weather_data["main"]["temp"],
        "weather": weather_data["weather"][0]["description"]
    })

if __name__ == "__main__":
    app.run(debug=True)
