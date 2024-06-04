import csv
import json
import os
from datetime import datetime, timezone
from flask import Flask, render_template, request
from pathlib import Path
from statistics import fmean

def write_settings(settings):
    with open(cfg_file, 'w') as f:
        json.dump(settings, f)

def read_settings():
    with open(cfg_file) as f:
        settings = json.load(f)
    return settings

def set_settings(data):
    settings = read_settings()
    for key in data.keys():
        if key in ['start_time', 'end_time']:
            settings[key] = f"{settings['today']}T{data[key]}:00Z"
        else:
            settings[key] = data[key]
    write_settings(settings)

def get_device_serial(device_ids, device_id):
    device = [x for x in device_ids if x['id']==device_id]
    if len(device)!=1:
        return
    return device[0]['serial']

class DeviceSessionData:

    # [(var name, csv column header, json var name ), ... ]
    characteristics = [('eda', 'eda_scl_usiemens', 'eda'), ('pulse-rate', 'pulse_rate_bpm', 'pulse_rate')]

    def __init__(self, 
                 settings,
                 device=None) -> None:
        self.device = device
        self.data_dir = Path(settings['data_root_dir']) / Path(settings['today'])

        if self.data_dir.exists():
            self.session_data = self.retrieve_session_data(
                devices=self.get_devices(data_dir=self.data_dir),
                chars=self.characteristics,
                session_start=self.to_timestamp(f"{settings['today']}T{settings['session_start']}:00Z"), 
                session_end=self.to_timestamp(f"{settings['today']}T{settings['session_end']}:00Z")
            )
            self.session_averages = self.calculate_averages()
        # else:
        #     raise FileNotFoundError(str(self.data_dir))
    
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

    def retrieve_session_data(self, devices, chars, session_start, session_end):
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
        if device:
            return { 'data': self.session_data[device], 'averages': self.session_averages } 
        return { 'data': self.session_data, 'averages': self.session_averages } 

cfg_file = "./config.json"
app = Flask(__name__)

@app.route('/')
def root():
    dsd = DeviceSessionData(settings=read_settings())
    return dsd.get_session_data()

@app.route('/admin')
def admin():
    settings = read_settings()
    dsd = DeviceSessionData(settings=settings)
    data = {
        'data_root_dir': settings['data_root_dir'],
        'device_ids': settings['device_ids'],
        'devices_with_data': dsd.get_devices(dsd.data_dir),
        'session': {
            'today': settings['today'],
            'start': settings['session_start'],
            'end': settings['session_end']
        },
        'highlights': settings['highlights'] if 'highlights' in settings else []
    }

    return render_template('admin.html', data=data)

@app.route('/data/<device_id>')
def data(device_id):
    settings = read_settings()
    device_serial = get_device_serial(device_ids=settings['device_ids'], device_id=device_id)
    dsd = DeviceSessionData(settings=settings)

    if not device_serial:
        data = f"device {device_id} not found"
        status = 404
    else:
        session_data = dsd.get_session_data(device=device_serial)
        data = {}
        status = 200
        for char in session_data['data']:
            
            data[char] = [
                {
                    'timestamp': x['timestamp'].strftime("%Y-%m-%d %H:%M"),
                    'value': x['val'],
                    'average': [y['val'] for y in session_data['averages'][char] if y['timestamp']==x['timestamp']][0]
                } for x in session_data['data'][char]]

    response = app.response_class(
        response=json.dumps(data),
        status=status,
        mimetype='application/json'
    )

    return response

@app.route('/device/<device_id>')
@app.route('/device/<device_id>/')
def device(device_id):
    settings = read_settings()
    device_serial = get_device_serial(device_ids=settings['device_ids'], device_id=device_id)
    if not device_serial:
        return f"device {device_id} not found"
    data = {
        'data_url': f'/data/{device_id}',
        'data_reload': 5000
    }
    return render_template('device.html', data=data)


@app.route('/ajax', methods = ['POST'])
def ajax():
    data = request.json
    set_settings(data)
    return read_settings()

if __name__ == '__main__':
    if not Path(cfg_file).exists():
        write_settings({
            'data_root_dir': os.getenv('DATA_DIR', '../../data/raw/'),
            'today': datetime.now().strftime("%Y-%m-%d"),
            'session_start': '2024-05-02T09:29:00Z',
            'session_end': '2024-05-02T10:12:00Z',
            'device_ids': [
                {'serial': '3YK3K152F5', 'id': '735'},
                {'serial': '7WA2U178X5', 'id': '974'},
                {'serial': '4ZL4L263G6', 'id': '465'},
                {'serial': '4Y76BHY33Z', 'id': '370'},
            ],
            'highlights': []
        })
    print(read_settings())
    app.run(host='0.0.0.0', debug=True)
