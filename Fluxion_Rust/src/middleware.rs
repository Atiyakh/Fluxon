use crate::http::request::Request;
use crate::http::response::Response;

pub type Middleware = fn(&Request) -> Result<(), Response>;

pub struct MiddlewareStack {
    middlewares: Vec<Middleware>,
}

impl MiddlewareStack {
    pub fn new() -> Self {
        Self {
            middlewares: Vec::new(),
        }
    }

    pub fn add(&mut self, middleware: Middleware) {
        self.middlewares.push(middleware);
    }

    pub fn handle(&self, request: &Request) -> Result<(), Response> {
        for middleware in &self.middlewares {
            middleware(request)?;
        }
        Ok(())
    }
}
