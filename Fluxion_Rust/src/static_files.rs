use std::path::{Path, PathBuf};
use crate::http::request::Request;
use crate::http::response::Response;
use crate::http::status_code::StatusCode;
use std::fs;
use std::collections::HashMap;

pub struct StaticFiles {
    pub root: PathBuf,
}

impl StaticFiles {
    pub fn new<P: AsRef<Path>>(root: P) -> Self {
        Self {
            root: root.as_ref().to_path_buf(),
        }
    }

    pub fn serve(&self, request: &Request) -> Response {
        let mut path = self.root.clone();
        path.push(&request.path()[1..]); // Remove leading slash

        if path.is_file() {
            match fs::read_to_string(&path) {
                Ok(content) => {
                    let mut headers = HashMap::new();
                    if let Some(extension) = path.extension() {
                        if let Some(mime) = Self::get_mime_type(extension.to_str().unwrap_or("")) {
                            headers.insert("Content-Type".to_string(), mime.to_string());
                        }
                    }
                    Response::new(StatusCode::Ok, headers, Some(content))
                }
                Err(_) => Response::new(StatusCode::NotFound, HashMap::new(), Some("File Not Found".to_string())),
            }
        } else {
            Response::new(StatusCode::NotFound, HashMap::new(), Some("File Not Found".to_string())),
        }
    }

    fn get_mime_type(extension: &str) -> Option<&'static str> {
        match extension {
            "html" => Some("text/html"),
            "css" => Some("text/css"),
            "js" => Some("application/javascript"),
            "json" => Some("application/json"),
            "png" => Some("image/png"),
            "jpg" | "jpeg" => Some("image/jpeg"),
            "gif" => Some("image/gif"),
            "svg" => Some("image/svg+xml"),
            "ico" => Some("image/x-icon"),
            _ => None,
        }
    }
}
