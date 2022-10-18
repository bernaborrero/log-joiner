import datetime
import gzip
import json
import os
import re
import shutil
import sys
import paramiko
import fnmatch

def read_config():
    file_path = 'config.json'
    with open(file_path, 'r') as f:
        return json.load(f)

def validate_option(input, modes):
    for mode in modes:
        if mode['name'] == input:
            return mode
    return False

def has_timestamp(line):
    if re.match(r'{}'.format(mode['date_regex']), line):
        return True
    return False

def log_chunker(log_lines):
    batch = []
    for line in log_lines:
        if batch and has_timestamp(line):
            # detected a new log statement, so yield the previous one
            yield batch
            batch = []
        batch.append(line)
    yield batch

def key_from_date(item):
    first_line = item[0]
    found = re.search(r'{}'.format(mode['date_regex']), first_line)
    date_raw = found.groups(1)[0]

    date = datetime.datetime.strptime(date_raw, mode['date_format']).replace(tzinfo=datetime.timezone.utc).timestamp()
    return date

def unzip_file(file_in, file_out):
    with gzip.open(file_in, 'rb') as f_in:
        with open(file_out, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


# Input args handling
try:
    arg = sys.argv[1]
except IndexError:
    raise SystemExit(f"Usage: {sys.argv[0]} <connection_name>")

config = read_config()

if arg in ['--help', '-h']:
    mode_names = [m['name'] for m in config['modes']]
    print(f"Usage: {sys.argv[0]} <connection_name>")
    raise SystemExit('Available modes: {}'.format(mode_names))

mode = validate_option(arg, config['modes'])
if not mode:
    raise SystemExit(f"Mode {arg} does not exist.")


# Iterate through connections to download logs
for conn in mode['ssh_connections']:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.connect(conn['domain'], username=conn['username'])
        print('SSH connection to: {}@{}'.format(conn['username'], conn['domain']))

        with client.open_sftp() as sftp:
            for filename in sftp.listdir(mode['remote_path']):

                # Download logs that match with pattern
                if fnmatch.fnmatch(filename, mode['file_pattern']):
                    print('Downloading {}'.format(filename))
                    local_filename = conn['number'] + '-' + filename
                    sftp.get(mode['remote_path'] + filename, mode['export_path'] + local_filename)

                    # Unzip logs if necessary
                    filename_sections = local_filename.split('.')
                    if filename_sections[-1] == 'gz':
                        print('Unzipping {}'.format(local_filename))
                        filename_sections.pop()
                        filename_clean = '.'.join(filename_sections)
                        unzip_file(mode['export_path'] + local_filename, mode['export_path'] + filename_clean)
                        os.unlink(mode['export_path'] + local_filename)

# Join all logs
contents = []
local_files = [f for f in os.listdir(mode['export_path']) if re.match('\d+-{}'.format(mode['file_pattern']), f)]
if not local_files:
    raise SystemExit('No logs found in remotes with path {}{}'.format(mode['remote_path'], mode['file_pattern']))

for local_file in local_files:
    with open(mode['export_path'] + local_file, 'r', encoding='utf8') as f:
        contents.extend(f.readlines())
    os.unlink(mode['export_path'] + local_file)

# Sort logs
print('Ordering logs...')
chunker = log_chunker(contents)
ordered = sorted(chunker, key=key_from_date)

# Write to output file
print('Writing to output file: {}{}'.format(mode['export_path'], mode['export_filename']))
log_lines_counter = 0
with open(mode['export_path'] + mode['export_filename'], 'w', encoding='utf8') as f:
    for line in ordered:
        for item in line:
            f.write(item)
            log_lines_counter = log_lines_counter + 1

file_size = os.stat(mode['export_path'] + mode['export_filename'])
file_size_mb = file_size.st_size / (1024 * 1024)
print('Done!')
print('Stats:\n-----------------------\nLog lines saved: {}\nFile size: {} MB'.format(log_lines_counter, file_size_mb))
