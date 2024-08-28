use tiktoken_rs::model;

pub enum Error {
    UnknownModel,
    FailedToTokenize,
}

pub fn token_count(model_name: &str, text: &str) -> Result<usize, Error> {
    // Consideration: is it more expensive to instantiate the BPE object every time, or to contend the singleton?
    let bpe = tiktoken_rs::get_bpe_from_model(model_name).map_err(|_| Error::UnknownModel)?;
    Ok(bpe.encode_ordinary(text).len())
}
