# Configuration specification for ThreatBook API application

[config]
# ThreatBook API 应用配置参数

# Splunk 基础连接配置
search_head_url = <string>
* Splunk Search Head URL
* 格式: host:port 或 host1:port1;host2:port2
* 示例: 192.168.100.91:8089

token = <string>
* Splunk REST API Token
* 用于连接 Splunk 服务的认证令牌

index_master_url = <string>
* Splunk Index Master URL
* 格式: host:port
* 示例: 192.168.100.91:8088

hec_token = <string>
* Splunk HEC (HTTP Event Collector) Token
* 用于发送数据到 Splunk

# IP情报配置
ip_intelligence_url = <string>
* IP情报API接口地址
* 示例: http://192.168.100.91:8090

ip_intelligence_config = <string>
* IP情报配置JSON字符串
* 包含API密钥、数据源配置等信息

# 域名情报配置
domain_intelligence_url = <string>
* 域名情报API接口地址
* 示例: http://192.168.100.91:8090

domain_intelligence_config = <string>
* 域名情报配置JSON字符串
* 包含API密钥、数据源配置等信息

# 文件情报配置
file_intelligence_url = <string>
* 文件情报API接口地址
* 示例: http://192.168.100.91:8090

file_intelligence_config = <string>
* 文件情报配置JSON字符串
* 包含API密钥、数据源配置等信息

# 代理配置
proxyEnabled = <boolean>
* Enable or disable proxy for all outbound API requests
* Default: true

proxyType = <string>
* Proxy protocol type
* Supported values: HTTP, HTTPS, SOCKS4, SOCKS5
* HTTP: Standard HTTP proxy (client-to-proxy connection uses HTTP)
* HTTPS: HTTPS proxy (client-to-proxy connection uses HTTPS, less common)
* SOCKS4: SOCKS4 protocol
* SOCKS5: SOCKS5 protocol
* Default: HTTP

proxyHost = <string>
* Proxy server hostname or IP address (without protocol prefix)
* Examples: 192.168.1.1, proxy.example.com
* Note: Do NOT include protocol (http://, https://, etc.)
* Required if proxyEnabled is true

proxyPort = <integer>
* Proxy server port number
* Valid range: 1-65535
* Example: 8080, 1080
* Required if proxyEnabled is true

proxyUsername = <string>
* Proxy authentication username (optional)
* Maximum length: 100 characters
* Default: empty

proxyPassword = <string>
* Proxy authentication password (optional)
* Maximum length: 100 characters
* Note: Stored in plain text
* Default: empty

proxyRemoteDNS = <boolean>
* Perform DNS resolution on the proxy server (SOCKS5 only)
* When enabled, DNS lookup is performed by the proxy server instead of locally
* Recommended for SOCKS5 to prevent DNS leaks
* Default: false
