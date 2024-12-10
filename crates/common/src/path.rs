use std::collections::HashMap;

pub fn replace_params_in_path(
    path: &str,
    params: &HashMap<String, String>,
) -> Result<String, String> {
    let mut result = String::new();
    let mut in_param = false;
    let mut current_param = String::new();

    for c in path.chars() {
        if c == '{' {
            in_param = true;
        } else if c == '}' {
            in_param = false;
            let param_name = current_param.clone();
            if let Some(value) = params.get(&param_name) {
                result.push_str(value);
            } else {
                return Err(format!("Missing value for parameter `{}`", param_name));
            }
            current_param.clear();
        } else if in_param {
            current_param.push(c);
        } else {
            result.push(c);
        }
    }

    Ok(result)
}

#[cfg(test)]
mod test {
    #[test]
    fn test_replace_path() {
        let path = "/cluster.open-cluster-management.io/v1/managedclusters/{cluster_name}";
        let params = vec![("cluster_name".to_string(), "test1".to_string())]
            .into_iter()
            .collect();
        assert_eq!(
            super::replace_params_in_path(path, &params),
            Ok("/cluster.open-cluster-management.io/v1/managedclusters/test1".to_string())
        );

        let path = "/cluster.open-cluster-management.io/v1/managedclusters";
        let params = vec![].into_iter().collect();
        assert_eq!(
            super::replace_params_in_path(path, &params),
            Ok("/cluster.open-cluster-management.io/v1/managedclusters".to_string())
        );

        let path = "/foo/{bar}/baz";
        let params = vec![("bar".to_string(), "qux".to_string())]
            .into_iter()
            .collect();
        assert_eq!(
            super::replace_params_in_path(path, &params),
            Ok("/foo/qux/baz".to_string())
        );

        let path = "/foo/{bar}/baz/{qux}";
        let params = vec![
            ("bar".to_string(), "qux".to_string()),
            ("qux".to_string(), "quux".to_string()),
        ]
        .into_iter()
        .collect();
        assert_eq!(
            super::replace_params_in_path(path, &params),
            Ok("/foo/qux/baz/quux".to_string())
        );

        let path = "/foo/{bar}/baz/{qux}";
        let params = vec![("bar".to_string(), "qux".to_string())]
            .into_iter()
            .collect();
        assert_eq!(
            super::replace_params_in_path(path, &params),
            Err("Missing value for parameter `qux`".to_string())
        );
    }
}
