import json

from server.constants import paths

def read_file(file_path):
    def wrapper():
        with file_path.open() as file:
            return json.load(file)
    return wrapper


read_devices = read_file(paths.DEVICES_FILE_PATH)
read_clusters = read_file(paths.CLUSTERS_FILE_PATH)
read_gateways = read_file(paths.GATEWAYS_FILE_PATH)

def write_file(file_path):
    def wrapper(data_to_write):
        with file_path.open(mode='w') as file:
            json.dump(data_to_write, file, indent=4,
                       skipkeys=True, sort_keys=True, ensure_ascii=True)
    return wrapper


write_devices = write_file(paths.DEVICES_FILE_PATH)
write_clusters = write_file(paths.CLUSTERS_FILE_PATH)
write_gateways = write_file(paths.GATEWAYS_FILE_PATH)
