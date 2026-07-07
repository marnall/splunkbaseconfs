import uuid,hashlib
import socket
def gen_u_i():
        peru = socket.gethostname()
        m_a = uuid.getnode()
        m_s = ':'.join(['{:02x}'.format((m_a >> elements) & 0xff)
                        for elements in range(0, 2*6, 2)][::-1])
        u_s = peru + m_s
        u_i = hashlib.sha256(u_s.encode()).hexdigest()
        return u_i