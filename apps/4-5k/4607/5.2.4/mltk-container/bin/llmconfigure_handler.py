import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
import splunk
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
# TODO: don't import kubernetes_fields here, add a function to K8SUtils to get just the K8S specific fields
from kubernetes_utility import K8SUtils, kubernetes_fields
from passwords import encode_llm_passwords, decode_llm_passwords

import exceptions


class LlmconfigureHandler(BaseRestHandler):
    def handle_POST(self):
        try:
            params = parse_qs(self.request['payload'])
            llm_ollama_is_configured = params["llm_ollama_is_configured"][0] if "llm_ollama_is_configured" in params else ''
            llm_azure_is_configured = params["llm_azure_is_configured"][0] if "llm_azure_is_configured" in params else ''
            llm_openai_is_configured = params["llm_openai_is_configured"][0] if "llm_openai_is_configured" in params else ''
            llm_bedrock_is_configured = params["llm_bedrock_is_configured"][0] if "llm_bedrock_is_configured" in params else ''
            llm_gemini_is_configured = params["llm_gemini_is_configured"][0] if "llm_gemini_is_configured" in params else ''
            llm_ollama_model = params["llm_ollama_model"][0] if "llm_ollama_model" in params else ''
            llm_azure_model = params["llm_azure_model"][0] if "llm_azure_model" in params else ''
            llm_openai_model = params["llm_openai_model"][0] if "llm_openai_model" in params else ''
            llm_bedrock_model = params["llm_bedrock_model"][0] if "llm_bedrock_model" in params else ''
            llm_gemini_model = params["llm_gemini_model"][0] if "llm_gemini_model" in params else ''
            llm_ollama_base_url = params["llm_ollama_base_url"][0] if "llm_ollama_base_url" in params else ''
            llm_azure_deployment_name = params["llm_azure_deployment_name"][0] if "llm_azure_deployment_name" in params else ''
            llm_openai_api_key = params["llm_openai_api_key"][0] if "llm_openai_api_key" in params else ''
            llm_azure_api_key = params["llm_azure_api_key"][0] if "llm_azure_api_key" in params else ''
            llm_gemini_api_key = params["llm_gemini_api_key"][0] if "llm_gemini_api_key" in params else ''
            llm_azure_endpoint = params["llm_azure_endpoint"][0] if "llm_azure_endpoint" in params else ''
            llm_azure_api_version = params["llm_azure_api_version"][0] if "llm_azure_api_version" in params else ''
            llm_bedrock_aws_access_key_id = params["llm_bedrock_aws_access_key_id"][0] if "llm_bedrock_aws_access_key_id" in params else ''
            llm_bedrock_aws_secret_access_key = params["llm_bedrock_aws_secret_access_key"][0] if "llm_bedrock_aws_secret_access_key" in params else ''
            llm_bedrock_aws_session_token = params["llm_bedrock_aws_session_token"][0] if "llm_bedrock_aws_session_token" in params else ''
            llm_bedrock_region_name = params["llm_bedrock_region_name"][0] if "llm_bedrock_region_name" in params else ''
            emb_hf_is_configured = params["emb_hf_is_configured"][0] if "emb_hf_is_configured" in params else ''
            emb_ollama_is_configured = params["emb_ollama_is_configured"][0] if "emb_ollama_is_configured" in params else ''
            emb_azure_is_configured = params["emb_azure_is_configured"][0] if "emb_azure_is_configured" in params else ''
            emb_openai_is_configured = params["emb_openai_is_configured"][0] if "emb_openai_is_configured" in params else ''
            emb_bedrock_is_configured = params["emb_bedrock_is_configured"][0] if "emb_bedrock_is_configured" in params else ''
            emb_gemini_is_configured = params["emb_gemini_is_configured"][0] if "emb_gemini_is_configured" in params else ''
            emb_hf_model_name = params["emb_hf_model_name"][0] if "emb_hf_model_name" in params else ''
            emb_ollama_model_name = params["emb_ollama_model_name"][0] if "emb_ollama_model_name" in params else ''
            emb_azure_model = params["emb_azure_model"][0] if "emb_azure_model" in params else ''
            emb_openai_model = params["emb_openai_model"][0] if "emb_openai_model" in params else ''
            emb_bedrock_model_name = params["emb_bedrock_model_name"][0] if "emb_bedrock_model_name" in params else ''
            emb_gemini_model_name = params["emb_gemini_model_name"][0] if "emb_gemini_model_name" in params else ''
            emb_hf_output_dims = params["emb_hf_output_dims"][0] if "emb_hf_output_dims" in params else ''
            emb_ollama_output_dims = params["emb_ollama_output_dims"][0] if "emb_ollama_output_dims" in params else ''
            emb_azure_output_dims = params["emb_azure_output_dims"][0] if "emb_azure_output_dims" in params else ''
            emb_openai_output_dims = params["emb_openai_output_dims"][0] if "emb_openai_output_dims" in params else ''
            emb_bedrock_output_dims = params["emb_bedrock_output_dims"][0] if "emb_bedrock_output_dims" in params else ''
            emb_gemini_output_dims = params["emb_gemini_output_dims"][0] if "emb_gemini_output_dims" in params else ''
            emb_ollama_base_url = params["emb_ollama_base_url"][0] if "emb_ollama_base_url" in params else ''
            emb_azure_deployment_name = params["emb_azure_deployment_name"][0] if "emb_azure_deployment_name" in params else ''
            emb_azure_api_key = params["emb_azure_api_key"][0] if "emb_azure_api_key" in params else ''
            emb_gemini_api_key = params["emb_gemini_api_key"][0] if "emb_gemini_api_key" in params else ''
            emb_azure_endpoint = params["emb_azure_endpoint"][0] if "emb_azure_endpoint" in params else ''
            emb_azure_api_version = params["emb_azure_api_version"][0] if "emb_azure_api_version" in params else ''
            emb_bedrock_aws_access_key_id = params["emb_bedrock_aws_access_key_id"][0] if "emb_bedrock_aws_access_key_id" in params else ''
            emb_bedrock_aws_secret_access_key = params["emb_bedrock_aws_secret_access_key"][0] if "emb_bedrock_aws_secret_access_key" in params else ''
            emb_bedrock_aws_session_token = params["emb_bedrock_aws_session_token"][0] if "emb_bedrock_aws_session_token" in params else ''
            emb_bedrock_region_name = params["emb_bedrock_region_name"][0] if "emb_bedrock_region_name" in params else ''
            vec_milvus_is_configured = params["vec_milvus_is_configured"][0] if "vec_milvus_is_configured" in params else ''
            vec_pinecone_is_configured = params["vec_pinecone_is_configured"][0] if "vec_pinecone_is_configured" in params else ''
            vec_alloydb_is_configured = params["vec_alloydb_is_configured"][0] if "vec_alloydb_is_configured" in params else ''
            vec_milvus_uri = params["vec_milvus_uri"][0] if "vec_milvus_uri" in params else ''
            vec_milvus_token = params["vec_milvus_token"][0] if "vec_milvus_token" in params else ''
            vec_pinecone_api_key = params["vec_pinecone_api_key"][0] if "vec_pinecone_api_key" in params else ''
            vec_pinecone_cloud = params["vec_pinecone_cloud"][0] if "vec_pinecone_cloud" in params else ''
            vec_pinecone_region = params["vec_pinecone_region"][0] if "vec_pinecone_region" in params else ''
            vec_pinecone_metric = params["vec_pinecone_metric"][0] if "vec_pinecone_metric" in params else ''
            vec_alloydb_user_name = params["vec_alloydb_user_name"][0] if "vec_alloydb_user_name" in params else ''
            vec_alloydb_password = params["vec_alloydb_password"][0] if "vec_alloydb_password" in params else ''
            vec_alloydb_region = params["vec_alloydb_region"][0] if "vec_alloydb_region" in params else ''
            vec_alloydb_cluster = params["vec_alloydb_cluster"][0] if "vec_alloydb_cluster" in params else ''
            vec_alloydb_instance = params["vec_alloydb_instance"][0] if "vec_alloydb_instance" in params else ''
            vec_alloydb_database = params["vec_alloydb_database"][0] if "vec_alloydb_database" in params else ''
            vec_alloydb_project_id = params["vec_alloydb_project_id"][0] if "vec_alloydb_project_id" in params else ''
            gra_neo4j_is_configured = params["gra_neo4j_is_configured"][0] if "gra_neo4j_is_configured" in params else ''
            gra_dgraph_is_configured = params["gra_dgraph_is_configured"][0] if "gra_dgraph_is_configured" in params else ''
            gra_neo4j_url = params["gra_neo4j_url"][0] if "gra_neo4j_url" in params else ''
            gra_neo4j_user_name = params["gra_neo4j_user_name"][0] if "gra_neo4j_user_name" in params else ''
            gra_neo4j_password = params["gra_neo4j_password"][0] if "gra_neo4j_password" in params else ''
            gra_neo4j_database = params["gra_neo4j_database"][0] if "gra_neo4j_database" in params else ''
            gra_dgraph_url = params["gra_dgraph_url"][0] if "gra_dgraph_url" in params else ''
            gra_dgraph_user_name = params["gra_dgraph_user_name"][0] if "gra_dgraph_user_name" in params else ''
            gra_dgraph_password = params["gra_dgraph_password"][0] if "gra_dgraph_password" in params else ''
            gra_dgraph_namespace = params["gra_dgraph_namespace"][0] if "gra_dgraph_namespace" in params else ''
            mcp_enabled_1 = params["mcp_enabled_1"][0] if "mcp_enabled_1" in params else ''
            mcp_name_1 = params["mcp_name_1"][0] if "mcp_name_1" in params else ''
            mcp_url_1 = params["mcp_url_1"][0] if "mcp_url_1" in params else ''
            mcp_token_1 = params["mcp_token_1"][0] if "mcp_token_1" in params else ''
            mcp_enabled_2 = params["mcp_enabled_2"][0] if "mcp_enabled_2" in params else ''
            mcp_name_2 = params["mcp_name_2"][0] if "mcp_name_2" in params else ''
            mcp_url_2 = params["mcp_url_2"][0] if "mcp_url_2" in params else ''
            mcp_token_2 = params["mcp_token_2"][0] if "mcp_token_2" in params else ''
            mcp_enabled_3 = params["mcp_enabled_3"][0] if "mcp_enabled_3" in params else ''
            mcp_name_3 = params["mcp_name_3"][0] if "mcp_name_3" in params else ''
            mcp_url_3 = params["mcp_url_3"][0] if "mcp_url_3" in params else ''
            mcp_token_3 = params["mcp_token_3"][0] if "mcp_token_3" in params else ''
            mcp_enabled_4 = params["mcp_enabled_4"][0] if "mcp_enabled_4" in params else ''
            mcp_name_4 = params["mcp_name_4"][0] if "mcp_name_4" in params else ''
            mcp_url_4 = params["mcp_url_4"][0] if "mcp_url_4" in params else ''
            mcp_token_4 = params["mcp_token_4"][0] if "mcp_token_4" in params else ''
            mcp_enabled_5 = params["mcp_enabled_5"][0] if "mcp_enabled_5" in params else ''
            mcp_name_5 = params["mcp_name_5"][0] if "mcp_name_5" in params else ''
            mcp_url_5 = params["mcp_url_5"][0] if "mcp_url_5" in params else ''
            mcp_token_5 = params["mcp_token_5"][0] if "mcp_token_5" in params else ''

            settings = {}

            settings["llm_ollama_is_configured"] = llm_ollama_is_configured
            settings["llm_azure_is_configured"] = llm_azure_is_configured
            settings["llm_openai_is_configured"] = llm_openai_is_configured
            settings["llm_bedrock_is_configured"] = llm_bedrock_is_configured
            settings["llm_gemini_is_configured"] = llm_gemini_is_configured
            settings["llm_ollama_model"] = llm_ollama_model
            settings["llm_azure_model"] = llm_azure_model
            settings["llm_openai_model"] = llm_openai_model
            settings["llm_bedrock_model"] = llm_bedrock_model
            settings["llm_gemini_model"] = llm_gemini_model
            settings["llm_ollama_base_url"] = llm_ollama_base_url
            settings["llm_azure_deployment_name"] = llm_azure_deployment_name
            settings["llm_openai_api_key"] = llm_openai_api_key
            settings["llm_azure_api_key"] = llm_azure_api_key
            settings["llm_gemini_api_key"] = llm_gemini_api_key
            settings["llm_azure_endpoint"] = llm_azure_endpoint
            settings["llm_azure_api_version"] = llm_azure_api_version
            settings["llm_bedrock_aws_access_key_id"] = llm_bedrock_aws_access_key_id
            settings["llm_bedrock_aws_secret_access_key"] = llm_bedrock_aws_secret_access_key
            settings["llm_bedrock_aws_session_token"] = llm_bedrock_aws_session_token
            settings["llm_bedrock_region_name"] = llm_bedrock_region_name
            settings["emb_hf_is_configured"] = emb_hf_is_configured
            settings["emb_ollama_is_configured"] = emb_ollama_is_configured
            settings["emb_azure_is_configured"] = emb_azure_is_configured
            settings["emb_openai_is_configured"] = emb_openai_is_configured
            settings["emb_bedrock_is_configured"] = emb_bedrock_is_configured
            settings["emb_gemini_is_configured"] = emb_gemini_is_configured
            settings["emb_hf_model_name"] = emb_hf_model_name
            settings["emb_ollama_model_name"] = emb_ollama_model_name
            settings["emb_azure_model"] = emb_azure_model
            settings["emb_openai_model"] = emb_openai_model
            settings["emb_bedrock_model_name"] = emb_bedrock_model_name
            settings["emb_gemini_model_name"] = emb_gemini_model_name
            settings["emb_hf_output_dims"] = emb_hf_output_dims
            settings["emb_ollama_output_dims"] = emb_ollama_output_dims
            settings["emb_azure_output_dims"] = emb_azure_output_dims
            settings["emb_openai_output_dims"] = emb_openai_output_dims
            settings["emb_bedrock_output_dims"] = emb_bedrock_output_dims
            settings["emb_gemini_output_dims"] = emb_gemini_output_dims
            settings["emb_ollama_base_url"] = emb_ollama_base_url
            settings["emb_azure_deployment_name"] = emb_azure_deployment_name
            settings["emb_azure_api_key"] = emb_azure_api_key
            settings["emb_gemini_api_key"] = emb_gemini_api_key
            settings["emb_azure_endpoint"] = emb_azure_endpoint
            settings["emb_azure_api_version"] = emb_azure_api_version
            settings["emb_bedrock_aws_access_key_id"] = emb_bedrock_aws_access_key_id
            settings["emb_bedrock_aws_secret_access_key"] = emb_bedrock_aws_secret_access_key
            settings["emb_bedrock_aws_session_token"] = emb_bedrock_aws_session_token
            settings["emb_bedrock_region_name"] = emb_bedrock_region_name
            settings["vec_milvus_is_configured"] = vec_milvus_is_configured
            settings["vec_pinecone_is_configured"] = vec_pinecone_is_configured
            settings["vec_alloydb_is_configured"] = vec_alloydb_is_configured
            settings["vec_milvus_uri"] = vec_milvus_uri
            settings["vec_milvus_token"] = vec_milvus_token
            settings["vec_pinecone_api_key"] = vec_pinecone_api_key
            settings["vec_pinecone_cloud"] = vec_pinecone_cloud
            settings["vec_pinecone_region"] = vec_pinecone_region
            settings["vec_pinecone_metric"] = vec_pinecone_metric
            settings["vec_alloydb_user_name"] = vec_alloydb_user_name
            settings["vec_alloydb_password"] = vec_alloydb_password
            settings["vec_alloydb_region"] = vec_alloydb_region
            settings["vec_alloydb_cluster"] = vec_alloydb_cluster
            settings["vec_alloydb_instance"] = vec_alloydb_instance
            settings["vec_alloydb_database"] = vec_alloydb_database
            settings["vec_alloydb_project_id"] = vec_alloydb_project_id
            settings["gra_neo4j_is_configured"] = gra_neo4j_is_configured
            settings["gra_dgraph_is_configured"] = gra_dgraph_is_configured
            settings["gra_neo4j_url"] = gra_neo4j_url
            settings["gra_neo4j_user_name"] = gra_neo4j_user_name
            settings["gra_neo4j_password"] = gra_neo4j_password
            settings["gra_neo4j_database"] = gra_neo4j_database
            settings["gra_dgraph_url"] = gra_dgraph_url
            settings["gra_dgraph_user_name"] = gra_dgraph_user_name
            settings["gra_dgraph_password"] = gra_dgraph_password
            settings["gra_dgraph_namespace"] = gra_dgraph_namespace
            settings["mcp_enabled_1"] = mcp_enabled_1
            settings["mcp_name_1"] = mcp_name_1
            settings["mcp_url_1"] = mcp_url_1
            settings["mcp_token_1"] = mcp_token_1
            settings["mcp_enabled_2"] = mcp_enabled_2
            settings["mcp_name_2"] = mcp_name_2
            settings["mcp_url_2"] = mcp_url_2
            settings["mcp_token_2"] = mcp_token_2
            settings["mcp_enabled_3"] = mcp_enabled_3
            settings["mcp_name_3"] = mcp_name_3
            settings["mcp_url_3"] = mcp_url_3
            settings["mcp_token_3"] = mcp_token_3
            settings["mcp_enabled_4"] = mcp_enabled_4
            settings["mcp_name_4"] = mcp_name_4
            settings["mcp_url_4"] = mcp_url_4
            settings["mcp_token_4"] = mcp_token_4
            settings["mcp_enabled_5"] = mcp_enabled_5
            settings["mcp_name_5"] = mcp_name_5
            settings["mcp_url_5"] = mcp_url_5
            settings["mcp_token_5"] = mcp_token_5

            encode_llm_passwords(self.service, settings)

            self.service.confs["llm"]["llm_config"].submit(settings)
            self.service.apps["mltk-container"].reload()
            self.send_json_response({})
        except exceptions.ApplicationError:
            raise
        except:
            import traceback
            raise Exception(traceback.format_exc())

    def handle_GET(self):
        settings = self.service.confs["llm"]["llm_config"]
        decode_llm_passwords(self.service, settings)
        data = {
            "llm_ollama_is_configured": settings["llm_ollama_is_configured"] if "llm_ollama_is_configured" in settings else "",
            "llm_azure_is_configured": settings["llm_azure_is_configured"] if "llm_azure_is_configured" in settings else "",
            "llm_openai_is_configured": settings["llm_openai_is_configured"] if "llm_openai_is_configured" in settings else "",
            "llm_bedrock_is_configured": settings["llm_bedrock_is_configured"] if "llm_bedrock_is_configured" in settings else "",
            "llm_gemini_is_configured": settings["llm_gemini_is_configured"] if "llm_gemini_is_configured" in settings else "",
            "llm_ollama_model": settings["llm_ollama_model"] if "llm_ollama_model" in settings else "",
            "llm_azure_model": settings["llm_azure_model"] if "llm_azure_model" in settings else "",
            "llm_openai_model": settings["llm_openai_model"] if "llm_openai_model" in settings else "",
            "llm_bedrock_model": settings["llm_bedrock_model"] if "llm_bedrock_model" in settings else "",
            "llm_gemini_model": settings["llm_gemini_model"] if "llm_gemini_model" in settings else "",
            "llm_ollama_base_url": settings["llm_ollama_base_url"] if "llm_ollama_base_url" in settings else "",
            "llm_azure_deployment_name": settings["llm_azure_deployment_name"] if "llm_azure_deployment_name" in settings else "",
            "llm_openai_api_key": settings["llm_openai_api_key"] if "llm_openai_api_key" in settings else "",
            "llm_azure_api_key": settings["llm_azure_api_key"] if "llm_azure_api_key" in settings else "",
            "llm_gemini_api_key": settings["llm_gemini_api_key"] if "llm_gemini_api_key" in settings else "",
            "llm_azure_endpoint": settings["llm_azure_endpoint"] if "llm_azure_endpoint" in settings else "",
            "llm_azure_api_version": settings["llm_azure_api_version"] if "llm_azure_api_version" in settings else "",
            "llm_bedrock_aws_access_key_id": settings["llm_bedrock_aws_access_key_id"] if "llm_bedrock_aws_access_key_id" in settings else "",
            "llm_bedrock_aws_secret_access_key": settings["llm_bedrock_aws_secret_access_key"] if "llm_bedrock_aws_secret_access_key" in settings else "",
            "llm_bedrock_aws_session_token": settings["llm_bedrock_aws_session_token"] if "llm_bedrock_aws_session_token" in settings else "",
            "llm_bedrock_region_name": settings["llm_bedrock_region_name"] if "llm_bedrock_region_name" in settings else "",
            "emb_hf_is_configured": settings["emb_hf_is_configured"] if "emb_hf_is_configured" in settings else "",
            "emb_ollama_is_configured": settings["emb_ollama_is_configured"] if "emb_ollama_is_configured" in settings else "",
            "emb_azure_is_configured": settings["emb_azure_is_configured"] if "emb_azure_is_configured" in settings else "",
            "emb_openai_is_configured": settings["emb_openai_is_configured"] if "emb_openai_is_configured" in settings else "",
            "emb_bedrock_is_configured": settings["emb_bedrock_is_configured"] if "emb_bedrock_is_configured" in settings else "",
            "emb_gemini_is_configured": settings["emb_gemini_is_configured"] if "emb_gemini_is_configured" in settings else "",
            "emb_hf_model_name": settings["emb_hf_model_name"] if "emb_hf_model_name" in settings else "",
            "emb_ollama_model_name": settings["emb_ollama_model_name"] if "emb_ollama_model_name" in settings else "",
            "emb_azure_model": settings["emb_azure_model"] if "emb_azure_model" in settings else "",
            "emb_openai_model": settings["emb_openai_model"] if "emb_openai_model" in settings else "",
            "emb_bedrock_model_name": settings["emb_bedrock_model_name"] if "emb_bedrock_model_name" in settings else "",
            "emb_gemini_model_name": settings["emb_gemini_model_name"] if "emb_gemini_model_name" in settings else "",
            "emb_hf_output_dims": settings["emb_hf_output_dims"] if "emb_hf_output_dims" in settings else "",
            "emb_ollama_output_dims": settings["emb_ollama_output_dims"] if "emb_ollama_output_dims" in settings else "",
            "emb_azure_output_dims": settings["emb_azure_output_dims"] if "emb_azure_output_dims" in settings else "",
            "emb_openai_output_dims": settings["emb_openai_output_dims"] if "emb_openai_output_dims" in settings else "",
            "emb_bedrock_output_dims": settings["emb_bedrock_output_dims"] if "emb_bedrock_output_dims" in settings else "",
            "emb_gemini_output_dims": settings["emb_gemini_output_dims"] if "emb_gemini_output_dims" in settings else "",
            "emb_ollama_base_url": settings["emb_ollama_base_url"] if "emb_ollama_base_url" in settings else "",
            "emb_azure_deployment_name": settings["emb_azure_deployment_name"] if "emb_azure_deployment_name" in settings else "",
            "emb_azure_api_key": settings["emb_azure_api_key"] if "emb_azure_api_key" in settings else "",
            "emb_gemini_api_key": settings["emb_gemini_api_key"] if "emb_gemini_api_key" in settings else "",
            "emb_azure_endpoint": settings["emb_azure_endpoint"] if "emb_azure_endpoint" in settings else "",
            "emb_azure_api_version": settings["emb_azure_api_version"] if "emb_azure_api_version" in settings else "",
            "emb_bedrock_aws_access_key_id": settings["emb_bedrock_aws_access_key_id"] if "emb_bedrock_aws_access_key_id" in settings else "",
            "emb_bedrock_aws_secret_access_key": settings["emb_bedrock_aws_secret_access_key"] if "emb_bedrock_aws_secret_access_key" in settings else "",
            "emb_bedrock_aws_session_token": settings["emb_bedrock_aws_session_token"] if "emb_bedrock_aws_session_token" in settings else "",
            "emb_bedrock_region_name": settings["emb_bedrock_region_name"] if "emb_bedrock_region_name" in settings else "",
            "vec_milvus_is_configured": settings["vec_milvus_is_configured"] if "vec_milvus_is_configured" in settings else "",
            "vec_pinecone_is_configured": settings["vec_pinecone_is_configured"] if "vec_pinecone_is_configured" in settings else "",
            "vec_alloydb_is_configured": settings["vec_alloydb_is_configured"] if "vec_alloydb_is_configured" in settings else "",
            "vec_milvus_uri": settings["vec_milvus_uri"] if "vec_milvus_uri" in settings else "",
            "vec_milvus_token": settings["vec_milvus_token"] if "vec_milvus_token" in settings else "",
            "vec_pinecone_api_key": settings["vec_pinecone_api_key"] if "vec_pinecone_api_key" in settings else "",
            "vec_pinecone_cloud": settings["vec_pinecone_cloud"] if "vec_pinecone_cloud" in settings else "",
            "vec_pinecone_region": settings["vec_pinecone_region"] if "vec_pinecone_region" in settings else "",
            "vec_pinecone_metric": settings["vec_pinecone_metric"] if "vec_pinecone_metric" in settings else "",
            "vec_alloydb_user_name": settings["vec_alloydb_user_name"] if "vec_alloydb_user_name" in settings else "",
            "vec_alloydb_password": settings["vec_alloydb_password"] if "vec_alloydb_password" in settings else "",
            "vec_alloydb_region": settings["vec_alloydb_region"] if "vec_alloydb_region" in settings else "",
            "vec_alloydb_cluster": settings["vec_alloydb_cluster"] if "vec_alloydb_cluster" in settings else "",
            "vec_alloydb_instance": settings["vec_alloydb_instance"] if "vec_alloydb_instance" in settings else "",
            "vec_alloydb_database": settings["vec_alloydb_database"] if "vec_alloydb_database" in settings else "",
            "vec_alloydb_project_id": settings["vec_alloydb_project_id"] if "vec_alloydb_project_id" in settings else "",
            "gra_neo4j_is_configured": settings["gra_neo4j_is_configured"] if "gra_neo4j_is_configured" in settings else "",
            "gra_dgraph_is_configured": settings["gra_dgraph_is_configured"] if "gra_dgraph_is_configured" in settings else "",
            "gra_neo4j_url": settings["gra_neo4j_url"] if "gra_neo4j_url" in settings else "",
            "gra_neo4j_user_name": settings["gra_neo4j_user_name"] if "gra_neo4j_user_name" in settings else "",
            "gra_neo4j_password": settings["gra_neo4j_password"] if "gra_neo4j_password" in settings else "",
            "gra_neo4j_database": settings["gra_neo4j_database"] if "gra_neo4j_database" in settings else "",
            "gra_dgraph_url": settings["gra_dgraph_url"] if "gra_dgraph_url" in settings else "",
            "gra_dgraph_user_name": settings["gra_dgraph_user_name"] if "gra_dgraph_user_name" in settings else "",
            "gra_dgraph_password": settings["gra_dgraph_password"] if "gra_dgraph_password" in settings else "",
            "gra_dgraph_namespace": settings["gra_dgraph_namespace"] if "gra_dgraph_namespace" in settings else "",
            "mcp_enabled_1": settings["mcp_enabled_1"] if "mcp_enabled_1" in settings else "",
            "mcp_name_1": settings["mcp_name_1"] if "mcp_name_1" in settings else "",
            "mcp_url_1": settings["mcp_url_1"] if "mcp_url_1" in settings else "",
            "mcp_token_1": settings["mcp_token_1"] if "mcp_token_1" in settings else "",
            "mcp_enabled_2": settings["mcp_enabled_2"] if "mcp_enabled_2" in settings else "",
            "mcp_name_2": settings["mcp_name_2"] if "mcp_name_2" in settings else "",
            "mcp_url_2": settings["mcp_url_2"] if "mcp_url_2" in settings else "",
            "mcp_token_2": settings["mcp_token_2"] if "mcp_token_2" in settings else "",
            "mcp_enabled_3": settings["mcp_enabled_3"] if "mcp_enabled_3" in settings else "",
            "mcp_name_3": settings["mcp_name_3"] if "mcp_name_3" in settings else "",
            "mcp_url_3": settings["mcp_url_3"] if "mcp_url_3" in settings else "",
            "mcp_token_3": settings["mcp_token_3"] if "mcp_token_3" in settings else "",
            "mcp_enabled_4": settings["mcp_enabled_4"] if "mcp_enabled_4" in settings else "",
            "mcp_name_4": settings["mcp_name_4"] if "mcp_name_4" in settings else "",
            "mcp_url_4": settings["mcp_url_4"] if "mcp_url_4" in settings else "",
            "mcp_token_4": settings["mcp_token_4"] if "mcp_token_4" in settings else "",
            "mcp_enabled_5": settings["mcp_enabled_5"] if "mcp_enabled_5" in settings else "",
            "mcp_name_5": settings["mcp_name_5"] if "mcp_name_5" in settings else "",
            "mcp_url_5": settings["mcp_url_5"] if "mcp_url_5" in settings else "",
            "mcp_token_5": settings["mcp_token_5"] if "mcp_token_5" in settings else "",

        }
        self.send_json_response(data)
