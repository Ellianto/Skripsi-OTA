from server.internal_handlers import file_io

def item_getter(file_reader):
    def wrapper(item_id):
        items = file_reader()
        return next((item for item in items['data'] if item['id'] == item_id), None)
    return wrapper

get_device  = item_getter(file_io.read_devices)
get_cluster = item_getter(file_io.read_clusters)
get_gateway = item_getter(file_io.read_gateways)

def find_index(items, item_id):
    return next((idx for idx, item in enumerate(items['data']) if item['id'] == item_id), None)