import time as t
from h_f import g_k_t_r, c_s, o_a, o_b, o_c
from c_h import c_c

class A_V:
    def __init__(self, a_n, k):
        self.a_n = a_n
        self.k = k

    def v_a_k(self):
        k_t, m_k, a_md = o_a(self.a_n, self.k)
        a_d_s, k, v_b = o_b(a_md, self.k)
        s, c_t = o_c(k, t)
        result = c_c(self.k, k, m_k, c_t, k_t, s, a_d_s, v_b) 
        if result:
            return result
        return None