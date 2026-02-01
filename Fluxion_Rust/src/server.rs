use crate::middleware::MiddlewareStack;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use crate::routing::router::Router;
use crate::http::request::Request;

pub struct Server {
    address: String,
    router: Arc<Router>,
    middleware_stack: Arc<MiddlewareStack>,
}

impl Server {
    pub fn new(address: &str, router: Router, middleware_stack: MiddlewareStack) -> Self {
        Self {
            address: address.to_string(),
            router: Arc::new(router),
            middleware_stack: Arc::new(middleware_stack),
        }
    }

    pub async fn run(self) -> Result<(), Box<dyn std::error::Error>> {
        let listener = TcpListener::bind(&self.address).await?;
        println!("Listening on {}", &self.address);

        loop {
            let (socket, _) = listener.accept().await?;
            let router = self.router.clone();
            let middleware_stack = self.middleware_stack.clone();
            tokio::spawn(async move {
                if let Err(e) = Self::handle_connection(socket, router, middleware_stack).await {
                    eprintln!("Failed to handle connection: {}", e);
                }
            });
        }
    }

    async fn handle_connection(mut socket: TcpStream, router: Arc<Router>, middleware_stack: Arc<MiddlewareStack>) -> Result<(), Box<dyn std::error::Error>> {
        let mut buffer = [0; 1024];
        let n = socket.read(&mut buffer).await?;
        let request = Request::from_raw(&buffer[..n])?;

        match middleware_stack.handle(&request) {
            Ok(_) => {
                let response = router.route(&request);
                socket.write_all(response.to_raw().as_bytes()).await?;
            }
            Err(response) => {
                socket.write_all(response.to_raw().as_bytes()).await?;
            }
        }

        socket.flush().await?;
        Ok(())
    }
}
