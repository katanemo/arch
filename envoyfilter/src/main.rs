fn main() {
    println!("Hello, world!\nMy favourite number is {}", some_fn());
}

fn some_fn() -> i32 {
    42
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn some_fn_is_42() {
        assert_eq!(some_fn(), 42);
    }
}
