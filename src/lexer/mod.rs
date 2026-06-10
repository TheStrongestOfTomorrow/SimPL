pub mod token;
pub mod flavor;

pub use token::{Token, TokenType};
pub use flavor::FlavorPack;

use crate::error::SimPLError;
use std::collections::HashMap;

pub struct Lexer {
    source: String,
    chars: Vec<char>,
    pos: usize,
    line: usize,
    column: usize,
    keywords: HashMap<String, TokenType>,
    flavor: FlavorPack,
}

impl Lexer {
    pub fn new(source: impl Into<String>) -> Self {
        let source = source.into();
        let chars: Vec<char> = source.chars().collect();
        let mut keywords = HashMap::new();

        // Default SimPL keywords
        keywords.insert("say".into(), TokenType::Say);
        keywords.insert("set".into(), TokenType::Set);
        keywords.insert("if".into(), TokenType::If);
        keywords.insert("else".into(), TokenType::Else);
        keywords.insert("elif".into(), TokenType::Elif);
        keywords.insert("for".into(), TokenType::For);
        keywords.insert("while".into(), TokenType::While);
        keywords.insert("func".into(), TokenType::Func);
        keywords.insert("return".into(), TokenType::Return);
        keywords.insert("break".into(), TokenType::Break);
        keywords.insert("continue".into(), TokenType::Continue);
        keywords.insert("try".into(), TokenType::Try);
        keywords.insert("catch".into(), TokenType::Catch);
        keywords.insert("finally".into(), TokenType::Finally);
        keywords.insert("raise".into(), TokenType::Raise);
        keywords.insert("import".into(), TokenType::Import);
        keywords.insert("as".into(), TokenType::As);
        keywords.insert("in".into(), TokenType::In);
        keywords.insert("and".into(), TokenType::And);
        keywords.insert("or".into(), TokenType::Or);
        keywords.insert("not".into(), TokenType::Not);
        keywords.insert("end".into(), TokenType::End);
        keywords.insert("true".into(), TokenType::True);
        keywords.insert("false".into(), TokenType::False);
        keywords.insert("null".into(), TokenType::Null);
        keywords.insert("none".into(), TokenType::None);

        Lexer {
            source,
            chars,
            pos: 0,
            line: 1,
            column: 1,
            keywords,
            flavor: FlavorPack::default(),
        }
    }

    pub fn with_flavor(mut self, flavor: &str) -> Self {
        self.flavor = FlavorPack::from_name(flavor);
        self.apply_flavor();
        self
    }

