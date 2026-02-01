use std::collections::HashMap;
use fluxion_rust::http::method::Method;
use fluxion_rust::http::request::Request;
use fluxion_rust::http::response::Response;
use fluxion_rust::http::status_code::StatusCode;
use fluxion_rust::routing::router::Router;
use fluxion_rust::server::Server;
use fluxion_rust::middleware::MiddlewareStack;
use fluxion_rust::templating::Templating;
use fluxion_rust::static_files::StaticFiles;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct User {
    id: u32,
    name: String,
}

fn handle_get(_req: &Request) -> Response {
    Response::new(StatusCode::Ok, HashMap::new(), Some("Hello from GET!".to_string()))
}

fn handle_post(_req: &Request) -> Response {
    Response::new(StatusCode::Ok, HashMap::new(), Some("Hello from POST!".to_string()))
}

fn handle_json_post(req: &Request) -> Response {
    match req.json::<User>() {
        Ok(user) => {
            println!("Received user: {:?}", user);
            Response::json(user)
        },
        Err(e) => {
            eprintln!("Failed to parse JSON: {}", e);
            Response::new(StatusCode::BadRequest, HashMap::new(), Some(format!("Invalid JSON: {}", e)))
        }
    }
}

fn simple_middleware(req: &Request) -> Result<(), Response> {
    println!("Middleware processing request for path: {}", req.path());
    // Example: Block requests to a specific path
    if req.path() == "/blocked" {
        return Err(Response::new(StatusCode::Forbidden, HashMap::new(), Some("This path is blocked by middleware.".to_string())));
    }
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut router = Router::new();
    router.add_route(Method::Get, "/", handle_get);
    router.add_route(Method::Post, "/", handle_post);
    router.add_route(Method::Post, "/json", handle_json_post);

    let mut middleware_stack = MiddlewareStack::new();
    middleware_stack.add(simple_middleware);

    // Initialize templating
    let templating = Templating::new("templates"); // Assuming a 'templates' directory at project root

    // Example template usage (not directly served by router, but demonstrates usage)
    let mut context = HashMap::new();
    context.insert("name".to_string(), "World".to_string());
    match templating.render("index.html", context) {
        Ok(rendered) => println!("Rendered template: {}", rendered),
        Err(e) => eprintln!("Failed to render template: {}", e),
    }

    // Initialize static files serving
    let static_files = StaticFiles::new("static"); // Assuming a 'static' directory at project root
    
    // Example of serving static files (would need to integrate into router for actual serving)
    // For now, this is just to show the StaticFiles struct usage
    let dummy_request = Request::new(Method::Get, "/test.txt".to_string(), HashMap::new(), None);
    let static_response = static_files.serve(&dummy_request);
    println!("Static file response status: {:?}", static_response);

    let server = Server::new("127.0.0.1:8080", router, middleware_stack);
    server.run().await
}