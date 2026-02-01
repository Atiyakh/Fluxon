#[derive(Debug, PartialEq, Eq, Hash, Clone, Copy)]
pub enum Method {
    Get,
    Post,
    Put,
    Delete,
    Patch,
    Options,
    Head,
}

impl Method {
    pub fn from_str(s: &str) -> Result<Self, String> {
        match s.to_uppercase().as_str() {
            "GET" => Ok(Method::Get),
            "POST" => Ok(Method::Post),
            "PUT" => Ok(Method::Put),
            "DELETE" => Ok(Method::Delete),
            "PATCH" => Ok(Method::Patch),
            "OPTIONS" => Ok(Method::Options),
            "HEAD" => Ok(Method::Head),
            _ => Err(format!("Unsupported HTTP method: {}", s)),
        }
    }
}
