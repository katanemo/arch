use crate::llm_providers::{LlmProvider, LlmProviders};
use rand::{seq::SliceRandom, thread_rng};

pub fn get_llm_provider<'hostname>(deterministic: bool) -> &'static LlmProvider<'hostname> {
    if deterministic {
        &LlmProviders::OPENAI_PROVIDER
    } else {
        let mut rng = thread_rng();
        LlmProviders::VARIANTS
            .choose(&mut rng)
            .expect("There should always be at least one llm provider")
    }
}
