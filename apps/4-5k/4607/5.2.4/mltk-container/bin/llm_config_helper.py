import json

basic_config = {'llm': {'ollama': [{'is_configured': 1,
    'model': None,
    'base_url': 'http://ollama:11434'}],
  'azure_openai': [{'is_configured': 0,
    'model': None,
    'deployment_name': None,
    'api_key': None,
    'azure_endpoint': None,
    'api_version': None}],
  'openai': [{'is_configured': 0, 
    'model': None, 
    'base_url': None,
    'api_key': None}],
  'bedrock': [{'is_configured': 0,
    'model': None,
    'aws_access_key_id': None,
    'aws_secret_access_key': None,
    'aws_session_token': None,
    'region_name': None}],
  'gemini': [{'is_configured': 0, 'model': None, 'api_key': None}]},
 'embedding_model': {'huggingface': [{'is_configured': 1,
    'model_name': 'all-MiniLM-L6-v2',
    'output_dims': 384},
   {'is_configured': 1,
    'model_name': 'intfloat/multilingual-e5-large',
    'output_dims': 1024}],
  'ollama': [{'is_configured': 0,
    'model_name': None,
    'base_url': None,
    'output_dims': None}],
  'azure_openai': [{'is_configured': 0,
    'model': None,
    'deployment_name': None,
    'api_key': None,
    'azure_endpoint': None,
    'api_version': None,
    'output_dims': None}],
  'openai': [{'is_configured': 0,
    'model': None,
    'api_key': None,
    'output_dims': None}],
  'bedrock': [{'is_configured': 0,
    'model_name': None,
    'aws_access_key_id': None,
    'aws_secret_access_key': None,
    'aws_session_token': None,
    'region_name': None,
    'aws_profile': None,
    'output_dims': None}],
  'gemini': [{'is_configured': 0,
    'model_name': None,
    'api_key': None,
    'output_dims': None}]},
 'vector_db': {'milvus': [{'is_configured': 1,
    'uri': 'http://milvus-standalone:19530',
    'token': ''}],
  'pinecone': [{'is_configured': 0,
    'api_key': None,
    'cloud': None,
    'region': None,
    'metric': None}],
  'alloydb': [{'is_configured': 0,
    'project_id': None,
    'region': None,
    'cluster': None,
    'instance': None,
    'database': None,
    'user': None,
    'password': None}]},
 'graph_db': {'neo4j': [{'is_configured': 0,
    'username': None,
    'password': None,
    'url': None,
    'database': None}],
  'dgraph': [{'is_configured': 0,
    'username': None,
    'password': None,
    'url': None,
    'namespace': None}]},
    'mcp': [
      {"enabled": 0, "name": None, "url": None, "token": None}, 
      {"enabled": 0, "name": None, "url": None, "token": None}, 
      {"enabled": 0, "name": None, "url": None, "token": None}, 
      {"enabled": 0, "name": None, "url": None, "token": None}, 
      {"enabled": 0, "name": None, "url": None, "token": None}
    ]
    }

