use std::collections::HashMap;
use crate::http::method::Method;
use crate::http::request::Request;
use crate::http::response::Response;
use crate::http::status_code::StatusCode;

type Handler = fn(&Request) -> Response;

#[derive(Clone)]
pub struct Router {
    routes: HashMap<(Method, String), Handler>,
}

impl Router {
    pub fn new() -> Self {
        Self {
            routes: HashMap::new(),
        }
    }

    pub fn add_route(&mut self, method: Method, path: &str, handler: Handler) {
        self.routes.insert((method, path.to_string()), handler);
    }

    pub fn route(&self, request: &Request) -> Response {
        match self.routes.get(&(request.method().clone(), request.path().to_string())) {
            Some(handler) => handler(request),
            None => Response::new(StatusCode::NotFound, HashMap::new(), Some("Not Found".to_string())),
        }
    }
}
