import re as r
import hashlib as h

def g_k_t_r(key):
    key = key[:-1]
    k_t = key[-10:][::-1]
    m_k = r.search('[a-zA-Z]', k_t)
    return k_t, m_k

def c_s(d_v):
    return sum([int(x) for x in str(int(d_v))])

def o_a(a_n, k):
    k_t, m_k = g_k_t_r(k)
    a_md = h.md5(a_n.encode('utf-8')).hexdigest().upper()
    return k_t, m_k, a_md

def o_b(a_md, k):
    a_d = int(a_md, 16)
    a_d_s = c_s(a_d)
    k = k[:-1]
    k = k[:-10]
    v_b = k[:-32]
    k = k[-32:]
    return a_d_s, k, v_b

def o_c(k, t):
    d = int(k, 16)
    l = [int(x) for x in str(int(d))]
    s = sum(list(l))
    c_t = t.time()
    return s, c_t
