# CreateEmbeddingRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**input** | [**CreateEmbeddingRequestInput**](CreateEmbeddingRequestInput.md) |  | 
**model** | [**CreateEmbeddingRequestModel**](CreateEmbeddingRequestModel.md) |  | 
**encoding_format** | **str** | The format to return the embeddings in. Can be either &#x60;float&#x60; or [&#x60;base64&#x60;](https://pypi.org/project/pybase64/). | [optional] [default to 'float']
**dimensions** | **int** | The number of dimensions the resulting output embeddings should have. Only supported in &#x60;text-embedding-3&#x60; and later models.  | [optional] 
**user** | **str** | A unique identifier representing your end-user, which can help OpenAI to monitor and detect abuse. [Learn more](/docs/guides/safety-best-practices/end-user-ids).  | [optional] 

## Example

```python
from openapi_client.models.create_embedding_request import CreateEmbeddingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateEmbeddingRequest from a JSON string
create_embedding_request_instance = CreateEmbeddingRequest.from_json(json)
# print the JSON string representation of the object
print(CreateEmbeddingRequest.to_json())

# convert the object into a dict
create_embedding_request_dict = create_embedding_request_instance.to_dict()
# create an instance of CreateEmbeddingRequest from a dict
create_embedding_request_from_dict = CreateEmbeddingRequest.from_dict(create_embedding_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


