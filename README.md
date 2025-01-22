## Weather Application

## Overview

This weather application allows users to search for weather data based on location and date range, utilize their current location for weather queries, and edit stored weather queries. It features a user-friendly interface and connects to the OpenWeatherMap API to fetch weather data.

## Features

1️⃣ Search for Weather by Location:

- 🌍 Users can input a location and a date range to retrieve weather data.

2️⃣ Use Current Location:

- 📍 Automatically fetch weather data for the user's current location using geolocation.

3️⃣ Edit Saved Queries:

- ✏️ Update the date range of a previously saved location query.

4️⃣ Dynamic Weather Output:

- 🌦️ View weather data including temperature, conditions, humidity, and wind speed.

5️⃣ Settings Modal:

- ⚙️ Download all database information to a CSV

6️⃣ Info Modal:

- ℹ️ Displays name and PM info.


## Technologies Used

### Frontend

- 🏗️ HTML5: Structuring the app’s interface.

- 🎨 CSS3 : Styling for responsive and visually appealing designs.

- 🛠️ JavaScript (Vanilla): Handling user interactions and API calls.

### Backend

- 🐍 Python (Flask): Server-side handling of API requests and database interactions.

- 🔥 Firebase: Storing and managing weather query data.

## Installation

1️⃣ Clone the Repository:

git clone https://github.com/branmh79/WeatherApp.git
cd <repository-folder>

2️⃣ Set Up Backend Environment:

Install Python dependencies:

pip install -r requirements.txt

Set environment variables for API keys (e.g., OpenWeatherMap API key).

3️⃣ Run the Application:

Start the Flask server in terminal:

python app.py

4️⃣ Access the Application:

Open a browser and navigate to:

http://127.0.0.1:5000

## Usage Instructions

### Searching for Weather Data

1️⃣ Enter a location in the search bar.
2️⃣ Specify a start and end date.
3️⃣ Click Submit to fetch weather data.

### Using Current Location

1️⃣ Click the Use Current Location button.
2️⃣ Grant browser permission to access location.
3️⃣ Specify a date range and click Submit.

### Editing a Saved Query

1️⃣ Click Edit next to a saved location.
2️⃣ Update the start and end dates.
3️⃣ Click Save to update the query.

### Contribution

1️⃣ Fork the repository and create a new branch for your feature.
2️⃣ Implement your feature or bug fix.
3️⃣ Submit a pull request for review.

