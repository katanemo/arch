# CreateEmbeddingRequestInput

Input text to embed, encoded as a string or array of tokens. To embed multiple inputs in a single request, pass an array of strings or array of token arrays. The input must not exceed the max input tokens for the model (8192 tokens for `text-embedding-ada-002`), cannot be an empty string, and any array must be 2048 dimensions or less. [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken) for counting tokens. 

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from openapi_client.models.create_embedding_request_input import CreateEmbeddingRequestInput

# TODO update the JSON string below
json = "{}"
# create an instance of CreateEmbeddingRequestInput from a JSON string
create_embedding_request_input_instance = CreateEmbeddingRequestInput.from_json(json)
# print the JSON string representation of the object
print(CreateEmbeddingRequestInput.to_json())

# convert the object into a dict
create_embedding_request_input_dict = create_embedding_request_input_instance.to_dict()
# create an instance of CreateEmbeddingRequestInput from a dict
create_embedding_request_input_from_dict = CreateEmbeddingRequestInput.from_dict(create_embedding_request_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


