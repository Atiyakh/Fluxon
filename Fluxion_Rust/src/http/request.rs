use serde::de::DeserializeOwned;
use std::collections::HashMap;
use crate::http::method::Method;

#[derive(Debug)]
pub struct Request {
    method: Method,
    path: String,
    headers: HashMap<String, String>,
    body: Option<String>,
}

impl Request {
    pub fn new(method: Method, path: String, headers: HashMap<String, String>, body: Option<String>) -> Self {
        Self {
            method,
            path,
            headers,
            body,
        }
    }

    pub fn from_raw(buffer: &[u8]) -> Result<Self, String> {
        let request_str = String::from_utf8_lossy(buffer);
        let mut lines = request_str.lines();

        let request_line = lines.next().ok_or("Invalid request: empty request")?;
        let mut request_line_parts = request_line.split_whitespace();

        let method = request_line_parts.next().ok_or("Invalid request: missing method")?;
        let path = request_line_parts.next().ok_or("Invalid request: missing path")?;
        let _version = request_line_parts.next().ok_or("Invalid request: missing HTTP version")?;

        let method = Method::from_str(method)?;

        let mut headers = HashMap::new();
        for line in lines.by_ref().take_while(|l| !l.is_empty()) {
            let mut parts = line.splitn(2, ": ");
            let key = parts.next().ok_or("Invalid header")?.to_string();
            let value = parts.next().ok_or("Invalid header")?.to_string();
            headers.insert(key, value);
        }

        let body = if let Some(content_length_str) = headers.get("Content-Length") {
            if let Ok(content_length) = content_length_str.parse::<usize>() {
                let body_str: String = lines.collect();
                if body_str.len() >= content_length {
                    Some(body_str[..content_length].to_string())
                } else {
                    None
                }
            } else {
                None
            }
        } else {
            None
        };

        Ok(Self::new(method, path.to_string(), headers, body))
    }

    pub fn method(&self) -> &Method {
        &self.method
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn json<T: DeserializeOwned>(&self) -> Result<T, serde_json::Error> {
        serde_json::from_str(self.body.as_ref().unwrap())
    }
}
