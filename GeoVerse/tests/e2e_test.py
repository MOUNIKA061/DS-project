import requests
import time
import re

BASE = 'http://127.0.0.1:5000'


def wait_for_server(timeout=10, interval=0.5):
    """Wait for the dev server to accept connections.
    Returns True if the server responds within timeout seconds, otherwise False.
    """
    s = requests.Session()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = s.get(BASE, timeout=1)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(interval)
    return False


def extract_userid_from_html(html):
    m = re.search(r"<strong>([0-9a-fA-F\-]+)</strong>", html)
    return m.group(1) if m else None


def run_e2e():
    ok = wait_for_server(timeout=15)
    if not ok:
        raise RuntimeError(f"Server at {BASE} did not become available within timeout")
    s = requests.Session()
    phone = f'+1555{int(time.time())%100000}'
    password = 'TestPass123!'
    print('Using phone:', phone)

    # Step 1: reserve userid
    r = s.post(f'{BASE}/signup', data={'step': 'phone', 'phone': phone})
    assert r.status_code in (200, 302), 'signup step1 failed'
    userid = extract_userid_from_html(r.text)
    assert userid, 'Could not extract userid from signup response'
    print('Reserved userid:', userid)

    # Step 2: finalize account with password
    r = s.post(f'{BASE}/signup', data={'step': 'create', 'userid': userid, 'password': password, 'confirm': password})
    assert r.status_code in (200, 302), 'signup finalize failed'
    assert 'Account created' in r.text or 'Your UserID' in r.text, 'Signup success page not found'
    print('Account finalized for', userid)

    # Login
    r = s.post(f'{BASE}/login', data={'login': phone, 'password': password}, allow_redirects=True)
    assert r.status_code in (200, 302), 'login failed'
    print('Logged in, dashboard status:', r.status_code)

    # initial timeline
    r = s.get(f'{BASE}/api/timeline', params={'userid': userid})
    assert r.status_code == 200
    data = r.json()
    initial_count = len(data.get('timeline', []))
    print('Initial timeline count:', initial_count)

    # generate 3 online points
    r = s.post(f'{BASE}/api/generate', json={'userid': userid, 'online': True, 'count': 3})
    assert r.status_code == 200
    created_online = r.json().get('created', [])
    print('Created online points:', len(created_online))

    # generate 2 offline points
    r = s.post(f'{BASE}/api/generate', json={'userid': userid, 'online': False, 'count': 2})
    assert r.status_code == 200
    created_offline = r.json().get('created', [])
    print('Created offline points (queued):', len(created_offline))

    # timeline should reflect only online points so far
    r = s.get(f'{BASE}/api/timeline', params={'userid': userid})
    timeline = r.json().get('timeline', [])
    after_online_count = len(timeline)
    print('Timeline count after online (before sync):', after_online_count)
    assert after_online_count >= initial_count + len(created_online), 'Online points not in timeline'

    # ensure offline points not in timeline yet (they would have source 'offline')
    offline_in_timeline = any(p.get('source') == 'offline' for p in timeline)
    assert not offline_in_timeline, 'Offline points should not be visible before sync'

    # sync
    r = s.post(f'{BASE}/api/sync', json={'userid': userid})
    assert r.status_code == 200
    synced = r.json().get('synced', [])
    print('Synced items:', len(synced))
    assert len(synced) == len(created_offline), 'Not all offline items were synced'

    # timeline after sync
    r = s.get(f'{BASE}/api/timeline', params={'userid': userid})
    timeline2 = r.json().get('timeline', [])
    after_sync_count = len(timeline2)
    print('Timeline count after sync:', after_sync_count)
    assert after_sync_count >= after_online_count + len(created_offline), 'Synced items not present in timeline'

    print('\nE2E test passed successfully')


if __name__ == '__main__':
    try:
        run_e2e()
    except AssertionError as e:
        print('E2E test failed:', e)
        raise
    except Exception as e:
        print('Unexpected error during E2E:', e)
        raise
