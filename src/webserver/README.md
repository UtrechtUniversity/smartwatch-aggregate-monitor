# Web server

Program designed to display aggregated biomarker data.

## Prerequisites

### Requirements
To install requirements:

```bash
pip install -r ../../requirements.txt
```

### Devices

Register all the EmbracePlus-devices that are part of the experiment in a JSON-file. Register the serial number (found on the box and the back of the device), an ID (will be part of the URL for accessing the graphs; can be anything as long as they're unique), and a password for accessing the page. Store it in a file `devices.json`. Example:

```json
{
    "devices":[
        {"serial": "3YK3K152F5", "id": "123", "password": "pass_1"},
        {"serial": "9HD0NG7ESH", "id": "456", "password": "pass_2"},
    ]
}
```

### Variables


```bash
export DATA_DIR=/data/lowlands/data
export CFG_FILE=/data/lowlands/config/config.json;
export DEVICES_FILE=/data/lowlands/devices.json
export ADMIN_PASS=<password>
export DEBUG=1
 ```

## Running

Run 
```bash
python src/webserver/webserver.py
```

## License

This project is licensed under the terms of the [MIT License](/LICENSE).
