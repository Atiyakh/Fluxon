use std::collections::HashMap;
use tera::{Context, Tera};

pub struct Templating {
    tera: Tera,
}

impl Templating {
    pub fn new(template_dir: &str) -> Self {
        let mut tera = match Tera::new(format!("{}/**/*.html", template_dir).as_str()) {
            Ok(t) => t,
            Err(e) => {
                eprintln!("Parsing error(s): {}", e);
                ::std::process::exit(1);
            }
        };
        tera.autoescape_on(true);
        Templating { tera }
    }

    pub fn render(&self, template_name: &str, context: HashMap<String, String>) -> Result<String, tera::Error> {
        let mut ctx = Context::new();
        for (key, value) in context {
            ctx.insert(key, &value);
        }
        self.tera.render(template_name, &ctx)
    }
}
