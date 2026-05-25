"""
Nearest campus building lookup from image GPS coordinates.

Delegates GPS extraction to img_gps_extract (supports JPEG + HEIC/HEIF).
Uses the Haversine formula to find the nearest building.
"""

import math
from src.backend.img_gps_extract import extract_gps_coordinates

CAMPUS_BUILDINGS = {
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
    "Yablokoff-Wallace Dining Center": (37.36454988338809, -120.42710185296478),
}

BART_STATIONS = CAMPUS_BUILDINGS


def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine distance between two points in miles."""
    R = 3959
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_nearest_building_from_coords(lat: float, lon: float) -> str:
    """Return name of nearest campus building given decimal lat/lon."""
    distances = {
        name: calculate_distance(lat, lon, coords[0], coords[1])
        for name, coords in CAMPUS_BUILDINGS.items()
    }
    return min(distances, key=distances.get)


def get_nearest_station_local(file_path: str) -> str:
    """Extract GPS from image file and return nearest campus building name.

    Supports JPEG, PNG, HEIC/HEIF via the img_gps_extract adapter.
    Returns an error string (not exception) on failure, matching existing API contract.
    """
    try:
        lat, lon = extract_gps_coordinates(file_path)
        return get_nearest_building_from_coords(lat, lon)
    except FileNotFoundError:
        return f"File not found at {file_path}"
    except ValueError as e:
        return f"No GPS Data: {e}"
    except Exception as e:
        return f"Error: {e}"
