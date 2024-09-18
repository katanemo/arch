#[non_exhaustive]
pub struct LlmProviders;

impl LlmProviders {
    pub const OPENAI_PROVIDER: LlmProvider<'static> = LlmProvider {
        name: "openai",
        hostname: "api.openai.com",
        api_key_header: "x-bolt-openai-api-key",
    };
    pub const MISTRAL_PROVIDER: LlmProvider<'static> = LlmProvider {
        name: "mistral",
        hostname: "api.openai.com",
        api_key_header: "x-bolt-mistral-api-key",
    };

    pub const VARIANTS: &'static [LlmProvider<'static>] =
        &[Self::OPENAI_PROVIDER, Self::MISTRAL_PROVIDER];
}

pub struct LlmProvider<'prov> {
    name: &'prov str,
    hostname: &'prov str,
    api_key_header: &'prov str,
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
}
