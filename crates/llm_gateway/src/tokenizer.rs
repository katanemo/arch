use log::debug;

#[derive(Debug, PartialEq, Eq)]
#[allow(dead_code)]
pub enum Error {
    UnknownModel,
    FailedToTokenize,
}

#[allow(dead_code)]
pub fn token_count(model_name: &str, text: &str) -> Result<usize, Error> {
    debug!("getting token count model={}", model_name);
    // Consideration: is it more expensive to instantiate the BPE object every time, or to contend the singleton?
    let bpe = tiktoken_rs::get_bpe_from_model(model_name).map_err(|_| Error::UnknownModel)?;
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
            Error::UnknownModel,
            token_count("unknown", "").expect_err("unknown model")
        )
    }
}
