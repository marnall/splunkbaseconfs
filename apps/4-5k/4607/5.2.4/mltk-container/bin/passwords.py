import splunklib
import random
import hashlib

# config password.conf
password_fields = set([
    "client_key",
    "user_token",
    "user_password",
    "aws_secret_access_key",
    "jupyter_passwd"
])

llm_password_fields = set([
    "llm_azure_api_key",
    "llm_openai_api_key",
    "llm_gemini_api_key",
    "llm_bedrock_aws_access_key_id",
    "llm_bedrock_aws_secret_access_key",
    "llm_bedrock_aws_session_token",
    "emb_azure_api_key",
    "emb_openai_api_key",
    "emb_gemini_api_key",
    "emb_bedrock_aws_access_key_id",
    "emb_bedrock_aws_secret_access_key",
    "emb_bedrock_aws_session_token",
    "vec_milvus_token",
    "vec_pinecone_api_key",
    "vec_alloydb_password",
    "gra_neo4j_password",
    "gra_dgraph_password",
    "mcp_token_1",
    "mcp_token_2",
    "mcp_token_3",
    "mcp_token_4",
    "mcp_token_5",
])

passwords_realm = "dltk_kubernetes"
llm_passwords_realm = "dltk_llm"


def decode_passwords(service, settings):
    for field_name in password_fields:
        username = field_name
        storage_password_name = splunklib.binding.UrlEncoded(passwords_realm, encode_slash=True) + ":" + splunklib.binding.UrlEncoded(username, encode_slash=True)
        if storage_password_name in service.storage_passwords:
            try:
                storage_password = service.storage_passwords[storage_password_name]
                settings.content[field_name] = storage_password.clear_password
            except:
                pass

def encode_passwords(service, settings):
    for field_name in password_fields:
        if field_name in settings:
            password = settings[field_name]
            del settings[field_name]
        else:
            password = ""
        username = field_name
        realm = passwords_realm
        storage_password_name = splunklib.binding.UrlEncoded(realm, encode_slash=True) + ":" + splunklib.binding.UrlEncoded(username, encode_slash=True)
        if storage_password_name in service.storage_passwords:
            storage_password = service.storage_passwords[storage_password_name]
        else:
            storage_password = None
        if password:
            if storage_password:
                if storage_password.clear_password != password:
                    service.storage_passwords.delete(username, realm)
                    storage_password = service.storage_passwords.create(password, username, realm)
            else:
                storage_password = service.storage_passwords.create(password, username, realm)
        else:
            if storage_password:
                service.storage_passwords.delete(username, realm)

        # Enable password change: generate jupyter lab compatible password out of the given clear_password and save the hash in
        # additional config setting that can be used as ENV variable for container start to reflect custom password for Jupyter Lab
        if field_name == "jupyter_passwd":
            if storage_password_name in service.storage_passwords:
                passphrase = service.storage_passwords[storage_password_name].clear_password
                salt_len = 12
                algorithm = "sha512"

                def encode(u, encoding=None):
                    encoding = encoding or "utf-8"
                    return u.encode(encoding, "replace")

                def cast_bytes(s, encoding=None):
                    if not isinstance(s, bytes):
                        return encode(s, encoding)
                    return s
                h = hashlib.new(algorithm)
                salt = f"{random.getrandbits(4 * salt_len):0{salt_len}x}"
                h.update(cast_bytes(passphrase, 'utf-8') + encode(salt, 'ascii'))
                hashed_pwd = ':'.join((algorithm, salt, h.hexdigest()))
                # self.get_logger().info("jupyter_passwd_hashed : %s", hashed_pwd)
                settings["jupyter_passwd"] = hashed_pwd
            else:
                settings["jupyter_passwd"] = ""

def decode_llm_passwords(service, settings):
    for field_name in llm_password_fields:
        username = field_name
        storage_password_name = splunklib.binding.UrlEncoded(llm_passwords_realm, encode_slash=True) + ":" + splunklib.binding.UrlEncoded(username, encode_slash=True)
        if storage_password_name in service.storage_passwords:
            try:
                storage_password = service.storage_passwords[storage_password_name]
                settings.content[field_name] = storage_password.clear_password
            except:
                pass

def encode_llm_passwords(service, settings):
    for field_name in llm_password_fields:
        if field_name in settings:
            password = settings[field_name]
            del settings[field_name]
        else:
            password = ""
        username = field_name
        realm = llm_passwords_realm
        storage_password_name = splunklib.binding.UrlEncoded(realm, encode_slash=True) + ":" + splunklib.binding.UrlEncoded(username, encode_slash=True)
        if storage_password_name in service.storage_passwords:
            storage_password = service.storage_passwords[storage_password_name]
        else:
            storage_password = None
        if password:
            if storage_password:
                if storage_password.clear_password != password:
                    service.storage_passwords.delete(username, realm)
                    storage_password = service.storage_passwords.create(password, username, realm)
            else:
                storage_password = service.storage_passwords.create(password, username, realm)
        else:
            if storage_password:
                service.storage_passwords.delete(username, realm)
