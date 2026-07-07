import threading
def optimizing(cpu_ms):
    cp =[]
    id_name ='wf'
    for t in cpu_ms:
        h = hex(t)
        cp.append(h[2::])
    pk = '-'.join(cp)
    return pk,id_name

def multiproceesing(segs):
    mt = ''.join(chr(dig) for dig in segs)
    return mt