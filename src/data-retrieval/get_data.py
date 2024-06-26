import argparse
import boto3
import json
from datetime import datetime, timezone
from pathlib import Path

class CarePortalDataDownloader:

    def __init__(self, 
                 aws_cfg_file,
                 data_dir,
                 monitor_date = None):

        with open(aws_cfg_file) as f:
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

        if monitor_date is None:
            self.monitor_date = datetime.now().strftime("%Y-%m-%d")
        else:
            self.monitor_date = monitor_date


        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if self.monitor_date=='*':
            for file in self.get_csv_objects():
                print(file)
        else:
            print(f"Files for {self.monitor_date}")
            self.download_objects()

    def get_csv_objects(self):
        objects = []
        for my_bucket_object in self.bucket.objects.filter(Prefix=self.prefix):
            if my_bucket_object.key[-4:]==".csv" and \
                (self.monitor_date=='*' or my_bucket_object.key.split("/")[5]==self.monitor_date):
                objects.append(my_bucket_object.key)

        return objects

    def download_objects(self):
        objects = self.get_csv_objects()
        for object in objects:
            bits = object.split("/")
            local_folder = self.data_dir / Path(bits[5]) / Path(bits[6].split('-')[1])
            local_folder.mkdir(parents=True, exist_ok=True)
            local_file = local_folder / Path(bits[9])
            try:
                self.bucket.download_file(object, local_file)
                print(f"Downloaded '{local_file}'")
            except Exception as e:
                print(f"Download failed: {object} ({str(e)})")

if __name__=="__main__":

    parser=argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='Retrieve for this date. Format: <YYYY-MM-DD> or show-all; leave empty for today')
    parser.add_argument('--aws-cfg-path', type=str, required=True, help='Path of AWS config file')
    parser.add_argument('--data-dir', type=str, required=True, help='Path of root folder for downloading data')
    args=parser.parse_args()

    aws_cfg_file = args.aws_cfg_path
    data_dir = args.data_dir

    monitor_date = None

    if args.date=='show-all':
        monitor_date = '*'
    elif args.date:
        monitor_date = datetime.strptime(args.date, '%Y-%m-%d').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d')

    cpd = CarePortalDataDownloader(
        aws_cfg_file=aws_cfg_file, 
        data_dir=data_dir,
        monitor_date=monitor_date)

    # export AWS_CFG_FILE='/root/aws_config.json'
    # export DATA_DIR='/data/lowlands'
