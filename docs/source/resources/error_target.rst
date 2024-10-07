.. _error_target:

Error Targets
=============

**Error targets** are designed to capture and manage specific issues or exceptions that occur during Arch's function or system's execution.

These endpoints receive errors forwarded from Arch when issues arise, such as improper function/API calls, guardrail violations, or other processing errors.
The errors are communicated to the application via headers like ``X-Arch-[ERROR-TYPE]``, enabling you to respond appropriately and handle errors gracefully.


Key Concepts
------------

**Error Type**: Categorizes the nature of the error, such as "ValidationError" or "RuntimeError." These error types help in identifying what
kind of issue occurred and provide context for troubleshooting.

**Error Message**: A clear, human-readable message describing the error. This should provide enough detail to inform users or developers of
the root cause or required action.

**Target Prompt**: The specific prompt or operation where the error occurred. Understanding where the error happened helps with debugging
 and pinpointing the source of the problem.

**Parameter-Specific Errors**: Errors that arise due to invalid or missing parameters when invoking a function. These errors are critical
for ensuring the correctness of inputs.


Error Header Example
--------------------

.. code-block:: http


    HTTP/1.1 400 Bad Request
    X-Arch-Error-Type: FunctionValidationError
    X-Arch-Error-Message: Tools call parsing failure
    X-Arch-Target-Prompt: createUser
    Content-Type: application/json

    "messages": [
    {
      "role": "user",
      "content": "Please create a user with the following ID: 1234"
    },
    {
      "role": "system",
      "content": "Expected a string for 'user_id', but got an integer."
    }]


Best Practices and Tips
-----------------------

- **Graceful Degradation**: If an error occurs, fail gracefully by providing fallback logic or alternative flows when possible.

- **Log Errors**: Always log errors on the server side for later analysis.

- **Client-Side Handling**: Make sure the client can interpret error responses and provide meaningful feedback to the user. Clients should not display raw error codes or stack traces but rather handle them gracefully.
