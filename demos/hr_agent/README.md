# HR Agent Demo

This demo showcases how the **Arch** can be used to build an HR agent to manage workforce-related inquiries, workforce planning, and communication via Slack. It intelligently routes incoming prompts to the correct targets, providing concise and useful responses tailored for HR and workforce decision-making.

## Available Functions:

- **HR Q/A**: Handles general Q&A related to insurance policies.
  - **Endpoint**: `/agent/hr_qa`

- **Workforce Data Retrieval**: Retrieves data related to workforce metrics like headcount, satisfaction, and staffing.
  - **Endpoint**: `/agent/workforce`
  - Parameters:
    - `staffing_type` (str, required): Type of staffing (e.g., `contract`, `fte`, `agency`).
    - `region` (str, required): Region for which the data is requested (e.g., `asia`, `europe`, `americas`).
    - `point_in_time` (int, optional): Time point for data retrieval (e.g., `0 days ago`, `30 days ago`).

- **Initiate Policy**: Sends messages to a Slack channel
  - **Endpoint**: `/agent/slack_message`
  - Parameters:
    - `slack_message` (str, required): The message content to be sent

# Starting the demo
1. Please make sure the [pre-requisites](https://github.com/katanemo/arch/?tab=readme-ov-file#prerequisites) are installed correctly
2. Start Arch
   ```sh
   sh run_demo.sh
   ```
3. Navigate to http://localhost:18080/agent/chat
4. "Can you give me workforce data for asia?"
