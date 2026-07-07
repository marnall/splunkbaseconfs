import ipaddress

def is_valid_ip(ip):
  try:
    ipaddress.ip_address(ip)
    return True
  except ValueError:
    return False

def is_valid_cidr(network):
  try:
    ipaddress.ip_network(network)
    return True
  except ValueError:
    return False