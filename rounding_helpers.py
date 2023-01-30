import time

def rounded_lat_lon(lat_lon: tuple) -> tuple:
    '''
    rounds() coordinates (lat, lon) to 6 decimals
    '''
    lat, lon = lat_lon
    nlat = round(lat, 6)
    nlon = round(lon, 6)
    return (nlat, nlon)

def rounded_timestamp() -> float:
    "rounds() a timestamp to 3 decimals"
    return round(time.time(), 3)