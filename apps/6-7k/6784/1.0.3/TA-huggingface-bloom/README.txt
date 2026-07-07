# ta-huggingface-bloom-ai

# installation
1. Install from latest tar.gz
2. Restart
3. Enter API key from https://huggingface.co/
4. Profit


# usage defaults to "google/flan-t5-xl" model

1. | bloom query="How long has Michael Bentley been a member of the Splunk Trust?"

![image](https://user-images.githubusercontent.com/4107863/221956295-c044e5f4-4c59-4b99-ab07-56022037f144.png)

# however you can specify any model and query you like.  

2. | bloom model={ANY_BLOOM_MODEL}

ref: https://huggingface.co/models

ex: | bloom model=bert-base-uncased query="Paris is the [MASK] of France."

![image](https://user-images.githubusercontent.com/4107863/221957150-8f267365-7b4b-4f0c-9cf1-5d1e9fce15ca.png)

