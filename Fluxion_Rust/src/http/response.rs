use serde::Serialize;
use std::collections::HashMap;
use crate::http::status_code::StatusCode;

#[derive(Debug)]
pub struct Response {
    status_code: StatusCode,
    headers: HashMap<String, String>,
    body: Option<String>,
}

impl Response {
    pub fn new(status_code: StatusCode, headers: HashMap<String, String>, body: Option<String>) -> Self {
        Self {
            status_code,
            headers,
            body,
        }
    }

    pub fn to_raw(&self) -> String {
        let mut response_str = format!("HTTP/1.1 {} {}\n", self.status_code.as_u16(), self.status_code.as_str());

        for (key, value) in &self.headers {
            response_str.push_str(&format!("{}: {}\n", key, value));
        }

        response_str.push_str("\r\n");

        if let Some(body) = &self.body {
            response_str.push_str(body);
        }

        response_str
    }

    pub fn json<T: Serialize>(payload: T) -> Self {
        let mut headers = HashMap::new();
        headers.insert("Content-Type".to_string(), "application/json".to_string());
        let body = serde_json::to_string(&payload).unwrap();
        Self::new(StatusCode::Ok, headers, Some(body))
    }
}
