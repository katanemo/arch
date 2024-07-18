# .EmbeddingsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**createEmbedding**](EmbeddingsApi.md#createEmbedding) | **POST** /embeddings | Creates an embedding vector representing the input text.


# **createEmbedding**
> CreateEmbeddingResponse createEmbedding(createEmbeddingRequest)


### Example


```typescript
import {  } from '';
import * as fs from 'fs';

const configuration = .createConfiguration();
const apiInstance = new .EmbeddingsApi(configuration);

let body:.EmbeddingsApiCreateEmbeddingRequest = {
  // CreateEmbeddingRequest
  createEmbeddingRequest: {
    input: null,
    model: null,
    encodingFormat: "float",
    dimensions: 1,
    user: "user-1234",
  },
};

apiInstance.createEmbedding(body).then((data:any) => {
  console.log('API called successfully. Returned data: ' + data);
}).catch((error:any) => console.error(error));
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **createEmbeddingRequest** | **CreateEmbeddingRequest**|  |


### Return type

**CreateEmbeddingResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK |  -  |

[[Back to top]](#) [[Back to API list]](README.md#documentation-for-api-endpoints) [[Back to Model list]](README.md#documentation-for-models) [[Back to README]](README.md)


