import csv
import os
import statistics
from datetime import datetime, timezone
from flask import Flask
from pathlib import Path
from statistics import fmean

app = Flask(__name__)

data_root_dir = os.getenv('DATA_DIR', '/data/lowlands')
monitor_date = os.getenv('MONITOR_DATE', datetime.now().strftime("%Y-%m-%d"))
session_start = '2024-05-02T09:29:00Z'
session_end = '2024-05-02T10:12:00Z'

device_ids = [
    {'serial': '3YK3K152F5', 'id': '123'},
    {'serial': '7WA2U178X5', 'id': '342'},
    {'serial': '4ZL4L263G6', 'id': '579'},
    {'serial': '4Y76BHY33Z', 'id': '199'},
]

# session_length_min = 30
# buffer_length_min = 5
# the_now = datetime.now(timezone.utc)

print(data_root_dir)
print(monitor_date)
print(session_start)
print(session_end)
print(device_ids)

def get_device_serial(device_id):
    device = [x for x in device_ids if x['id']==device_id]
    if len(device)!=1:
        return
    return device[0]['serial']

class DeviceSessionData:

    # [(var name, column header), ... ]
    characteristics = [('eda', 'eda_scl_usiemens'), ('pulse-rate', 'pulse_rate_bpm')]

    def __init__(self,
                 data_root_dir,
                 monitor_date,
                 device=None,
                 session_start=None,
                 session_end=None) -> None:
        self.data_dir = Path(data_root_dir) / Path(monitor_date)
        self.device = device
        if session_start and session_end:
            self.session_data = self.retrieve_session_data(
                devices=self.get_devices(data_dir=self.data_dir),
                chars=self.characteristics,
                session_start=self.to_timestamp(session_start), 
                session_end=self.to_timestamp(session_end))
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

    def retrieve_session_data(self, devices, chars, session_start, session_end):
        s_data = {}
        for device in devices:
            s_data[device] = {}
            for char in chars:
                d_data = self.get_device_data(device=device, char=char)
                s_data[device][char[0]] = [x for x in d_data if x['timestamp'] >= session_start and x['timestamp'] <= session_end]
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

        for key in averages.copy():
            averages[key] = [{'timestamp': x['timestamp'], 'val': fmean(ts['val'])} for x in averages[key]]
        
        return averages


    def get_session_data(self, device=None):
        if device:
            return { 'data': self.session_data[device], 'averages': self.session_averages } 
        return { 'data': self.session_data, 'averages': self.session_averages } 

@app.route('/')
def root():
    dsd = DeviceSessionData(
        data_root_dir = data_root_dir,
        monitor_date = monitor_date,
        session_start = session_start,
        session_end = session_end
    )
    return dsd.get_session_data()

@app.route('/device/<device_id>')
@app.route('/device/<device_id>/')
def device(device_id):
    device_serial = get_device_serial(device_id)
    if not device_serial:
        return f"device {device_id} not found"

    dsd = DeviceSessionData(
        data_root_dir = data_root_dir,
        monitor_date = monitor_date,
        session_start = session_start,
        session_end = session_end
    )

    return dsd.get_session_data(device=device_serial)

@app.route('/devices')
def devices():
    dsd = DeviceSessionData(
        data_root_dir = data_root_dir,
        monitor_date = monitor_date
    )
    return {'devices_with_data': dsd.get_devices(dsd.data_dir), 'device_ids': device_ids}

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


# if x['timestamp'] > datetime.now(timezone.utc) - timedelta(minutes=session_length+buffer_length) and b < now - timedelta(minutes=buffer_length) ]