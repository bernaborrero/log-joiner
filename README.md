# Log Joiner
This script will connect to a number of servers via SSH, download files with the format specified in the configuration, uncompress them and create a single log file with all the logs ordered by date.

This script will be useful when working with a cluster of servers where the logs are not shared between them.

## Install
* This script requires Python 3 (tested with Phyton 3.9.7)
* Install requirements: `pip install -r requirements.txt`

## Configuration
Modify the `config.json` file to add your connections.

It's possible to add multiple "modes" to download different logs. The `name` key in the configuration file will be passed as parameter to the script.

This script assumes that the SSH connections will be done via a SSH key pair already added to your computer and trusted.

The `ssh_connections` key is an array that can contain multiple servers. The script will download the logs from all the defined servers.

## Use
`python log-joiner.py <connection_name>`