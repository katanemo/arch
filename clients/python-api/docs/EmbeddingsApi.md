# openapi_client.EmbeddingsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_embedding**](EmbeddingsApi.md#create_embedding) | **POST** /embeddings | Creates an embedding vector representing the input text.


# **create_embedding**
> CreateEmbeddingResponse create_embedding(create_embedding_request)

Creates an embedding vector representing the input text.

### Example


```python
import openapi_client
from openapi_client.models.create_embedding_request import CreateEmbeddingRequest
from openapi_client.models.create_embedding_response import CreateEmbeddingResponse
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.EmbeddingsApi(api_client)
    create_embedding_request = openapi_client.CreateEmbeddingRequest() # CreateEmbeddingRequest | 

    try:
        # Creates an embedding vector representing the input text.
        api_response = api_instance.create_embedding(create_embedding_request)
        print("The response of EmbeddingsApi->create_embedding:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmbeddingsApi->create_embedding: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **create_embedding_request** | [**CreateEmbeddingRequest**](CreateEmbeddingRequest.md)|  | 

### Return type

[**CreateEmbeddingResponse**](CreateEmbeddingResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

