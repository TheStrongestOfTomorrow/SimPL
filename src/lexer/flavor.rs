use crate::lexer::token::TokenType;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct FlavorPack {
    pub name: String,
    keyword_overrides: HashMap<String, TokenType>,
}

impl FlavorPack {
    pub fn from_name(name: &str) -> Self {
        let mut overrides = HashMap::new();
        match name {
            "python" | "py" => {
                overrides.insert("print".into(), TokenType::Say);
                overrides.insert("def".into(), TokenType::Func);
                overrides.insert("True".into(), TokenType::True);
                overrides.insert("False".into(), TokenType::False);
                overrides.insert("None".into(), TokenType::Null);
                overrides.insert("raise".into(), TokenType::Raise);
                overrides.insert("elif".into(), TokenType::Elif);
            }
            "rust" | "rs" => {
                overrides.insert("println".into(), TokenType::Say);
                overrides.insert("let".into(), TokenType::Set);
                overrides.insert("fn".into(), TokenType::Func);
                overrides.insert("loop".into(), TokenType::While);
            }
            "go" => {
                overrides.insert("var".into(), TokenType::Set);
                overrides.insert("nil".into(), TokenType::Null);
            }
            "javascript" | "js" => {
                overrides.insert("console.log".into(), TokenType::Say);
                overrides.insert("let".into(), TokenType::Set);
                overrides.insert("const".into(), TokenType::Set);
                overrides.insert("var".into(), TokenType::Set);
                overrides.insert("function".into(), TokenType::Func);
                overrides.insert("undefined".into(), TokenType::Null);
                overrides.insert("throw".into(), TokenType::Raise);
            }
            "ruby" | "rb" => {
                overrides.insert("puts".into(), TokenType::Say);
                overrides.insert("def".into(), TokenType::Func);
                overrides.insert("nil".into(), TokenType::Null);
                overrides.insert("unless".into(), TokenType::If);
            }
            _ => {}
        }
        FlavorPack {
            name: name.to_string(),
            keyword_overrides: overrides,
        }
    }

    pub fn keyword_overrides(&self) -> Vec<(String, TokenType)> {
        self.keyword_overrides.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
    }

    pub fn available_flavors() -> Vec<&'static str> {
        vec!["simpl", "python", "rust", "go", "javascript", "ruby"]
    }
}

impl Default for FlavorPack {
    fn default() -> Self {
        FlavorPack {
            name: "simpl".into(),
            keyword_overrides: HashMap::new(),
        }
    }
}
