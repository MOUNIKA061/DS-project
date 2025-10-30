import random, time

def generate_random_location(base_time=None):
    """Return a dict with timestamp, lat, lon. Latitude and longitude are random.
    """
    ts = base_time if base_time is not None else time.time()
    # random point roughly within some bounds (example: somewhere in world)
    lat = random.uniform(-85.0, 85.0)
    lon = random.uniform(-180.0, 180.0)
    return {"timestamp": ts, "lat": lat, "lon": lon}
