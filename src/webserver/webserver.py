import csv
import json
import os
import qrcode
import qrcode.image.svg
from datetime import (datetime, timezone, timedelta)
from flask import (Flask, render_template, request)
from flask_httpauth import HTTPBasicAuth
from pathlib import Path
from statistics import fmean
from werkzeug.security import (generate_password_hash, check_password_hash)

debug = False
cfg_file = None
devices_file = None
data_dir = None
device_refresh = 5000
base_url = None
device_path = '/device/<ID>/'
image_folder = '/app/static/img'

def make_qr_code(url, filename):
    filename = f'{image_folder}/{filename}.svg'
    if Path(filename).is_file():
        return
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgImage)
    with open(filename, 'wb') as f:
        img.save(f)

def get_devices():
    with open(devices_file) as f:
        obj = json.load(f)
    return obj['devices']

def write_latest_request(device_id):
    with open(Path(cfg_file).parent / f'{device_id}.json', 'w') as f:
        json.dump({device_id: datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)

def get_latest_request(device_id):
    file = Path(cfg_file).parent / f'{device_id}.json'
    if file.exists():
        with open(file, 'r') as f:
            obj = json.load(f)
        return obj[device_id]
    return ''

def write_settings(settings):
    with open(cfg_file, 'w') as f:
        json.dump(settings, f)

def get_settings():
    with open(cfg_file) as f:
        settings = json.load(f)
    settings['data_dir'] = data_dir
    settings['devices'] = get_devices()
    return settings

def set_settings(data):
    settings = get_settings()
    for key in data.keys():
        if key == 'offset':
            try:
                settings[key] = int(data[key])
                if abs(settings[key])>12:
                    settings[key] = 0
            except:
                settings[key] = 0
        else:
            settings[key] = data[key]

        if key == 'today' and data[key]==datetime.now().strftime("%Y-%m-%d"):
            del settings[key]

    del settings['devices']
    write_settings(settings)

def set_users():
    for device in get_devices():
        users[device['id']] = generate_password_hash(device['password'])
    users['admin'] = generate_password_hash(get_settings()['admin'])

def get_device_serial(devices, device_id):
    device = [x for x in devices if x['id']==device_id]
    if len(device)!=1:
        return
    return device[0]['serial']

def get_admin_data():

    def add_meta_data(dict, devices_with_data):
        dict['latest_request'] = get_latest_request(device_id=dict['id'])
        dict['has_data'] = dict['serial'] in devices_with_data
        return dict

    settings = get_settings()
    dsd = DeviceSessionData(settings=settings)
    data = {
        'show_graphs': settings['show_graphs'],
        'data_dir': settings['data_dir'],
        'devices': [add_meta_data(dict=x, devices_with_data=dsd.get_devices(dsd.data_dir)) for x in get_devices()],
        'session': {
            'today': get_today(settings),
            'start': settings['session_start'],
            'end': settings['session_end'],
            'offset': settings['offset']
        },
        'highlights': settings['highlights'] if 'highlights' in settings else []
    }

    return data

def get_today(settings):
    return settings['today'] if 'today' in settings else datetime.now().strftime("%Y-%m-%d")

def get_device_data(device_id):
    settings = get_settings()
    if device_id=='avg':
        avg_only = True
        for device in get_devices():
            path = Path(settings['data_dir']) / Path(get_today(settings)) / Path(device['serial'])
            if path.exists():
                device_id = device['id']
                break
    else:
        avg_only = False
    
    device_serial = get_device_serial(devices=settings['devices'], device_id=device_id)
    dsd = DeviceSessionData(settings=settings)

    if not device_serial:
        out = {'error': f"device {device_id} not found"}
        status = 404
    else:
        write_latest_request('avg' if avg_only else device_id)
        session_data = dsd.get_session_data(device=device_serial)
        data = {}
        status = 200
        for char in session_data['data']:
            data[char] = [
                {
                    'timestamp': x['timestamp'].strftime("%Y-%m-%d %H:%M"),
                    'value': 0 if avg_only else x['val'],
                    'average': [y['val'] for y in session_data['averages'][char] if y['timestamp']==x['timestamp']][0]
                } for x in session_data['data'][char]]

        def makeTimeToday(record, today):
            record['timestamp'] = f"{today} {record['timestamp']}"
            return record

        out = {
            'avg_only' : avg_only,
            'show_graphs': settings['show_graphs'],
            'session_data': data,
            'highlights': [ makeTimeToday(record=x, today=get_today(settings)) 
                           for x in settings['highlights']] if 'highlights' in settings else [],
            'session': {
                'today': get_today(settings),
                'start': settings['session_start'],
                'end': settings['session_end']
            },
        }

        return out, status

class DeviceSessionData:

    # [(var name, csv column header, json var name ), ... ]
    characteristics = [('eda', 'eda_scl_usiemens', 'eda'), ('pulse-rate', 'pulse_rate_bpm', 'pulse_rate')]

    def __init__(self, 
                 settings,
                 device=None) -> None:
        self.device = device
        self.data_dir = Path(settings['data_dir']) / Path(get_today(settings))
        self.session_data = []
        self.session_averages = []
        self.offset = settings['offset'] if 'offset' in settings else 0
        if self.data_dir.exists():
            self.session_data = self.set_session_data(
                devices=self.get_devices(data_dir=self.data_dir),
                chars=self.characteristics,
                session_start=self.to_timestamp(f"{get_today(settings)}T{settings['session_start']}:00Z"), 
                session_end=self.to_timestamp(f"{get_today(settings)}T{settings['session_end']}:00Z")
            )
            self.session_averages = self.calculate_averages()

    @staticmethod
    def to_timestamp(string, offset=0):
        return datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) + timedelta(hours=offset)
        # return datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    @staticmethod
    def get_devices(data_dir):
        devices = []
        if data_dir.exists():
            devices = [x.name for x in list(data_dir.iterdir())]
        return devices

    def get_device_data(self, device, char):
        data = []
        path = self.data_dir / Path(device)
        c_file = [str(x) for x in list(path.iterdir()) if f"_{char[0]}.csv" in x.name][0]
        if Path(c_file).exists():
            with open(c_file) as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    data.append({
                        'timestamp': self.to_timestamp(string=row['timestamp_iso'], offset=self.offset),
                        'val': float(0 if len(row[char[1]])==0 else row[char[1]]),
                        'error': row['missing_value_reason']})
        else:
            print(f"{c_file} doen't exist")
        return data

    def set_session_data(self, devices, chars, session_start, session_end):
        s_data = {}
        for device in devices:
            s_data[device] = {}
            for char in chars:
                d_data = self.get_device_data(device=device, char=char)
                s_data[device][char[2]] = [x for x in d_data if x['timestamp'] >= session_start and x['timestamp'] <= session_end]
        return s_data

    def calculate_averages(self):
        averages = {}
        for device in self.session_data.copy():
            for key in self.session_data[device]:
                d_data = self.session_data[device][key]

                if key not in averages:
                    averages[key] = [{'timestamp': x['timestamp'], 'val': []} for x in d_data]

                for ts in averages[key]:
                    t = [x['val'] for x in d_data if x['timestamp']==ts['timestamp'] and x['val']!=0]
                    if len(t)>0:
                        ts['val'].append(t[0])

        for key in averages:
            averages[key] = [{'timestamp': x['timestamp'], 'val': fmean(x['val']) if len(x['val'])>0 else 0} for x in averages[key]]
        
        return averages

    def get_session_data(self, device=None):
        if device and device in self.session_data:
            return { 'data': self.session_data[device], 'averages': self.session_averages } 
        return { 'data': {}, 'averages': self.session_averages } 

