use std::sync::RwLock;
use std::{collections::HashMap, sync::OnceLock};

use crate::configuration::{Header, Ratelimit};

type RatelimitMap = HashMap<String, HashMap<Header, u32>>;
pub type RatelimitData = RwLock<RatelimitMap>;

pub fn ratelimits(ratelimits_config: Option<Vec<Ratelimit>>) -> &'static RatelimitData {
    static RATELIMIT_DATA: OnceLock<RatelimitData> = OnceLock::new();
    RATELIMIT_DATA.get_or_init(|| {
        RwLock::new(process_ratelimits(
            ratelimits_config.expect("The initialization call has to have passed a config"),
        ))
    })
}

fn process_ratelimits(ratelimits_config: Vec<Ratelimit>) -> RatelimitMap {
    let mut ratelimits = RatelimitMap::new();
    for mut ratelimit_config in ratelimits_config {
        match ratelimits.get_mut(&ratelimit_config.provider) {
            Some(limits) => {
                let selector = ratelimit_config.selectors.pop().unwrap();
                match limits.get_mut(&selector) {
                    Some(_) => {
                        panic!("repeated selector. Selectors per provider must be unique")
                    }
                    None => {
                        limits.insert(selector, 0);
                    }
                }
            }
            None => {
                ratelimits.insert(ratelimit_config.provider, HashMap::new());
            }
        }
    }
    ratelimits
}
