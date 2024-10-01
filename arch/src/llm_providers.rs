use public_types::configuration::LlmProvider;
use std::collections::HashMap;

pub struct LlmProviders<'providers> {
    providers: HashMap<String, LlmProvider>,
    default: Option<&'providers LlmProvider>,
}

impl<'providers> From<&[LlmProvider]> for LlmProviders<'providers> {
    fn from(llm_providers_config: &[LlmProvider]) -> Self {
        let llm_providers: HashMap<String, LlmProvider> = llm_providers_config
            .iter()
            .map(|llm_provider| (llm_provider.name.clone(), llm_provider.clone()))
            .collect();

        LlmProviders {
            providers: llm_providers,
            default: llm_providers
                .values()
                .find(|llm_provider| llm_provider.default.unwrap_or_default()),
        }
    }
}
