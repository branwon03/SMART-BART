from src.backend.gps_lookup import calculate_distance, BART_STATIONS

# --- UNIT TESTS FOR MATH ---

def test_calculate_distance_same_point():
    """If the points are the same, distance should be 0."""
    lat, lon = 37.8049, -122.2951  # West Oakland
    assert calculate_distance(lat, lon, lat, lon) == 0

def test_calculate_distance_known_gap():
    """Test distance between West Oakland and 12th St Oakland (~1.3 miles)."""
    # Coords from your BART_STATIONS dict
    lat1, lon1 = 37.8049, -122.2951 # West Oakland
    lat2, lon2 = 37.8037, -122.2714 # 12th St
    dist = calculate_distance(lat1, lon1, lat2, lon2)
    
    # We allow a small margin of error (0.1 miles) for rounding
    assert 1.2 <= dist <= 1.4

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
    """Providing exact Fremont coords should return 'Fremont'."""
    fremont_coords = BART_STATIONS["Fremont"]
    assert get_nearest_name_only(fremont_coords[0], fremont_coords[1]) == "Fremont"

def test_nearest_station_offset():
    """A point slightly north of Downtown Berkeley should still snap to Berkeley."""
    # Offset Berkeley lat slightly
    lat, lon = 37.8710, -122.2681 
    assert get_nearest_name_only(lat, lon) == "Downtown Berkeley"

def test_far_away_point():
    """A point in Merced should snap to the closest station (Berryessa/North San José)."""
    # UC Merced Coords
    merced_lat, merced_lon = 37.3647, -120.4244
    assert get_nearest_name_only(merced_lat, merced_lon) == "Berryessa/North San José"