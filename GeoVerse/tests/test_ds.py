import time
from GeoVerse.data_structures.user_store import UserStore
from GeoVerse.data_structures.generator import generate_random_location

def smoke_test():
    s = UserStore()
    phone = '+15550001'
    try:
        uid = s.create_user(phone, 'pass123')
        print('Created user', uid)
    except Exception as e:
        uid = s.phone_to_userid(phone) or list(s.users.keys())[0]
        print('Using existing user', uid)

    # insert three online points
    for _ in range(3):
        e = generate_random_location()
        s.insert_location(uid, e['timestamp'], e['lat'], e['lon'], online=True)
    
    # insert two offline points (older timestamps)
    t = time.time() - 3600
    s.insert_location(uid, t - 30, 10.0, 10.0, online=False)
    s.insert_location(uid, t - 10, 11.0, 11.0, online=False)

    print('Timeline before sync:')
    for p in s.timeline(uid):
        print(p)

    s.sync_queue(uid)
    print('\nTimeline after sync:')
    for p in s.timeline(uid):
        print(p)

    # search last 2 hours
    now = time.time()
    res = s.search_range(uid, now - 7200, now + 10)
    print('\nSearch results:', len(res))

if __name__ == '__main__':
    smoke_test()
