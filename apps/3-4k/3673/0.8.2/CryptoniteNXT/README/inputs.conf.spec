
# Listen on plain TCP
[tcp://8514]
connection_host = ip
# Use own index
index=cryptonitenxt
# The source type must be set to 
sourcetype = Cryptonite:CryptoniteNXT
# The input port must listen on IPv6
listenOnIPv6 = only

# -OR-
[tcp-ssl://8514]
connection_host = ip
index=cryptonitenxt
# The source type must be set to 
sourcetype = Cryptonite:CryptoniteNXT
# The input port must listen on IPv6
listenOnIPv6 = only

