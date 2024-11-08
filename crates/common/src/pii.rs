pub fn obfuscate_auth_header(headers: &mut [(String, String)]) -> &[(String, String)] {
    headers.iter_mut().for_each(|(key, value)| {
        if key.to_lowercase() == "authorization" {
            if value.starts_with("Bearer ") {
                *value = "Bearer ***".to_string();
            } else {
                *value = "***".to_string();
            }
        }
    });

    headers
}

#[cfg(test)]
mod test {
    use crate::pii::obfuscate_auth_header;

    #[test]
    pub fn test_obfuscate_auth_header() {
        let mut headers = vec![("Authorization".to_string(), "Bearer 1234".to_string())];
        obfuscate_auth_header(&mut headers);
        assert_eq!(headers, vec![("Authorization".to_string(), "Bearer ***".to_string())]);
    }
}
