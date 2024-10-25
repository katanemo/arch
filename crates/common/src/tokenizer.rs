use log::debug;

#[derive(thiserror::Error, Debug, PartialEq, Eq)]
#[allow(dead_code)]
pub enum Error {
    #[error("Unknown model: {model_name}")]
    UnknownModel { model_name: String },
}

#[allow(dead_code)]
pub fn token_count(model_name: &str, text: &str) -> Result<usize, Error> {
    debug!("getting token count model={}", model_name);
    // Consideration: is it more expensive to instantiate the BPE object every time, or to contend the singleton?
    let bpe = tiktoken_rs::get_bpe_from_model(model_name).map_err(|_| Error::UnknownModel {
        model_name: model_name.to_string(),
    })?;
    Ok(bpe.encode_ordinary(text).len())
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn encode_ordinary() {
        let model_name = "gpt-3.5-turbo";
        let text = "How many tokens does this sentence have?";
        assert_eq!(
            8,
            token_count(model_name, text).expect("correct tokenization")
        );
    }

    #[test]
    fn unrecognized_model() {
        assert_eq!(
            Error::UnknownModel {
                model_name: "unknown".to_string()
            },
            token_count("unknown", "").expect_err("unknown model")
        )
    }
}
