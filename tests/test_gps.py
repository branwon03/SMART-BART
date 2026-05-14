from src.backend.gps_lookup import calculate_distance, BART_STATIONS

# --- UNIT TESTS FOR MATH ---

def test_calculate_distance_same_point():
    """If the points are the same, distance should be 0."""
    lat, lon = 37.363896235419695, -120.42389535027772          #Arbitrary, ACS building coords
    assert calculate_distance(lat, lon, lat, lon) == 0

def test_calculate_distance_uc_merced():
    """Test distance between El Portal and Glacier Point (~0.14 miles)."""
    # Coords for UC Merced locations
    lat1, lon1 = 37.36158902195956, -120.42647249725572 # El Portal
    lat2, lon2 = 37.363076916497405, -120.42479034586975 # Glacier Point
    
    dist = calculate_distance(lat1, lon1, lat2, lon2)
    
    # Actual distance: ~0.138 miles. Checking if it's within a reasonable range (0.12 to 0.16).
    assert 0.12 <= dist <= 0.16

# --- TESTS FOR STATION SELECTION LOGIC ---

def get_nearest_name_only(user_lat, user_lon):
    """
    A helper function that runs just the 'nearest station' 
    logic without needing an image file.
    """
    distances = {
        name: calculate_distance(user_lat, user_lon, coords[0], coords[1])
        for name, coords in BART_STATIONS.items()
    }
    return min(distances, key=distances.get)

def test_nearest_station_exact_match():
    """Providing exact Gym coords should return 'Gym'."""
    gym_coords = BART_STATIONS["Gym"]
    assert get_nearest_name_only(gym_coords[0], gym_coords[1]) == "Gym"

def test_nearest_station_offset_pavilion():
    """A point slightly north of Pavilion Dining Center should still snap to it."""
    # Pavilion Dining Center base: (37.36411258128183, -120.4247885650939)
    # Adding a slight northern offset (~55 meters)
    lat, lon = 37.3642, -120.4247                                                                                           
    assert get_nearest_name_only(lat, lon) == "Pavilion Dining Center"
