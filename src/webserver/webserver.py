import csv
import json
import os
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request
from flask_httpauth import HTTPBasicAuth
from pathlib import Path
from statistics import fmean
from werkzeug.security import generate_password_hash, check_password_hash

debug = False
cfg_file = None
devices_file = None
data_dir = None
device_refresh = 5000
device_path = '/device/<ID>/'

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
    if 'today' not in settings or len(settings['today'])==0:
        settings['today'] = datetime.now().strftime("%Y-%m-%d")
    return settings

def set_settings(data):
    settings = get_settings()
    for key in data.keys():
        if key in ['start_time', 'end_time']:
            settings[key] = f"{settings['today']}T{data[key]}:00Z"
        else:
            settings[key] = data[key]

        if key =='today' and data[key]==datetime.now().strftime("%Y-%m-%d"):
            del settings[key]

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
        dict['latest_request']=get_latest_request(device_id=dict['id'])
        dict['has_data']=dict['serial'] in devices_with_data
        return dict

    settings = get_settings()
    dsd = DeviceSessionData(settings=settings)
    data = {
        'show_graphs': settings['show_graphs'],
        'data_dir': settings['data_dir'],
        'devices': [add_meta_data(dict=x, devices_with_data=dsd.get_devices(dsd.data_dir)) for x in get_devices()],
        'session': {
            'today': settings['today'],
            'start': settings['session_start'],
            'end': settings['session_end']
        },
        'highlights': settings['highlights'] if 'highlights' in settings else []
    }

    return data

class DeviceSessionData:

    # [(var name, csv column header, json var name ), ... ]
    characteristics = [('eda', 'eda_scl_usiemens', 'eda'), ('pulse-rate', 'pulse_rate_bpm', 'pulse_rate')]

    def __init__(self, 
                 settings,
                 device=None) -> None:
        self.device = device
        self.data_dir = Path(settings['data_dir']) / Path(settings['today'])
        self.session_data = []
        self.session_averages = []
        if self.data_dir.exists():
            self.session_data = self.set_session_data(
                devices=self.get_devices(data_dir=self.data_dir),
                chars=self.characteristics,
                session_start=self.to_timestamp(f"{settings['today']}T{settings['session_start']}:00Z"), 
                session_end=self.to_timestamp(f"{settings['today']}T{settings['session_end']}:00Z")
            )
            self.session_averages = self.calculate_averages()

    @staticmethod
    def to_timestamp(string):
        return datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

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
                        'timestamp': self.to_timestamp(row['timestamp_iso']),
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
                    ts['val'].append([x['val'] for x in d_data if x['timestamp']==ts['timestamp']][0])
        
        for key in averages:
            averages[key] = [{'timestamp': x['timestamp'], 'val': fmean(x['val'])} for x in averages[key]]
        
        return averages

    def get_session_data(self, device=None):
        if device and device in self.session_data:
            return { 'data': self.session_data[device], 'averages': self.session_averages } 
        return { 'data': self.session_data, 'averages': self.session_averages } 

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

    avg_only = False
    if device_id=='avg':
        avg_only = True
        device_id = get_devices()[0]['id']

    settings = get_settings()
    device_serial = get_device_serial(devices=settings['devices'], device_id=device_id)
    dsd = DeviceSessionData(settings=settings)

    if not device_serial:
        out = {'error': f"device {device_id} not found"}
        status = 404
    else:
        write_latest_request(device_id)
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
            'highlights': [ makeTimeToday(record=x, today=settings['today']) 
                           for x in settings['highlights']] if 'highlights' in settings else [],
            'session': {
                'today': settings['today'],
                'start': settings['session_start'],
                'end': settings['session_end']
            },
        }

    response = app.response_class(
        response=json.dumps(out),
        status=status,
        mimetype='application/json'
    )

    return response

@app.route('/device/<device_id>/')
@auth.login_required
def device(device_id):
    settings = get_settings()
    device_serial = get_device_serial(devices=settings['devices'], device_id=device_id)
    if not device_id=='avg' and not device_serial:
        return f"device {device_id} not found"
    data = {
        'data_url': f'/data/{device_id}',
        'data_reload': device_refresh
    }
    return render_template('device.html', data=data)

@app.route('/ajax/', methods = ['POST'])
def ajax():
    data = request.json
    # print(data)
    set_settings(data)
    settings=get_settings()
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

    if debug:
        print(f"CFG_FILE={cfg_file}")
        print(f"DEVICES_FILE={devices_file}")
        print(f"DATA_DIR={data_dir}")
        print(f"devices: {get_devices()}")

    if not Path(cfg_file).exists():
        write_settings({
            'today': datetime.now().strftime("%Y-%m-%d"),
            'session_start': datetime.now().strftime("%H:%M"),
            'session_end': (datetime.now() + timedelta(hours=1)).strftime("%H:%M"),
            'show_graphs': False,
            'highlights': [],
            'last_requests': []
        })

    set_users()
    app.run(host='0.0.0.0', debug=debug)
