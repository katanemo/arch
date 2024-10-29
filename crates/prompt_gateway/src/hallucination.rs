use common::{
    common_types::open_ai::Message,
    consts::{ARCH_MODEL_PREFIX, HALLUCINATION_TEMPLATE, USER_ROLE},
};

pub fn extract_messages_for_hallucination(messages: &[Message]) -> Vec<String> {
    let mut arch_assistant = false;
    let mut user_messages = Vec::new();
    if messages.len() >= 2 {
        let latest_assistant_message = &messages[messages.len() - 2];
        if let Some(model) = latest_assistant_message.model.as_ref() {
            if model.starts_with(ARCH_MODEL_PREFIX) {
                arch_assistant = true;
            }
        }
    }
    if arch_assistant {
        for message in messages.iter().rev() {
            if let Some(model) = message.model.as_ref() {
                if !model.starts_with(ARCH_MODEL_PREFIX) {
                    if let Some(content) = &message.content {
                        if !content.starts_with(HALLUCINATION_TEMPLATE) {
                            break;
                        }
                    }
                }
            }
            if message.role == USER_ROLE {
                if let Some(content) = &message.content {
                    user_messages.push(content.clone());
                }
            }
        }
    } else if let Some(message) = messages.last() {
        if let Some(content) = &message.content {
            user_messages.push(content.clone());
        }
    }
    user_messages.reverse(); // Reverse to maintain the original order
    user_messages
}

#[cfg(test)]
mod test {
    use common::common_types::open_ai::Message;
    use pretty_assertions::assert_eq;

    use super::extract_messages_for_hallucination;

    #[test]
    fn test_hallucination_message_simple() {
        let test_str = r#"
      [
        {
          "role": "system",
          "model" : "gpt-3.5-turbo",
          "content": "You are a helpful assistant.\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{\"type\": \"function\", \"function\": {\"name\": \"headcount\", \"description\": \"Get headcount data for a region by staffing type\", \"parameters\": {\"properties\": {\"staffing_type\": {\"type\": \"str\", \"description\": \"The staffing type like contract, fte or agency\"}, \"region\": {\"type\": \"str\", \"description\": \"the geographical region for which you want headcount data.\"}}, \"required\": [\"staffing_type\", \"region\"]}}}\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
        },
        { "role": "user", "content": "tell me about headcount data" },
        {
          "role": "assistant",
          "model": "Arch-Function-1.5B",
          "content": "The \"headcount\" tool provides information about the number of employees in a specific region based on the type of staffing used. It requires two parameters: \"staffing_type\" and \"region\". The \"staffing_type\" parameter specifies the type of staffing, such as contract, full-time equivalent (fte), or agency. The \"region\" parameter specifies the geographical region for which you want headcount data."
        },
        { "role": "user", "content": "europe and for fte" }
      ]
      "#;

        let messages: Vec<Message> = serde_json::from_str(test_str).unwrap();
        let messages_for_halluncination = extract_messages_for_hallucination(&messages);
        assert_eq!(messages_for_halluncination.len(), 2);
    }
    #[test]
    fn test_hallucination_message_medium() {
        let test_str = r#"
      [
        {
          "role": "system",
          "model" : "gpt-3.5-turbo",
          "content": "You are a helpful assistant.\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{\"type\": \"function\", \"function\": {\"name\": \"headcount\", \"description\": \"Get headcount data for a region by staffing type\", \"parameters\": {\"properties\": {\"staffing_type\": {\"type\": \"str\", \"description\": \"The staffing type like contract, fte or agency\"}, \"region\": {\"type\": \"str\", \"description\": \"the geographical region for which you want headcount data.\"}}, \"required\": [\"staffing_type\", \"region\"]}}}\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
        },
        { "role": "user", "content": "Hello" },
        {
          "role": "assistant",
          "model": "gpt-3.5-turbo",
          "content": "Hi there!"
        },
        { "role": "user", "content": "tell me about headcount data" },
        {
          "role": "assistant",
          "model": "Arch-Function-1.5B",
          "content": "The \"headcount\" tool provides information about the number of employees in a specific region based on the type of staffing used. It requires two parameters: \"staffing_type\" and \"region\". The \"staffing_type\" parameter specifies the type of staffing, such as contract, full-time equivalent (fte), or agency. The \"region\" parameter specifies the geographical region for which you want headcount data."
        },
        { "role": "user", "content": "europe" }
        ,
        {
          "role": "system",
          "model": "Arch-Function-1.5B",
          "content": "It seems like you are asking for headcount data for Europe. Could you please specify the staffing type?"
        },
        { "role": "user", "content": "fte" }
      ]
      "#;

        let messages: Vec<Message> = serde_json::from_str(test_str).unwrap();
        let messages_for_halluncination = extract_messages_for_hallucination(&messages);
        println!("{:?}", messages_for_halluncination);
        assert_eq!(messages_for_halluncination.len(), 3);
    }
    #[test]
    fn test_hallucination_message_long() {
        let test_str = r#"
      [
        {
          "role": "system",
          "model" : "gpt-3.5-turbo",
          "content": "You are a helpful assistant.\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{\"type\": \"function\", \"function\": {\"name\": \"headcount\", \"description\": \"Get headcount data for a region by staffing type\", \"parameters\": {\"properties\": {\"staffing_type\": {\"type\": \"str\", \"description\": \"The staffing type like contract, fte or agency\"}, \"region\": {\"type\": \"str\", \"description\": \"the geographical region for which you want headcount data.\"}}, \"required\": [\"staffing_type\", \"region\"]}}}\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
        },
        { "role": "user", "content": "Hello" },
        {
          "role": "assistant",
          "model": "gpt-3.5-turbo",
          "content": "Hi there!"
        },
        { "role": "user", "content": "tell me about headcount data" },
        {
          "role": "assistant",
          "model": "Arch-Function-1.5B",
          "content": "The \"headcount\" tool provides information about the number of employees in a specific region based on the type of staffing used. It requires two parameters: \"staffing_type\" and \"region\". The \"staffing_type\" parameter specifies the type of staffing, such as contract, full-time equivalent (fte), or agency. The \"region\" parameter specifies the geographical region for which you want headcount data."
        },
        { "role": "user", "content": "europe" },
        {
          "role": "system",
          "model": "Arch-Function-1.5B",
          "content": "It seems like you are asking for headcount data for Europe. Could you please specify the staffing type?"
        },
        { "role": "user", "content": "fte" },
        {
          "role": "assistant",
          "model": "gpt-3.5-turbo",
          "content": "The headcount is 50000"
        },
        { "role": "user", "content": "tell me about the weather" },
        {
          "role": "assistant",
          "model": "Arch-Function-1.5B",
          "content" : "The weather forcast tools requires 2 parameters: city and days. Please specify"
        },
        { "role": "user", "content": "Seattle" },
        {
          "role": "system",
          "model": "Arch-Function-1.5B",
          "content": "It seems like you are asking for weather data for Seattle. Could you please specify the days?"
        },
        { "role": "user", "content": "7 days" }
      ]
      "#;

        let messages: Vec<Message> = serde_json::from_str(test_str).unwrap();
        let messages_for_halluncination = extract_messages_for_hallucination(&messages);
        println!("{:?}", messages_for_halluncination);
        assert_eq!(messages_for_halluncination.len(), 3);
        assert_eq!(
            ["tell me about the weather", "Seattle", "7 days"],
            messages_for_halluncination.as_slice()
        );
    }
}
