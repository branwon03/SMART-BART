from src.backend.gps_lookup import calculate_distance, CAMPUS_BUILDINGS


BART_STATIONS = CAMPUS_BUILDINGS


def test_calculate_distance_same_point():
    lat, lon = 37.363896235419695, -120.42389535027772
    assert calculate_distance(lat, lon, lat, lon) == 0


def test_calculate_distance_uc_merced():
    lat1, lon1 = 37.36158902195956, -120.42647249725572  # El Portal
    lat2, lon2 = 37.363076916497405, -120.42479034586975  # Glacier Point
    dist = calculate_distance(lat1, lon1, lat2, lon2)
    assert 0.12 <= dist <= 0.16


def get_nearest_name_only(user_lat, user_lon):
    distances = {
        name: calculate_distance(user_lat, user_lon, coords[0], coords[1])
        for name, coords in CAMPUS_BUILDINGS.items()
    }
    return min(distances, key=distances.get)


def test_nearest_station_exact_match():
    gym_coords = CAMPUS_BUILDINGS["Gym"]
    assert get_nearest_name_only(gym_coords[0], gym_coords[1]) == "Gym"


def test_nearest_station_offset_pavilion():
    lat, lon = 37.3642, -120.4247
    assert get_nearest_name_only(lat, lon) == "Pavilion Dining Center"


def test_get_nearest_building_from_coords():
    from src.backend.gps_lookup import get_nearest_building_from_coords

    gym_coords = CAMPUS_BUILDINGS["Gym"]
    result = get_nearest_building_from_coords(gym_coords[0], gym_coords[1])
    assert result == "Gym"


def test_get_nearest_building_from_coords_returns_string():
    from src.backend.gps_lookup import get_nearest_building_from_coords

    result = get_nearest_building_from_coords(37.3642, -120.4247)
    assert isinstance(result, str)
    assert result in CAMPUS_BUILDINGS
