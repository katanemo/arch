use common::{common_types::open_ai::Message, consts::USER_ROLE};

pub fn extract_messages_for_hallucination(messages: &[Message]) -> Vec<String> {
    let all_user_messages = messages
        .iter()
        .filter(|m| m.role == USER_ROLE)
        .map(|m| m.content.as_ref().unwrap().clone())
        .collect::<Vec<String>>();
    all_user_messages
}

#[cfg(test)]
mod test {
    use common::common_types::open_ai::Message;

    use super::extract_messages_for_hallucination;

    #[test]
    fn test_hallucination_message() {
        let test_str = r#"
      [
        {
          "role": "system",
          "content": "You are a helpful assistant.\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{\"type\": \"function\", \"function\": {\"name\": \"headcount\", \"description\": \"Get headcount data for a region by staffing type\", \"parameters\": {\"properties\": {\"staffing_type\": {\"type\": \"str\", \"description\": \"The staffing type like contract, fte or agency\"}, \"region\": {\"type\": \"str\", \"description\": \"the geographical region for which you want headcount data.\"}}, \"required\": [\"staffing_type\", \"region\"]}}}\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
        },
        { "role": "user", "content": "tell me about headcount data" },
        {
          "role": "assistant",
          "content": "The \"headcount\" tool provides information about the number of employees in a specific region based on the type of staffing used. It requires two parameters: \"staffing_type\" and \"region\". The \"staffing_type\" parameter specifies the type of staffing, such as contract, full-time equivalent (fte), or agency. The \"region\" parameter specifies the geographical region for which you want headcount data."
        },
        { "role": "user", "content": "europe and for fte" }
      ]
      "#;

        let messages: Vec<Message> = serde_json::from_str(test_str).unwrap();
        let messages_for_halluncination = extract_messages_for_hallucination(&messages);
        assert_eq!(messages_for_halluncination.len(), 2);
    }
}
