#[non_exhaustive]
pub struct LlmProviders;

impl LlmProviders {
    pub const OPENAI_PROVIDER: LlmProvider<'static> = LlmProvider {
        name: "openai",
        hostname: "api.openai.com",
        api_key_header: "x-bolt-openai-api-key",
        model: "gpt-3.5-turbo",
    };
    pub const MISTRAL_PROVIDER: LlmProvider<'static> = LlmProvider {
        name: "mistral",
        hostname: "api.mistral.ai",
        api_key_header: "x-bolt-mistral-api-key",
        model: "mistral-large-latest",
    };

    pub const VARIANTS: &'static [LlmProvider<'static>] =
        &[Self::OPENAI_PROVIDER, Self::MISTRAL_PROVIDER];
}

pub struct LlmProvider<'prov> {
    name: &'prov str,
    hostname: &'prov str,
    api_key_header: &'prov str,
    model: &'prov str,
}

impl std::fmt::Display for LlmProvider<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name)
    }
}

impl LlmProvider<'_> {
    pub fn api_key_header(&self) -> &str {
        self.api_key_header
    }

    pub fn hostname(&self) -> &str {
        self.hostname
    }

    pub fn choose_model(&self) -> &str {
        // In the future this can be a more complex function balancing reliability, cost, performance, etc.
        self.model
    }
}
