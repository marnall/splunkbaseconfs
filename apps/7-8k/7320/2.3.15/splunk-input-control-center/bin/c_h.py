from n_f import n_f_a
from t_f import o_t

def c_c(key, k, m_k, c_t, k_t, s, a_d_s, v_b):

    try:
        if (int(s) + int(a_d_s) != int(v_b)) or (len(k) != 32 or m_k):
            return n_f_a("501")
        else:
            if key[-1:] == '0':
                if (c_t - int(k_t)) > o_t():
                    return  n_f_a("502")
                else:
                    pass
            elif key[-1:] == '1':
                if (c_t - int(k_t)) > 31536000:
                    return  n_f_a("503")
                else:  
                    pass
            elif key[-1:] == '2':
                if (c_t - int(k_t)) > 86400:
                    return "Activation Key is mismatched"
                else:
                    pass

    except Exception:
        return n_f_a("504")
    return None