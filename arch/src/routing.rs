use std::rc::Rc;

use crate::llm_providers::LlmProviders;
use public_types::configuration::LlmProvider;
use rand::{seq::IteratorRandom, thread_rng};

pub enum ProviderHint {
    Default,
    Name(String),
}

impl From<String> for ProviderHint {
    fn from(value: String) -> Self {
        match value.as_str() {
            "default" => ProviderHint::Default,
            _ => ProviderHint::Name(value),
        }
    }
}

pub fn get_llm_provider(
    llm_providers: &LlmProviders,
    provider_hint: Option<ProviderHint>,
) -> Rc<LlmProvider> {
    let maybe_provider = provider_hint.and_then(|hint| match hint {
        ProviderHint::Default => llm_providers.default(),
        // FIXME: should a non-existent name in the hint be more explicit? i.e, return a BAD_REQUEST?
        ProviderHint::Name(name) => llm_providers.get(&name),
    });

    if let Some(provider) = maybe_provider {
        return provider;
    }

    let mut rng = thread_rng();
    llm_providers
        .iter()
        .choose(&mut rng)
        .expect("There should always be at least one llm provider")
        .1
        .clone()
}
