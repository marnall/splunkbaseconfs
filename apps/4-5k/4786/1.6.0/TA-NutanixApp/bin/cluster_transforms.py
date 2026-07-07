

def clusterstatistics(starttime,json_data):
    data_keys = ['controller_num_iops','controller_io_bandwidth_kBps','controller_avg_io_latency_usecs','time_start']
    list_data = [x['values'] for x in json_data]
    data_zip = zip(*list_data)
    list_of_lists = [list(item) for item in data_zip]
    length = 0
    while length < len(list_of_lists):
        for element in list_of_lists:
            element.append(starttime)
            starttime = int(starttime + 60000000)
            length = length +1
    final_data = [dict(zip(data_keys,tup)) for tup in list_of_lists]
    yield final_data
            
            
            
            
if __name__ == '__main__':
    clusterstatistics(starttime,json_data)