def set_llm_config(settings):
    params = {
        "llm_ollama_is_configured": settings["llm_ollama_is_configured"],
        "llm_azure_is_configured": settings["llm_azure_is_configured"],
        "llm_openai_is_configured": settings["llm_openai_is_configured"],
        "llm_bedrock_is_configured": settings["llm_bedrock_is_configured"],
        "llm_gemini_is_configured": settings["llm_gemini_is_configured"],
        "llm_ollama_model": settings["llm_ollama_model"],
        "llm_azure_model": settings["llm_azure_model"],
        "llm_openai_model": settings["llm_openai_model"],
        "llm_bedrock_model": settings["llm_bedrock_model"],
        "llm_gemini_model": settings["llm_gemini_model"],
        "llm_ollama_base_url": settings["llm_ollama_base_url"],
        "llm_openai_base_url": settings["llm_openai_base_url"],
        "llm_azure_deployment_name": settings["llm_azure_deployment_name"],
        "llm_openai_api_key": settings["llm_openai_api_key"],
        "llm_azure_api_key": settings["llm_azure_api_key"],
        "llm_gemini_api_key": settings["llm_gemini_api_key"],
        "llm_azure_endpoint": settings["llm_azure_endpoint"],
        "llm_azure_api_version": settings["llm_azure_api_version"],
        "llm_bedrock_aws_access_key_id": settings["llm_bedrock_aws_access_key_id"],
        "llm_bedrock_aws_secret_access_key": settings["llm_bedrock_aws_secret_access_key"],
        "llm_bedrock_aws_session_token": settings["llm_bedrock_aws_session_token"],
        "llm_bedrock_region_name": settings["llm_bedrock_region_name"],
        "emb_hf_is_configured": settings["emb_hf_is_configured"],
        "emb_ollama_is_configured": settings["emb_ollama_is_configured"],
        "emb_azure_is_configured": settings["emb_azure_is_configured"],
        "emb_openai_is_configured": settings["emb_openai_is_configured"],
        "emb_bedrock_is_configured": settings["emb_bedrock_is_configured"],
        "emb_gemini_is_configured": settings["emb_gemini_is_configured"],
        "emb_hf_model_name": settings["emb_hf_model_name"],
        "emb_ollama_model_name": settings["emb_ollama_model_name"],
        "emb_azure_model": settings["emb_azure_model"],
        "emb_openai_model": settings["emb_openai_model"],
        "emb_bedrock_model_name": settings["emb_bedrock_model_name"],
        "emb_gemini_model_name": settings["emb_gemini_model_name"],
        "emb_hf_output_dims": settings["emb_hf_output_dims"],
        "emb_ollama_output_dims": settings["emb_ollama_output_dims"],
        "emb_azure_output_dims": settings["emb_azure_output_dims"],
        "emb_openai_output_dims": settings["emb_openai_output_dims"],
        "emb_bedrock_output_dims": settings["emb_bedrock_output_dims"],
        "emb_gemini_output_dims": settings["emb_gemini_output_dims"],
        "emb_ollama_base_url": settings["emb_ollama_base_url"],
        "emb_azure_deployment_name": settings["emb_azure_deployment_name"],
        "emb_azure_api_key": settings["emb_azure_api_key"],
        "emb_gemini_api_key": settings["emb_gemini_api_key"],
        "emb_azure_endpoint": settings["emb_azure_endpoint"],
        "emb_azure_api_version": settings["emb_azure_api_version"],
        "emb_bedrock_aws_access_key_id": settings["emb_bedrock_aws_access_key_id"],
        "emb_bedrock_aws_secret_access_key": settings["emb_bedrock_aws_secret_access_key"],
        "emb_bedrock_aws_session_token": settings["emb_bedrock_aws_session_token"],
        "emb_bedrock_region_name": settings["emb_bedrock_region_name"],
        "vec_milvus_is_configured": settings["vec_milvus_is_configured"],
        "vec_pinecone_is_configured": settings["vec_pinecone_is_configured"],
        "vec_alloydb_is_configured": settings["vec_alloydb_is_configured"],
        "vec_milvus_uri": settings["vec_milvus_uri"],
        "vec_milvus_token": settings["vec_milvus_token"],
        "vec_pinecone_api_key": settings["vec_pinecone_api_key"],
        "vec_pinecone_cloud": settings["vec_pinecone_cloud"],
        "vec_pinecone_region": settings["vec_pinecone_region"],
        "vec_pinecone_metric": settings["vec_pinecone_metric"],
        "vec_alloydb_user_name": settings["vec_alloydb_user_name"],
        "vec_alloydb_password": settings["vec_alloydb_password"],
        "vec_alloydb_region": settings["vec_alloydb_region"],
        "vec_alloydb_cluster": settings["vec_alloydb_cluster"],
        "vec_alloydb_instance": settings["vec_alloydb_instance"],
        "vec_alloydb_database": settings["vec_alloydb_database"],
        "vec_alloydb_project_id": settings["vec_alloydb_project_id"],
        "gra_neo4j_is_configured": settings["gra_neo4j_is_configured"],
        "gra_dgraph_is_configured": settings["gra_dgraph_is_configured"],
        "gra_neo4j_url": settings["gra_neo4j_url"],
        "gra_neo4j_user_name": settings["gra_neo4j_user_name"],
        "gra_neo4j_password": settings["gra_neo4j_password"],
        "gra_neo4j_database": settings["gra_neo4j_database"],
        "gra_dgraph_url": settings["gra_dgraph_url"],
        "gra_dgraph_user_name": settings["gra_dgraph_user_name"],
        "gra_dgraph_password": settings["gra_dgraph_password"],
        "gra_dgraph_namespace": settings["gra_dgraph_namespace"],
    }
    
    for key_name in params.keys():
        key_name_s = key_name.split("_", 2)
        key1, key2, key3 = key_name_s[0], key_name_s[1], key_name_s[-1]
        if key1 == "emb":
            key1 = "embedding_model"
        elif key1 == "vec":
            key1 = "vector_db"
        elif key1 == "gra":
            key1 = "graph_db"
            
        if key2 == "azure":
            key2 = "azure_openai"
        elif key2 == "hf":
            key2 = "huggingface"

        if key3 == "endpoint":
            key3 = "azure_endpoint"
        elif key3 == "user_name":
            if key2 == "alloydb":
                key3 = "user"
            else:
                key3 = "username"

        if params[key_name]:
            try:
                basic_config[key1][key2][0][key3] = params[key_name]
            except Exception as e:
                print(e)
    try:
      basic_config['mcp'][0]['enabled'] = settings["mcp_enabled_1"]
      basic_config['mcp'][0]['name'] = settings["mcp_name_1"]
      basic_config['mcp'][0]['url'] = settings["mcp_url_1"]
      basic_config['mcp'][0]['token'] = settings["mcp_token_1"]
      basic_config['mcp'][1]['enabled'] = settings["mcp_enabled_2"]
      basic_config['mcp'][1]['name'] = settings["mcp_name_2"]
      basic_config['mcp'][1]['url'] = settings["mcp_url_2"]
      basic_config['mcp'][1]['token'] = settings["mcp_token_2"]
      basic_config['mcp'][2]['enabled'] = settings["mcp_enabled_3"]
      basic_config['mcp'][2]['name'] = settings["mcp_name_3"]
      basic_config['mcp'][2]['url'] = settings["mcp_url_3"]
      basic_config['mcp'][2]['token'] = settings["mcp_token_3"]
      basic_config['mcp'][3]['enabled'] = settings["mcp_enabled_4"]
      basic_config['mcp'][3]['name'] = settings["mcp_name_4"]
      basic_config['mcp'][3]['url'] = settings["mcp_url_4"]
      basic_config['mcp'][3]['token'] = settings["mcp_token_4"]
      basic_config['mcp'][4]['enabled'] = settings["mcp_enabled_5"]
      basic_config['mcp'][4]['name'] = settings["mcp_name_5"]
      basic_config['mcp'][4]['url'] = settings["mcp_url_5"]
      basic_config['mcp'][4]['token'] = settings["mcp_token_5"]
    except:
      pass

    return json.dumps(basic_config)
