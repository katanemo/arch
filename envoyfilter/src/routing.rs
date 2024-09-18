const OPEN_AI_PROVIDER: LlmProvider = LlmProvider::OpenAi("api.openai.com");
const MISTRAL_PROVIDER: LlmProvider = LlmProvider::Mistral("api.mistral.ai");

pub enum LlmProvider<'hostname> {
    OpenAi(&'hostname str),
    Mistral(&'hostname str),
}

impl AsRef<str> for LlmProvider<'_> {
    fn as_ref(&self) -> &str {
        match self {
            LlmProvider::OpenAi(hostname) => hostname,
            LlmProvider::Mistral(hostname) => hostname,
        }
    }
}

pub fn get_llm_provider<'hostname>() -> LlmProvider<'hostname> {
    if rand::random() {
        OPEN_AI_PROVIDER
    } else {
        MISTRAL_PROVIDER
    }
}
