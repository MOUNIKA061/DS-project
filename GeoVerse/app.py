from flask import Flask, request, render_template, redirect, url_for, jsonify
from data_structures.user_store import UserStore
from data_structures.generator import generate_random_location
import time
import threading
import random

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'replace-this-with-a-secure-secret'

store = UserStore()
# per-user online status (True=online, False=offline). Default: True when initialized.
user_online_status = {}


def ensure_user_status(userid):
    if userid not in user_online_status:
        user_online_status[userid] = True
    return user_online_status[userid]


# Background generator thread: periodically create simulated locations for users.
def generator_loop(poll_interval=10):
    while True:
        try:
            # snapshot user ids
            userids = list(store.users.keys())
            for uid in userids:
                # decide interval per user to jitter generation
                # skip if user structures missing (will be initialized on demand)
                ensure_user_status(uid)
                online = user_online_status.get(uid, True)
                # generate a random location and insert accordingly
                entry = generate_random_location()
                ts = entry.get('timestamp', time.time())
                if online:
                    store.insert_location(uid, ts, entry['lat'], entry['lon'], online=True)
                else:
                    store.insert_location(uid, ts, entry['lat'], entry['lon'], online=False)
                # small sleep between users to avoid tight bursts
                time.sleep(0.05)
        except Exception:
            # swallow thread exceptions, continue looping
            pass
        # randomize wait to simulate 10-30s
        time.sleep(random.uniform(poll_interval, poll_interval + 20))


# start background thread once
gen_thread = threading.Thread(target=generator_loop, args=(10,), daemon=True)
gen_thread.start()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Two-step signup:
    # Step 1: user POSTs phone -> reserve userid and show password form
    # Step 2: user POSTs userid + password -> finalize account
    if request.method == 'GET':
        return render_template('signup_phone.html')

    # POST
    step = request.form.get('step', 'phone')
    if step == 'phone':
        phone = request.form.get('phone')
        if not phone:
            return 'Missing phone', 400
        try:
            userid = store.reserve_user(phone)
        except ValueError as e:
            return str(e), 400
        # render password form and show generated userid
        return render_template('signup_password.html', phone=phone, userid=userid)

    if step == 'create':
        userid = request.form.get('userid')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if not userid or not password or not confirm:
            return 'Missing fields', 400
        if password != confirm:
            return 'Passwords do not match', 400
        try:
            store.set_password_for_user(userid, password)
        except ValueError as e:
            return str(e), 400
        # show success page with UserID
        return render_template('signup_success.html', userid=userid)

    return 'Invalid signup step', 400

@app.route('/login', methods=['POST'])
def login():
    login = request.form.get('login')
    password = request.form.get('password')
    userid = store.authenticate(login, password)
    if not userid:
        return 'Invalid credentials', 401
    # simple flow: redirect to dashboard with userid in query
    return redirect(url_for('dashboard') + f'?userid={userid}')

@app.route('/dashboard')
def dashboard():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return redirect(url_for('index'))
    # ensure status exists
    ensure_user_status(userid)
    return render_template('dashboard.html', userid=userid)


@app.route('/api/latest-location')
def api_latest_location():
    userid = request.args.get('userid')
    count = int(request.args.get('count', 5))
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    timeline = store.timeline(userid)
    # return last `count` entries
    last = timeline[-count:] if len(timeline) > 0 else []
    return jsonify({'latest': last})


@app.route('/api/offline-queue-count')
def api_offline_queue_count():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    s = store.get_structs(userid)
    q = s['queue']
    return jsonify({'count': len(q)})


@app.route('/api/sync-offline-data', methods=['POST'])
def api_sync_offline_data():
    data = request.json or {}
    userid = data.get('userid')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    inserted = store.sync_queue(userid)
    return jsonify({'synced': [n.to_dict() for n in inserted]})


@app.route('/api/user-status', methods=['GET'])
def api_user_status():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    status = user_online_status.get(userid, True)
    return jsonify({'online': bool(status)})


@app.route('/api/set-online', methods=['POST'])
def api_set_online():
    data = request.json or {}
    userid = data.get('userid')
    online = data.get('online')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    user_online_status[userid] = bool(online)
    return jsonify({'ok': True, 'online': user_online_status[userid]})


@app.route('/history')
def history():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return redirect(url_for('index'))
    return render_template('history.html', userid=userid)


@app.route('/timeline')
def timeline_page():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return redirect(url_for('index'))
    return render_template('timeline.html', userid=userid)


@app.route('/search')
def search_page():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return redirect(url_for('index'))
    # Search page removed; redirect users to the Timeline Map which contains search controls
    return redirect(url_for('timeline_page') + f'?userid={userid}')

@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json or {}
    userid = data.get('userid')
    online = data.get('online', True)
    count = int(data.get('count', 1))
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    created = []
    for _ in range(count):
        entry = generate_random_location()
        ts = entry['timestamp'] if 'timestamp' in entry else time.time()
        if online:
            node = store.insert_location(userid, ts, entry['lat'], entry['lon'], online=True)
            created.append(node.to_dict())
        else:
            store.insert_location(userid, ts, entry['lat'], entry['lon'], online=False)
            created.append({'timestamp': ts, 'lat': entry['lat'], 'lon': entry['lon'], 'source': 'offline'})
    return jsonify({'created': created})

@app.route('/api/sync', methods=['POST'])
def api_sync():
    data = request.json or {}
    userid = data.get('userid')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    inserted = store.sync_queue(userid)
    return jsonify({'synced': [n.to_dict() for n in inserted]})

@app.route('/api/timeline')
def api_timeline():
    userid = request.args.get('userid')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    return jsonify({'timeline': store.timeline(userid)})

@app.route('/api/search')
def api_search():
    userid = request.args.get('userid')
    start = float(request.args.get('start', 0))
    end = float(request.args.get('end', time.time()))
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    res = store.search_range(userid, start, end)
    return jsonify({'results': res})


@app.route('/api/search-nearest')
def api_search_nearest():
    userid = request.args.get('userid')
    ts = request.args.get('ts')
    if not userid or not store.userid_exists(userid):
        return jsonify({'error': 'invalid userid'}), 400
    if not ts:
        return jsonify({'error': 'missing ts'}), 400
    try:
        tsv = float(ts)
    except Exception:
        return jsonify({'error': 'invalid ts'}), 400
    res = store.search_nearest(userid, tsv)
    return jsonify({'results': res})

if __name__ == '__main__':
    app.run(debug=True)
