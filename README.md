# Smartwatch aggregate monitor

Program designed to harvest aggregated biomarker data collected from EmbracePlus wearables via an instance of Empatica's Care Portal, and display them as simple time series graphs.

## Usage

### Prerequisites

The Empatica Care Portal writes data to an AWS S3 bucket. In order to download the data, you require credentials for accessing the bucket. You need three pieces of information, which are provided by Empatica as part of a license:

+ s3_path
+ my_aws_access_key_id
+ my_aws_secret_access_key

Store these as key-value pairs in a JSON-file (for instance `aws_config.json`) and set its path as an environment variable `AWS_CFG_FILE`. Next, create a folder to hold the downloaded data, and set its path as an environment variable as well (if you omit this, the program will default to the `/data/raw` folder of this repo).


```bash
export AWS_CFG_FILE='/path/to/aws_config.json'
export DATA_DIR='/path/to/data'
```

### Harvest data

Run 
```bash
python src/data-retrieval/get_data.py
```
to harvest data.  Options:

+ To retrieve files for today: `python get_data.py`
+ To retrieve files for a specific date: `python get_data.py <YYYY-MM-DD>`
+ For a list of available .CSV-files: `python get_data.py show-all`

Ideally, this process is scheduled so the 




Run `webserver/webserver.py` to present data. 

## License

This project is licensed under the terms of the [MIT License](/LICENSE).
