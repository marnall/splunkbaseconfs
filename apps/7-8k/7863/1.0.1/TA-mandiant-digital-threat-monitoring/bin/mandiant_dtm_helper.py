"""Helper functions for Mandiant DTM."""


def build_proxy_config(proxies: dict) -> dict:
  proxy_type = proxies.get('proxy_type')
  proxy_url = proxies.get('proxy_url')
  proxy_port = proxies.get('proxy_port')
  proxy_user = proxies.get('proxy_username')
  proxy_pass = proxies.get('proxy_password')

  if not proxy_user:
    proxy_str = f'{proxy_type}://{proxy_url}:{proxy_port}'
  else:
    proxy_str = (
        f'{proxy_type}://{proxy_user}:{proxy_pass}@{proxy_url}:{proxy_port}'
    )

  return {'http': proxy_str, 'https': proxy_str}
