from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
import time

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
    try:
        data = request.json
        location = data.get("location")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        print(f"Request received: location={location}, start_date={start_date}, end_date={end_date}")

        # Validate date range
        valid, message = validate_date_range(start_date, end_date)
        if not valid:
            print(f"Invalid date range: {message}")
            return jsonify({"error": message}), 400

        # Load API key
        api_key = os.getenv("API_KEY")
        if not api_key:
            return jsonify({"error": "API key is missing. Check your environment configuration."}), 500

        # Determine location type (zip code or city name)
        if location.isdigit():
            geo_url = f"http://api.openweathermap.org/geo/1.0/zip?zip={location},US&appid={api_key}"
        else:
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"

        # Validate location
        geo_response = requests.get(geo_url)
        if geo_response.status_code != 200 or not geo_response.json():
            print(f"Invalid location response: {geo_response.text}")
            return jsonify({"error": "Invalid location or location not found."}), 400

        if location.isdigit():
            geo_data = geo_response.json()
            lat, lon = geo_data["lat"], geo_data["lon"]
        else:
            geo_data = geo_response.json()[0]
            lat, lon = geo_data["lat"], geo_data["lon"]

        # Initialize weather data
        weather_data = []

        # Make all datetime objects timezone-aware
        today = datetime.now(timezone.utc).date()
        max_date = today + timedelta(days=7)
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Adjust the end date to the maximum allowed (7 days ahead)
        limited_end_date = min(end_date_dt, max_date)
        exceeded_limit = end_date_dt > max_date

        # Fetch historical data for the range prior to today
        if start_date_dt < today:
            for single_date in (start_date_dt + timedelta(days=n) for n in range((min(today, end_date_dt) - start_date_dt).days)):
                single_datetime = datetime.combine(single_date, datetime.min.time(), timezone.utc)  # Combine date with midnight UTC
                unix_time = int(single_datetime.timestamp())
                weather_url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={unix_time}&appid={api_key}&units=imperial"
                response = requests.get(weather_url)

                if response.status_code == 200:
                    day_data = response.json()
                    if "data" in day_data and day_data["data"]:
                        current_weather = day_data["data"][0]
                        weather_data.append({
                            "date": single_datetime.date().strftime("%Y-%m-%d"),  # Correct date handling
                            "temp": current_weather.get("temp", "N/A"),
                            "conditions": current_weather.get("weather", [{}])[0].get("description", "N/A"),
                        })
                else:
                    print(f"Error fetching historical weather for {single_date.strftime('%Y-%m-%d')}: {response.text}")

        # Fetch forecast data for the remaining range
        if limited_end_date >= today:
            forecast_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
            forecast_response = requests.get(forecast_url)

            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                if "daily" in forecast_data:
                    for daily in forecast_data["daily"]:
                        forecast_date = datetime.fromtimestamp(daily["dt"], tz=timezone.utc).date()  # Use UTC-aware datetime
                        if max(start_date_dt, today) <= forecast_date <= limited_end_date:
                            weather_data.append({
                                "date": forecast_date.strftime("%Y-%m-%d"),  # Ensure correct date format
                                "temp": daily.get("temp", {}).get("day", "N/A"),
                                "conditions": daily.get("weather", [{}])[0].get("description", "N/A"),
                            })

        # Ensure no duplicate entries in weather_data
        unique_weather_data = {entry["date"]: entry for entry in weather_data}.values()

        # Save data to Firebase
        location_key = location.replace(" ", "_").lower()
        ref = db.reference(f"weather_requests/{location_key}")
        ref.set({
            "location": location,
            "date_range": {
                "start_date": start_date,
                "end_date": limited_end_date.strftime("%Y-%m-%d"),
            },
            "weather_data": list(unique_weather_data),
        })

        # Prepare response message
        message = "Weather request successfully created."
        if exceeded_limit:
            message += " Note: Weather data is only available up to 7 days in the future."

        print(f"Weather request successfully saved for {location}.")
        return jsonify({
            "message": message,
            "location": location,
            "weather_data": list(unique_weather_data)
        }), 201

    except Exception as e:
        print(f"Error in /create: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500



@app.route("/current-weather", methods=["GET"])
def current_weather():
    try:
        location = request.args.get("location")
        lat = request.args.get("lat")
        lon = request.args.get("lon")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        print(f"Request received: location={location}, lat={lat}, lon={lon}, start_date={start_date}, end_date={end_date}")

        if not start_date or not end_date:
            return jsonify({"error": "Start and end dates are required."}), 400

        # Convert dates to datetime objects
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Case 1: Fetch from the database if location is provided
        if location:
            ref = db.reference("weather_requests")
            saved_data = ref.order_by_child("location").equal_to(location).get()
            print(f"Query result for location '{location}': {saved_data}")

            if saved_data:
                for key, value in saved_data.items():
                    weather_data = [
                        entry for entry in value.get("weather_data", [])
                        if start_date_dt <= datetime.strptime(entry["date"], "%Y-%m-%d").date() <= end_date_dt
                    ]

                    # Filter weather data by the requested date range
                    filtered_weather_data = [
                        entry for entry in weather_data
                        if start_date_dt <= datetime.strptime(entry["date"], "%Y-%m-%d").date() <= end_date_dt
                    ]

                    return jsonify({
                        "message": "Data fetched from database.",
                        "location": location,
                        "weather_data": filtered_weather_data
                    }), 200

            return jsonify({"error": f"No data found for location '{location}'."}), 404

        # Case 2: Fetch from the API if lat and lon are provided
        if lat and lon:
            api_key = os.getenv("API_KEY")
            date_diff = (end_date_dt - start_date_dt).days + 1

            if date_diff > 14:
                return jsonify({"error": "You can only request weather data for up to 14 days at a time."}), 400

            # Reverse Geocoding to get city name
            geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={api_key}"
            geo_response = requests.get(geo_url)
            if geo_response.status_code != 200 or not geo_response.json():
                return jsonify({"error": "Failed to fetch location details."}), 500

            geo_data = geo_response.json()[0]
            city_name = geo_data.get("name", "Current Location")

            # Fetch weather data
            weather_data = []
            for single_date in (start_date_dt + timedelta(days=n) for n in range(date_diff)):
                single_datetime = datetime.combine(single_date, datetime.min.time(), timezone.utc)
                unix_time = int(single_datetime.timestamp())
                weather_url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={unix_time}&appid={api_key}&units=imperial"
                response = requests.get(weather_url)

                if response.status_code != 200:
                    return jsonify({"error": f"Error fetching weather for {single_date.strftime('%Y-%m-%d')}.", "details": response.text}), 500

                data = response.json()
                if "data" in data and data["data"]:
                    day_data = data["data"][0]
                    weather_data.append({
                        "date": single_date.strftime("%Y-%m-%d"),
                        "temp": day_data.get("temp", "N/A"),
                        "conditions": day_data["weather"][0]["description"] if day_data.get("weather") else "N/A"
                    })

            return jsonify({
                "location": city_name,
                "weather_data": weather_data
            }), 200

        return jsonify({"error": "Either location or latitude and longitude are required."}), 400

    except Exception as e:
        print(f"Error in /current-weather: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500


    
@app.route("/read-locations", methods=["GET"])
def read_locations():
    try:
        # Reference the Firebase database node for weather requests
        ref = db.reference("weather_requests")
        data = ref.get()  # Retrieve all saved data

        # Extract locations from the data
        if data:
            locations = [entry["location"] for entry in data.values() if "location" in entry]
        else:
            locations = []

        # Return the list of locations
        return jsonify({"locations": locations}), 200

    except Exception as e:
        print(f"Error in /read-locations: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching locations."}), 500


if __name__ == "__main__":
    app.run(debug=True)
