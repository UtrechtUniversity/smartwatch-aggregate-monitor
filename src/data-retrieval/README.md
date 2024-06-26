# Data retrieval

Program designed to harvest aggregated biomarker data collected from EmbracePlus wearables via an instance of Empatica's Care Portal.

## Prerequisites

### Requirements
To install requirements:

```bash
pip install -r ../../requirements.txt
```

### Variables

The Empatica Care Portal writes data to an AWS S3 bucket. In order to download the data, you require credentials for accessing the bucket. You need three pieces of information, which are provided by Empatica as part of a license:

+ s3_path
+ my_aws_access_key_id
+ my_aws_secret_access_key

Store these as key-value pairs in a JSON-file (for instance `aws_config.json`) and set its path as an environment variable `AWS_CFG_FILE`. Next, create a folder to hold the downloaded data, and set its path as an environment variable as well (if you omit this, the program will default to the `/data/raw` folder of this repo).


```bash
export AWS_CFG_FILE='/path/to/aws_config.json'
export DATA_DIR='/path/to/data'
```

## Running

Run 
```bash
python src/data-retrieval/get_data.py
```
to harvest data. Options:

+ To retrieve files for today: `python get_data.py`
+ To retrieve files for a specific date: `python get_data.py <YYYY-MM-DD>`
+ For a list of available .CSV-files: `python get_data.py show-all`

The program downloads all CSV-files with biometric for all devices that are available for a given date. When an EmbracePlus is activated, it starts sending back data to the portal, even if it's not worn. Once the portal has received data for a specific device, it aggregates the data over one-minute periods, and writes the data to the S3 bucket (how often this is done is unclear, but it seems every 5 mimutes or so). This results in fourteen files per day per device, one for each measured variable. Each file always contains data for the entire day, even if that day is not over yet, in which aggregates of timeperiods still to come are being presented with the error label 'device_not_recording'. 

Ideally, the program is scheduled over short intervals (say 5 or less minutes), to keep the data reasonably up to date.


## License

This project is licensed under the terms of the [MIT License](/LICENSE).
