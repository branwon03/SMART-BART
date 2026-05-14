import math
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

BART_STATIONS = {
    "Arts and Computational Sciences": (37.363896235419695, -120.42389535027772), 
    "Bellevue Lot": (37.36046217603944, -120.42886485280854),
    "Biomedical Sciences and Physics": (37.364663934260975, -120.42264201521219),
    "Bobcat Field": (37.36260455474495, -120.42912793432374),
    "Cathedral": (37.36357799807278, -120.43033702798346),
    "Central Utilities Plant": (37.36645201370865, -120.42099811955525),
    "Classroom and Office Building 1": (37.36709759517184, -120.42336910599181),
    "Classroom and Office Building 2": (37.36700825415848, -120.42461726721234),
    "El Portal": (37.36158902195956, -120.42647249725572),
    "Glacier Point": (37.363076916497405, -120.42479034586975),
    "Granite Pass": (37.36304559187469, -120.42590002851557),
    "Gym": (37.36537831890965, -120.4261463602752),
    "Half Dome": (37.3641442616845, -120.42984518062514),
    "Kolligian Library": (37.36629383112198, -120.42460748693927),
    "Mariposa": (37.3653766767744, -120.42770883074229),
    "Pavilion Dining Center": (37.36411258128183, -120.4247885650939),
    "Scholar's Lot": (37.36223666704868, -120.4316525064889),
    "Science and Engineering": (37.36653412086759, -120.42226928709387),
    "Science and Engineering 2": (37.36587895346956, -120.42147945910962),
    "Sentinel Rock": (37.36246217574306, -120.42573555751889),
    "Social Sciences and Management": (37.36728212665387, -120.42198864662339),
    "Student Services Building": (37.36774266843638, -120.42286253467417),
    "Sustainability Research and Engineering": (37.3647419375431, -120.42421934285167),
    "Tenaya": (37.36358018068558, -120.42949653475515),
    "Tuolomne": (37.36506338890882, -120.42678374931111),
    "University Plaza": (37.36161718611481, -120.42723264722463),
    "Valley Terraces": (37.36411437125763, -120.42761655373933),
    "Yablokoff-Wallace Dining Center": (37.36454988338809, -120.42710185296478)
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
    
