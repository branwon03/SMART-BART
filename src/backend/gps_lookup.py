import math
import requests
from io import BytesIO
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

BART_STATIONS = {
    "Embarcadero": (37.7928, -122.3970),
    "12th St. Oakland": (37.8037, -122.2714),
    "Downtown Berkeley": (37.8701, -122.2681),
    "Walnut Creek": (37.9055, -122.0675),
    "Dublin/Pleasanton": (37.7016, -121.8992),
    "West Oakland": (37.8049, -122.2951),
    "Fremont": (37.5574, -121.9766)
}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth."""
    R = 3959  # Earth radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_nearest_station_local(file_path):
    try:
        # Check if file exists first to avoid crashes
        if not os.path.exists(file_path):
            return f"File not found at {file_path}"

        img = Image.open(file_path)
        exif = img._getexif()
        
        if not exif:
            return "No Metadata Found in local image"

        gps_info = {}
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in value:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_info[sub_tag] = value[t]

        if not gps_info:
            return "No GPS Data in test_outlet.jpg"

        def to_decimal(coords, ref):
            # Safe conversion for EXIF rational types
            parts = [float(x) for x in coords]
            d, m, s = parts
            decimal = d + (m / 60.0) + (s / 3600.0)
            return -decimal if ref in ['S', 'W'] else decimal

        user_lat = to_decimal(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
        user_lon = to_decimal(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])

        distances = {
            name: calculate_distance(user_lat, user_lon, coords[0], coords[1])
            for name, coords in BART_STATIONS.items()
        }

        nearest = min(distances, key=distances.get)
        return f"{nearest}"# ({distances[nearest]:.2f} miles away)"

    except Exception as e:
        return f"Error: {str(e)}"
    

if __name__ == "__main__":
    #Test with local image
    test_file = "2-trashA.jpg"

    #result = get_nearest_station_local(test_file)
    
    #print(f"Result for {test_file}: {result}")