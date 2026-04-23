import math
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

BART_STATIONS = {
    "12th St. Oakland City Center": (37.8037, -122.2714),
    "16th St. Mission": (37.7651, -122.4197),
    "19th St. Oakland": (37.8078, -122.2690),
    "24th St. Mission": (37.7523, -122.4181),
    "Antioch": (37.9953, -121.7806),
    "Ashby": (37.8528, -122.2700),
    "Balboa Park": (37.7216, -122.4475),
    "Bay Fair": (37.6969, -122.1265),
    "Berryessa / North San Jose": (37.3684, -121.8746),
    "Castro Valley": (37.6907, -122.0756),
    "Civic Center / UN Plaza": (37.7797, -122.4141),
    "Coliseum": (37.7537, -122.1969),
    "Colma": (37.6846, -122.4662),
    "Concord": (37.9737, -122.0290),
    "Daly City": (37.7061, -122.4690),
    "Downtown Berkeley": (37.8701, -122.2681),
    "Dublin / Pleasanton": (37.7016, -121.8992),
    "El Cerrito del Norte": (37.9251, -122.3168),
    "El Cerrito Plaza": (37.9026, -122.2989),
    "Embarcadero": (37.7928, -122.3970),
    "Fremont": (37.5574, -121.9766),
    "Fruitvale": (37.7748, -122.2241),
    "Glen Park": (37.7315, -122.4338),
    "Hayward": (37.6697, -122.0870),
    "Lafayette": (37.8931, -122.1246),
    "Lake Merritt": (37.7970, -122.2651),
    "MacArthur": (37.8290, -122.2670),
    "Millbrae": (37.6002, -122.3867),
    "Milpitas": (37.4102, -121.8911),
    "Montgomery St.": (37.7894, -122.4010),
    "North Berkeley": (37.8740, -122.2834),
    "North Concord / Martinez": (38.0031, -122.0246),
    "Oakland International Airport": (37.7121, -122.2123),
    "Orinda": (37.8784, -122.1837),
    "Pittsburg / Bay Point": (38.0189, -121.9451),
    "Pittsburg Center": (38.0189, -121.8902),
    "Pleasant Hill / Contra Costa Centre": (37.9284, -122.0560),
    "Powell St.": (37.7844, -122.4080),
    "Richmond": (37.9368, -122.3530),
    "Rockridge": (37.8447, -122.2513),
    "San Bruno": (37.6377, -122.4162),
    "San Francisco International Airport": (37.6159, -122.3923),
    "San Leandro": (37.7219, -122.1608),
    "South Hayward": (37.6343, -122.0571),
    "South San Francisco": (37.6642, -122.4439),
    "Union City": (37.5906, -122.0173),
    "Walnut Creek": (37.9055, -122.0675),
    "Warm Springs / South Fremont": (37.5021, -121.9393),
    "West Dublin / Pleasanton": (37.6997, -121.9280),
    "West Oakland": (37.8049, -122.2951)
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
    
