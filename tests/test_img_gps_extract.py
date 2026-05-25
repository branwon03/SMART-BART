from src.backend.img_gps_extract import to_decimal


def test_to_decimal_north():
    coords = (37.0, 21.0, 50.0)
    result = to_decimal(coords, "N")
    assert abs(result - 37.363889) < 0.001


def test_to_decimal_west():
    coords = (120.0, 25.0, 26.0)
    result = to_decimal(coords, "W")
    assert abs(result - (-120.423889)) < 0.001


def test_to_decimal_south():
    coords = (33.0, 52.0, 10.0)
    result = to_decimal(coords, "S")
    assert result < 0
