use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PromptGuardTask {
    #[serde(rename = "jailbreak")]
    Jailbreak,
    #[serde(rename = "toxicity")]
    Toxicity,
    #[serde(rename = "both")]
    Both,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptGuardRequest {
    pub input: String,
    pub task: PromptGuardTask,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptGuardResponse {
    pub toxic_prob: Option<f64>,
    pub jailbreak_prob: Option<f64>,
    pub toxic_verdict: Option<bool>,
    pub jailbreak_verdict: Option<bool>,
}
