import re

from pydantic import BaseModel, Field, field_validator, model_validator


class UpdateIntegration(BaseModel):
    """Pydantic model for validating integration POST requests"""

    device_name: str = Field(..., min_length=30, max_length=128)
    auth_endpoint: str = Field(..., min_length=45, max_length=128)
    api_endpoint: str = Field(..., min_length=10, max_length=128)
    api_region: str = Field(..., min_length=9, max_length=25)
    index_name: str = Field(default='main', max_length=64)
    services_filter: str = Field(default='All')
    initial_minutes_back_start: int = Field(default=15, ge=15, le=60)
    page_size: int = Field(default=500, ge=100, le=1000)
    integration_display_name: str = Field(default='')
    host: str = Field(default='$decideOnStartup')
    sourcetype: str = Field(default='cyberark:audit')

    @field_validator('device_name')
    @classmethod
    def validate_device_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('device_name contains invalid characters. Use only alphanumeric, underscores, hyphens, and brackets.')
        return v

    @field_validator('api_endpoint')
    @classmethod
    def validate_api_endpoint(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith('https://'):
            raise ValueError('api_endpoint must start with https://')
        if re.search(r'[\s\x00-\x1f\x7f]', v):
            raise ValueError('api_endpoint contains invalid characters')
        return v

    @field_validator('auth_endpoint')
    @classmethod
    def validate_auth_endpoint(cls, v: str) -> str:
        v = v.strip()
        if re.search(r'[\s\x00-\x1f\x7f]', v):
            raise ValueError('auth_endpoint contains invalid characters')
        if not re.match(r'^[a-z0-9\-]+\.credentials\.iot\.[a-z0-9\-]+\.amazonaws\.com$', v):
            raise ValueError(
                'auth_endpoint must be a valid AWS IoT credentials endpoint (e.g., <id>.credentials.iot.<region>.amazonaws.com)')
        return v

    @field_validator('api_region')
    @classmethod
    def validate_api_region(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-z0-9\-]+$', v):
            raise ValueError('api_region contains invalid characters')
        return v

    @field_validator('index_name')
    @classmethod
    def validate_index_name(cls, v: str) -> str:
        v = v.strip().lower()
        if v and not re.match(r'^[a-z0-9_\-]+$', v):
            raise ValueError('Invalid index name. Use only lowercase letters, numbers, underscores, and hyphens.')
        return v or 'main'


class IntegrationRequest(UpdateIntegration):
    certificate: str = Field(..., min_length=100)
    private_key: str = Field(..., min_length=100)

    @field_validator('certificate', 'private_key')
    @classmethod
    def validate_credentials(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Certificate and private key are required')
        return v


class ProxyUpdateRequest(BaseModel):
    proxy_enabled: bool = Field(default=False)
    proxy_host: str = Field(default=None)
    proxy_port: int = Field(default=None)
    proxy_username: str = Field(default=None)
    proxy_password: str = Field(default=None)
    proxy_verify_ssl: bool = Field(default=True)

    @field_validator('proxy_host')
    @classmethod
    def validate_proxy_host(cls, v):
        if v is not None:
            v = v.strip()
            if not re.match(r'^[a-zA-Z0-9.\-]+$', v):
                raise ValueError('proxy_host must be a valid hostname or IP address')
            if len(v) > 253:
                raise ValueError('proxy_host exceeds maximum length')
        return v

    @field_validator('proxy_port')
    @classmethod
    def validate_proxy_port(cls, v):
        if v is not None and (v < 1 or v > 65535):
            raise ValueError('Proxy port must be between 1 and 65535')
        return v

    @model_validator(mode='after')
    def validate_proxy_fields(self):
        if self.proxy_enabled:
            if not self.proxy_host:
                raise ValueError('Proxy host is required when proxy is enabled')
            if not self.proxy_port:
                raise ValueError('Proxy port is required when proxy is enabled')

        has_username = bool(self.proxy_username)
        has_password = bool(self.proxy_password)
        if has_username != has_password:
            raise ValueError('Please provide both username and password, or leave both empty to use proxy without authentication')

        return self