    fn apply_flavor(&mut self) {
        for (kw, tt) in self.flavor.keyword_overrides() {
            self.keywords.insert(kw.to_string(), tt.clone());
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn peek_next(&self) -> Option<char> {
        self.chars.get(self.pos + 1).copied()
    }

    fn advance(&mut self) -> Option<char> {
        let ch = self.chars.get(self.pos).copied();
        if let Some(c) = ch {
            self.pos += 1;
            if c == '\n' {
                self.line += 1;
                self.column = 1;
            } else {
                self.column += 1;
            }
        }
        ch
    }

    fn match_char(&mut self, expected: char) -> bool {
        if self.peek() == Some(expected) {
            self.advance();
            true
        } else {
            false
        }
    }

    fn skip_whitespace(&mut self) {
        while let Some(ch) = self.peek() {
            match ch {
                ' ' | '\t' | '\r' => {
                    self.advance();
                }
                '#' => {
                    while let Some(c) = self.peek() {
                        if c == '\n' { break; }
                        self.advance();
                    }
                }
                _ => break,
            }
        }
    }

    fn scan_string(&mut self, quote: char) -> Result<Token, SimPLError> {
        let line = self.line;
        let col = self.column;
        let mut value = String::new();

        while let Some(ch) = self.peek() {
            if ch == quote {
                self.advance();
                break;
            }
            if ch == '\n' {
                return Err(SimPLError::lexer("Unterminated string", line, col, &self.source));
            }
            if ch == '\\' {
                self.advance();
                if let Some(escaped) = self.peek() {
                    match escaped {
                        'n' => value.push('\n'),
                        't' => value.push('\t'),
                        'r' => value.push('\r'),
                        '\\' => value.push('\\'),
                        '"' => value.push('"'),
                        '\'' => value.push('\''),
                        '0' => value.push('\0'),
                        _ => {
                            value.push('\\');
                            value.push(escaped);
                        }
                    }
                    self.advance();
                }
            } else {
                value.push(ch);
                self.advance();
            }
        }

        Ok(Token::new(TokenType::String, value, line, col))
    }

    fn scan_number(&mut self) -> Token {
        let line = self.line;
        let col = self.column;
        let mut num_str = String::new();

        while let Some(ch) = self.peek() {
            if ch.is_ascii_digit() {
                num_str.push(ch);
                self.advance();
            } else if ch == '.' {
                // Only include dot if followed by a digit (part of number)
                // Otherwise it's a method call like 5.sqrt()
                if let Some(next) = self.peek_next() {
                    if next.is_ascii_digit() {
                        num_str.push(ch);
                        self.advance();
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            } else {
                break;
            }
        }

        if num_str.ends_with('.') {
            num_str.push('0');
        }

        Token::new(TokenType::Number, num_str, line, col)
    }

    fn scan_identifier(&mut self) -> Token {
        let line = self.line;
        let col = self.column;
        let mut ident = String::new();

        while let Some(ch) = self.peek() {
            if ch.is_alphanumeric() || ch == '_' {
                ident.push(ch);
                self.advance();
            } else {
                break;
            }
        }

        let token_type = self.keywords.get(&ident).cloned().unwrap_or(TokenType::Ident);
        Token::new(token_type, ident, line, col)
    }

    pub fn tokenize(&mut self) -> Result<Vec<Token>, SimPLError> {
        let mut tokens = Vec::new();

        loop {
            self.skip_whitespace();

            let ch = match self.peek() {
                Some(c) => c,
                None => {
                    tokens.push(Token::eof(self.line, self.column));
                    break;
                }
            };

            let line = self.line;
            let col = self.column;

            let token = match ch {
                '\n' => {
                    self.advance();
                    if tokens.last().map_or(true, |t| t.token_type != TokenType::Newline) {
                        Token::new(TokenType::Newline, "\n".into(), line, col)
                    } else {
                        continue;
                    }
                }
                '+' => {
                    self.advance();
                    if self.match_char('=') {
                        Token::new(TokenType::PlusEqual, "+=".into(), line, col)
                    } else {
                        Token::new(TokenType::Plus, "+".into(), line, col)
                    }
                }
                '-' => {
                    self.advance();
                    if self.match_char('>') {
                        Token::new(TokenType::Arrow, "->".into(), line, col)
                    } else if self.match_char('=') {
                        Token::new(TokenType::MinusEqual, "-=".into(), line, col)
                    } else {
                        Token::new(TokenType::Minus, "-".into(), line, col)
                    }
                }
                '*' => {
                    self.advance();
                    if self.match_char('*') {
                        Token::new(TokenType::Power, "**".into(), line, col)
                    } else if self.match_char('=') {
                        Token::new(TokenType::StarEqual, "*=".into(), line, col)
                    } else {
                        Token::new(TokenType::Star, "*".into(), line, col)
                    }
                }
                '/' => {
                    self.advance();
                    if self.match_char('/') {
                        Token::new(TokenType::FloorDiv, "//".into(), line, col)
                    } else if self.match_char('=') {
                        Token::new(TokenType::SlashEqual, "/=".into(), line, col)
                    } else {
                        Token::new(TokenType::Slash, "/".into(), line, col)
                    }
                }
                '%' => {
                    self.advance();
                    Token::new(TokenType::Percent, "%".into(), line, col)
                }
                '=' => {
                    self.advance();
                    if self.match_char('=') {
                        Token::new(TokenType::EqualEqual, "==".into(), line, col)
                    } else {
                        Token::new(TokenType::Equal, "=".into(), line, col)
                    }
                }
                '!' => {
                    self.advance();
                    if self.match_char('=') {
                        Token::new(TokenType::NotEqual, "!=".into(), line, col)
                    } else {
                        return Err(SimPLError::lexer(
                            "Unexpected character '!'. Did you mean '!='?",
                            line, col, &self.source,
                        ));
                    }
                }
                '<' => {
                    self.advance();
                    if self.match_char('=') {
                        Token::new(TokenType::LessEqual, "<=".into(), line, col)
                    } else {
                        Token::new(TokenType::Less, "<".into(), line, col)
                    }
                }
                '>' => {
                    self.advance();
                    if self.match_char('=') {
                        Token::new(TokenType::GreaterEqual, ">=".into(), line, col)
                    } else {
                        Token::new(TokenType::Greater, ">".into(), line, col)
                    }
                }
                '(' => { self.advance(); Token::new(TokenType::LParen, "(".into(), line, col) }
                ')' => { self.advance(); Token::new(TokenType::RParen, ")".into(), line, col) }
                '{' => { self.advance(); Token::new(TokenType::LBrace, "{".into(), line, col) }
                '}' => { self.advance(); Token::new(TokenType::RBrace, "}".into(), line, col) }
                '[' => { self.advance(); Token::new(TokenType::LBracket, "[".into(), line, col) }
                ']' => { self.advance(); Token::new(TokenType::RBracket, "]".into(), line, col) }
                ',' => { self.advance(); Token::new(TokenType::Comma, ",".into(), line, col) }
                '.' => { self.advance(); Token::new(TokenType::Dot, ".".into(), line, col) }
                ':' => { self.advance(); Token::new(TokenType::Colon, ":".into(), line, col) }
                '"' => { self.advance(); self.scan_string('"')? }
                '\'' => { self.advance(); self.scan_string('\'')? }
                _ if ch.is_ascii_digit() => self.scan_number(),
                _ if ch.is_alphabetic() || ch == '_' => self.scan_identifier(),
                _ => {
                    self.advance();
                    return Err(SimPLError::lexer(
                        format!("Unexpected character '{}'", ch),
                        line, col, &self.source,
                    ));
                }
            };

            tokens.push(token);
        }

        Ok(tokens)
    }
}
