from flask import Flask, render_template, request
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
        location = request.form.get("location").strip()
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
        else:  # Likely a city name
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
            weather_url = "https://api.openweathermap.org/data/3.0/onecall"
            weather_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
            weather_response = requests.get(weather_url, params=weather_params)

            if weather_response.status_code == 200:
                weather = weather_response.json()
            else:
                error = "Could not retrieve weather data."

    return render_template("index.html", weather=weather, city_name=city_name, error=error)

if __name__ == "__main__":
    app.run(debug=True)
