import requests
import json
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================
WF_TOKEN = "c3095a0bc292a205fe1dcfe9d9f7fa60"  # Your iKitesurf session token
# REPLACE IN Jan 2027 - HOW:
# 1. Go here and login: https://wx.ikitesurf.com/spot/453
# 2. Press F12 devtools in firefox, go to `Storage` tab, click `Cookies` and find `wfToken`. 
#    There ya go put that here. (should have 13 month lease)
SPOT_ID = "453"  # Jupiter-Juno Beach Pier

# =============================================================================
# API FUNCTIONS
# =============================================================================
def get_wind_data(spot_id):
    """Fetch wind data from WeatherFlow API for a given spot."""
    url = "https://api.weatherflow.com/wxengine/rest/spot/getSpotDetailSetByList"
    
    params = {
        "units_wind": "kts",
        "units_temp": "f",
        "units_distance": "mi",
        "units_precip": "in",
        "include_spot_products": "true",
        "stormprint_only": "false",
        "wf_token": WF_TOKEN,
        "spot_types": "1,100,101",
        "spot_list": spot_id
    }
    
    headers = {
        "Accept": "*/*",
        "Origin": "https://wx.ikitesurf.com",
        "Referer": "https://wx.ikitesurf.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0"
    }
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def parse_wind_data(data):
    """Parse the API response into a clean dictionary."""
    if not data or data.get("status", {}).get("status_code") != 0:
        return None
    
    spot = data["spots"][0]
    station = spot["stations"][0]
    
    # Map field names to values
    field_names = spot["data_names"]
    field_values = station["data_values"][0]
    
    # Create a dictionary mapping names to values
    obs = dict(zip(field_names, field_values))
    
    return {
        "spot_name": spot["name"],
        "station_code": spot["station_code"],
        "city": spot["city"],
        "state": spot["state"],
        "lat": spot["lat"],
        "lon": spot["lon"],
        "timestamp_local": obs.get("timestamp"),
        "timestamp_utc": obs.get("utc_timestamp"),
        "wind_speed_avg": obs.get("avg"),
        "wind_lull": obs.get("lull"),
        "wind_gust": obs.get("gust"),
        "wind_dir_degrees": obs.get("dir"),
        "wind_dir_text": obs.get("dir_text"),
        "wind_description": obs.get("wind_desc"),
        "air_temp": obs.get("atemp"),
        "water_temp": obs.get("wtemp"),
        "pressure": obs.get("pres"),
        "humidity": obs.get("humidity"),
        "wave_height": obs.get("wave_height"),
        "wave_period": obs.get("wave_period"),
    }


def print_wind_report(wind_data):
    """Print a nice formatted wind report."""
    if not wind_data:
        print("No data available!")
        return
    
    print("\n" + "=" * 50)
    print(f"🏖️  {wind_data['spot_name']}")
    print(f"📍 {wind_data['city']}, {wind_data['state']}")
    print("=" * 50)
    print(f"🕐 {wind_data['timestamp_local']}")
    print("-" * 50)
    print(f"💨 Wind:     {wind_data['wind_speed_avg']} kts {wind_data['wind_dir_text']} ({wind_data['wind_dir_degrees']}°)")
    print(f"📈 Gust:     {wind_data['wind_gust']} kts")
    print(f"📉 Lull:     {wind_data['wind_lull']} kts")
    print(f"🌡️  Air Temp: {wind_data['air_temp']}°F")
    if wind_data['water_temp']:
        print(f"🌊 Water:    {wind_data['water_temp']}°F")
    print(f"🔘 Pressure: {wind_data['pressure']} mb")
    print("=" * 50 + "\n")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("Fetching wind data from Jupiter-Juno Beach Pier...")
    
    raw_data = get_wind_data(SPOT_ID)
    
    if raw_data:
        wind_data = parse_wind_data(raw_data)
        print_wind_report(wind_data)
        
        # Also print raw parsed data for debugging
        print("Raw parsed data:")
        print(json.dumps(wind_data, indent=2))