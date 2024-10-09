# Insurance Agent Demo

This demo showcases how the **Arch** can be used to manage insurance-related tasks such as policy inquiries, initiating policies, and updating claims or deductibles. In this demo, the assistant provides factual information related to insurance policies (e.g., car, boat, house, motorcycle).

The system can perform a variety of tasks, such as answering insurance-related questions, retrieving policy coverage details, initiating policies, and updating claims or deductibles.

## Available Functions:

- **Policy Q/A**: Handles general Q&A related to insurance policies.
  - **Endpoint**: `/policy/qa`
  - This function answers general inquiries related to insurance, such as coverage details or policy types. It is the default target for insurance-related queries.

- **Get Policy Coverage**: Retrieves the coverage details for a given policy type (car, boat, house, motorcycle).
  - **Endpoint**: `/policy/coverage`
  - Parameters:
    - `policy_type` (required): The type of policy. Available options: `car`, `boat`, `house`, `motorcycle`. Defaults to `car`.

- **Initiate Policy**: Starts a policy coverage for car, boat, motorcycle, or house.
  - **Endpoint**: `/policy/initiate`
  - Parameters:
    - `policy_type` (required): The type of policy. Available options: `car`, `boat`, `house`, `motorcycle`. Defaults to `car`.
    - `deductible` (required): The deductible amount set for the policy.

- **Update Claim**: Updates the notes on a specific insurance claim.
  - **Endpoint**: `/policy/claim`
  - Parameters:
    - `claim_id` (required): The claim number.
    - `notes` (optional): Notes about the claim number for the adjustor to see.

- **Update Deductible**: Updates the deductible amount for a specific policy coverage.
  - **Endpoint**: `/policy/deductible`
  - Parameters:
    - `policy_id` (required): The ID of the policy.
    - `deductible` (required): The deductible amount to be set for the policy.

**Arch** is designed to intelligently routes prompts to the appropriate functions based on the target, allowing for seamless interaction with various insurance-related services.

# Starting the demo
1. Please make sure the [pre-requisites](../../../README.md?tab=readme-ov-file#prerequisites) are installed correctly
2. Start Arch
   ```sh
   sh run_demo.sh
   ```
3. Navigate to http://localhost:18080/
4. Tell me what can you do for me?"

# Observability
Arch gateway publishes stats endpoint at http://localhost:19901/stats. In this demo we are using prometheus to pull stats from arch and we are using grafana to visalize the stats in dashboard. To see grafana dashboard follow instructions below,

1. Start grafana and prometheus using following command
   ```yaml
   docker compose --profile monitoring up
   ```
1. Navigate to http://localhost:3000/ to open grafana UI (use admin/grafana as credentials)
1. From grafana left nav click on dashboards and select "Intelligent Gateway Overview" to view arch gateway stats

Here is sample interaction,
<img width="575" alt="image" src="https://github.com/user-attachments/assets/25d40f46-616e-41ea-be8e-1623055c84ec">