app = Flask(__name__)
auth = HTTPBasicAuth()
users = {}

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

@app.route('/')
def root():
    return render_template('root.html')

@app.route('/admin/')
@auth.login_required()
def admin():

    set_users()

    for device in get_devices():
        make_qr_code(f"{base_url}/device/{device['id']}/", f"qr_device_{device['id']}")
        make_qr_code(f"{base_url}/static/{device['id']}/", f"qr_static_{device['id']}")
    
    make_qr_code(f"{base_url}/device/avg/", f"qr_device_avg")

    data = {
        'data_url': f'/admin/data/',
        'data_reload': 30000,
        'device_path': device_path,
        'device_refresh': device_refresh
    }
    return render_template('admin.html', data=data)

@app.route('/admin/data/')
def admin_data():
    response = app.response_class(
        response=json.dumps(get_admin_data()),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/data/<device_id>/')
def data(device_id):

    data, status = get_device_data(device_id=device_id)

    response = app.response_class(
        response=json.dumps(data),
        status=status,
        mimetype='application/json'
    )

    return response

@app.route('/device/<device_id>/')
@app.route('/static/<device_id>/')
@auth.login_required
def device(device_id):
    static = '/static/' in request.path
    settings = get_settings()
    device_serial = get_device_serial(devices=settings['devices'], device_id=device_id)
    if not device_id=='avg' and not device_serial:
        return f"device {device_id} not found"

    device_data, _ = get_device_data(device_id=device_id)

    data = {
        'data_url': f'/data/{device_id}/',
        'data_reload': device_refresh,
        'static': static
    }

    if static:
        data['device_data'] = device_data

    return render_template('device.html', data=data)

@app.route('/ajax/', methods = ['POST'])
def ajax():
    data = request.json
    set_settings(data)
    settings = get_settings()
    del settings['admin']
    response = app.response_class(
        response=json.dumps(get_admin_data()),
        status=200,
        mimetype='application/json'
    )
    return response

if __name__ == '__main__':

    debug = os.getenv('DEBUG', '0')=='1'
    cfg_file = os.getenv('CFG_FILE', './config.json')
    devices_file = os.getenv('DEVICES_FILE', './devices.json')
    data_dir = os.getenv('DATA_DIR', '../../data/raw/')
    base_url = os.getenv('BASE_URL', 'https://lowlands2024.its-re.src.surf-hosted.nl')

    if debug:
        print(f"CFG_FILE={cfg_file}")
        print(f"DEVICES_FILE={devices_file}")
        print(f"DATA_DIR={data_dir}")
        print(f"devices: {get_devices()}")

    if not Path(cfg_file).exists():
        write_settings({
            'session_start': datetime.now().strftime("%H:%M"),
            'session_end': (datetime.now() + timedelta(hours=1)).strftime("%H:%M"),
            'show_graphs': False,
            'highlights': [],
            'last_requests': [],
            'offset': 2
        })

    set_users()
    app.run(host='0.0.0.0', debug=debug)
