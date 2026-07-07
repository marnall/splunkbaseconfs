def CSVtoDict(csv_s):
    event_list = []
    if csv_s:
        csv_l = csv_s.split("\r\n")
        if len(csv_l[0]) > 1:
            csv_h = csv_l[0].split(",")
        else:
            return event_list

    for x in range(1,len(csv_l)):
        event = {}
        for y in range(0,len(csv_h)):
            csv_l_v = csv_l[x].split(",")
            key = csv_h[y].strip('\"')
            val = csv_l_v[y].strip('\"')
            event[f'{key}'] = val
        
        event_list.append(event)

    return event_list

