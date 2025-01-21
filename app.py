from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None
    city_name = None
    if request.method == "POST":
        location = request.form.get("location", "").strip()
        api_key = os.getenv("API_KEY")

        # Determine if input is a zip code or city name
        if location.isdigit():  # Likely a zip code
            geo_url = "http://api.openweathermap.org/geo/1.0/zip"
            geo_params = {"zip": location + ",US", "appid": api_key}
            geo_response = requests.get(geo_url, params=geo_params)

            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                lat, lon = geo_data["lat"], geo_data["lon"]
                city_name = geo_data.get("name", "Unknown City")
            else:
                error = "Zip code not found."
        elif location:  # Likely a city name
            geo_url = "http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {"q": location, "limit": 1, "appid": api_key}
            geo_response = requests.get(geo_url, params=geo_params)

            if geo_response.status_code == 200 and len(geo_response.json()) > 0:
                geo_data = geo_response.json()[0]
                lat, lon = geo_data["lat"], geo_data["lon"]
                city_name = geo_data.get("name", location)
            else:
                error = "City not found."

        # Fetch weather data if lat/lon and city_name are available
        if not error and city_name:
            weather = get_weather(lat, lon, api_key)

    return render_template("index.html", weather=weather, city_name=city_name, error=error)


@app.route("/weather_by_location", methods=["POST"])
def weather_by_location():
    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")
    api_key = os.getenv("API_KEY")

    if lat and lon:
        weather = get_weather(lat, lon, api_key)
        # Add city name by reverse geocoding
        geo_url = "http://api.openweathermap.org/geo/1.0/reverse"
        geo_params = {"lat": lat, "lon": lon, "limit": 1, "appid": api_key}
        geo_response = requests.get(geo_url, params=geo_params)

        if geo_response.status_code == 200 and len(geo_response.json()) > 0:
            city_name = geo_response.json()[0].get("name", "Unknown Location")
            weather["city_name"] = city_name
        else:
            weather["city_name"] = "Unknown Location"

        return jsonify(weather)
    else:
        return jsonify({"error": "Latitude and longitude are required."}), 400



def get_weather(lat, lon, api_key):
    """Fetch weather data using OpenWeatherMap One Call API."""
    weather_url = "https://api.openweathermap.org/data/3.0/onecall"
    weather_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "imperial"}
    weather_response = requests.get(weather_url, params=weather_params)

    if weather_response.status_code == 200:
        return weather_response.json()
    else:
        return {"error": "Could not retrieve weather data."}


if __name__ == "__main__":
    app.run(debug=True)
