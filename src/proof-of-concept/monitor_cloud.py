import argparse
import boto3
import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from pathlib import Path
from termcolor import colored

# https://manuals.empatica.com/ehmp/careportal/data_access/v2.5e/en.pdf
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html

class LowlandsFileMonitor:

    def __init__(self, cfg_file):
        with open(cfg_file) as f:
            cfg = json.load(f)

        s3_path = cfg['s3_path']
        my_aws_access_key_id = cfg['my_aws_access_key_id']
        my_aws_secret_access_key = cfg['my_aws_secret_access_key']
        bits = list(filter(None, s3_path.split("/")))
        bucket_name = bits[1]

        session = boto3.Session(
            aws_access_key_id = my_aws_access_key_id,
            aws_secret_access_key = my_aws_secret_access_key,
        )

        s3 = session.resource('s3')
        self.prefix = "/".join(bits[-2:])+"/"
        self.bucket = s3.Bucket(bucket_name)
        self.var_field = None
        plt.ion()
        plt.show()

    def get_objects(self):
        objects = []
        for my_bucket_object in self.bucket.objects.filter(Prefix=self.prefix):
            if my_bucket_object.key[-4:]==".csv":
                objects.append(my_bucket_object.key)

        return objects
    
    def set_source_file(self, source_file):
        self.source_file = source_file

    def set_local_file(self, local_file):
        self.local_file = local_file

    def download_file(self):
        self.bucket.download_file(self.source_file, self.local_file)

    def get_session(self, session_length=30, buffer_length=5, now=datetime.now(timezone.utc)):
        lines = []
        with open(self.local_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                b = datetime.strptime(row['timestamp_iso'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                if b > now - timedelta(minutes=session_length+buffer_length) and b < now - timedelta(minutes=buffer_length):
                    lines.append(row)
                    
        return lines

    def display_session(self, session):
        if len(session)==0:
            print("Empty session")
            return

        self.var_field = list(session[0].keys())[3]

        for line in session:
            val = f"{self.var_field}: {line[self.var_field]}" if len(line[self.var_field])>0 else line['missing_value_reason']
            print(f"{line['timestamp_iso']}: {val}")

    def plot_session(self, session):
        x_val = [datetime.strptime(x['timestamp_iso'][11:19], '%H:%M:%S').replace(tzinfo=timezone.utc) for x in session]
        y_val = [float(x[self.var_field]) if len(x[self.var_field])>0 else 0 for x in session]
        plt.clf()
        plt.title(self.var_field)
        plt.plot(x_val,y_val)
        plt.ylabel(self.var_field)
        plt.draw()
        plt.pause(0.1)

if __name__=="__main__":

    refresh_sec = 5
    session_length_min = 30
    buffer_length_min = 5
    cfg_file = os.getenv('CFG_FILE')
    local_data = '../../data/temp'
    mock_date = None
    select_date = None
    select_char = None
    wristband = None

    characteristics = ['accelerometers-std', 'actigraphy-counts', 'activity-classification',
                       'activity-counts', 'activity-intensity', 'body-position', 'eda', 'met', 'prv',
                       'pulse-rate', 'respiratory-rate', 'step-counts', 'temperature', 'wearing-detection']

    clear = lambda: os.system('clear')

    def parse_date(arg):
        return datetime.strptime(arg, '%Y-%m-%d').replace(tzinfo=timezone.utc)

    def parse_datetime(arg):
        return datetime.strptime(arg, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    def characteristic(arg):
        return characteristics[characteristics.index(arg)]

    parser=argparse.ArgumentParser()

    parser.add_argument('--wristband', type=str, help="Embrace S/N; looks like: 3YK3K152F5")
    parser.add_argument('--date', type=parse_date, help="Date to monitor; format: 2024-04-29")
    parser.add_argument('--characteristic', type=characteristic, help=f"Possible values: {', '.join(characteristics)}")
    parser.add_argument('--tardis', type=parse_datetime, help="Forced datetime; format: 2024-04-29T11:40:00Z")
    args=parser.parse_args()

    if args.date:
        select_date = args.date

    if args.characteristic:
        select_char = args.characteristic

    if args.wristband:
        wristband = args.wristband.upper()

    if args.tardis:
        mock_date = args.tardis

    lfm = LowlandsFileMonitor(cfg_file=cfg_file)

    if select_date and select_char and wristband:
        candidates = []
        for item in lfm.get_objects():
            if item.find(f"_{select_char}.csv")==-1:
                continue
            if item.find(wristband)==-1:
                continue
            if item.split("/")[5]!=select_date.strftime('%Y-%m-%d'):
                continue
            candidates.append(item)

        if len(candidates)==0:
            print(f"Combination of '{select_date}', '{select_char}' and '{wristband}' not found.")
            raise SystemExit

        source_file = list(sorted(candidates))[0]

    else:
        def print_objects(items, select_date, select_char, wristband):
            objects = []
            for item in items:
                if select_char and item.find(f"_{select_char}.csv")==-1:
                    continue
                if wristband and item.find(wristband)==-1:
                    continue
                if select_date and item.split("/")[5]!=select_date.strftime('%Y-%m-%d'):
                    continue
                objects.append((len(objects)+1, item))
            if len(objects)==0:
                print(f"No objects found.")
            for object in objects:
                i = object[0]
                print(colored(f"{i:2d}. {object[1]:144s} {i:2d}.", "white" if i%2==0 else "black", "on_black"  if i%2==0 else "on_light_grey"))
            return objects

        file = []
        id = None
        while len(file)==0:
            if id=='q':
                raise SystemExit
            if id is None or id=='r':
                clear()
                if select_date:
                    print(f"Date: {select_date.strftime('%Y-%m-%d')}")
                if select_char:
                    print(f"Characteristic: {select_char}")
                if wristband:
                    print(f"Wristband: {wristband}")
                objects = print_objects(lfm.get_objects(), select_date=select_date, select_char=select_char, wristband=wristband)
            id = input("File to monitor (r to refresh, q to quit): ")
            if id.isnumeric():
                file = [x[1] for x in objects if x[0] == int(id)]

        source_file = file[0]

    bits = source_file.split("/")
    participant = f"{bits[1]}-{bits[-1].split('_')[0]}"

    if not select_date:
        select_date = parse_date(bits[5])
    if not select_char:
        select_char = bits[-1].split("_")[-1][:-4]
    if not wristband:
        wristband = bits[6].split("-")[1]

    local_file = Path(local_data) / bits[-1]
    lfm.set_source_file(source_file)
    lfm.set_local_file(local_file)

    var_field = None
    just_now = datetime.now()

    while True:
        try:
            if mock_date is not None:
                the_now = mock_date
            else:
                the_now = datetime.now(timezone.utc)

            clear()

            print(f"+ monitoring: {source_file}")
            print(f"+ wristband: {wristband}")
            print(f"+ participant: {participant}")
            print(f"+ characteristic: {select_char}")
            print(f"+ date: {select_date.strftime('%Y-%m-%d')}")
            print(f"+ current_time: {colored(the_now, 'red') if the_now==mock_date else the_now} ({datetime.now()-just_now}s)")
            print(f"+ session_length: {session_length_min}m; buffer_length: {buffer_length_min}m")
            print(f"+ refresh: {refresh_sec}s")
            print(f"+ ctrl+c to break")
            print()

            lfm.download_file()
            session = lfm.get_session(now=the_now, session_length=session_length_min, buffer_length=buffer_length_min)
            lfm.display_session(session)
            lfm.plot_session(session)
            just_now = datetime.now()
            time.sleep(refresh_sec)
        except KeyboardInterrupt:
            print("Exited")
            raise SystemExit



