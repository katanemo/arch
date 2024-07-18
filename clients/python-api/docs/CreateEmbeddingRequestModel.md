# CreateEmbeddingRequestModel

ID of the model to use. You can use the [List models](/docs/api-reference/models/list) API to see all of your available models, or see our [Model overview](/docs/models/overview) for descriptions of them. 

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from openapi_client.models.create_embedding_request_model import CreateEmbeddingRequestModel

# TODO update the JSON string below
json = "{}"
# create an instance of CreateEmbeddingRequestModel from a JSON string
create_embedding_request_model_instance = CreateEmbeddingRequestModel.from_json(json)
# print the JSON string representation of the object
print(CreateEmbeddingRequestModel.to_json())

# convert the object into a dict
create_embedding_request_model_dict = create_embedding_request_model_instance.to_dict()
# create an instance of CreateEmbeddingRequestModel from a dict
create_embedding_request_model_from_dict = CreateEmbeddingRequestModel.from_dict(create_embedding_request_model_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


