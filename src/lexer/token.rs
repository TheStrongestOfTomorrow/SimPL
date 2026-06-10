use std::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum TokenType {
    // Keywords
    Say,
    Set,
    If,
    Else,
    Elif,
    For,
    While,
    Func,
    Return,
    Break,
    Continue,
    Try,
    Catch,
    Finally,
    Raise,
    Import,
    As,
    In,
    And,
    Or,
    Not,
    End,
    True,
    False,
    Null,
    None,

    // Literals
    Number,
    String,
    Ident,

    // Operators
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    Power,
    FloorDiv,

    // Comparison
    Equal,
    EqualEqual,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,

    // Assignment shortcuts
    PlusEqual,
    MinusEqual,
    StarEqual,
    SlashEqual,

    // Delimiters
    LParen,
    RParen,
    LBrace,
    RBrace,
    LBracket,
    RBracket,
    Comma,
    Dot,
    Colon,
    Arrow,
    Newline,
    Eof,
}

#[derive(Debug, Clone)]
pub struct Token {
    pub token_type: TokenType,
    pub lexeme: String,
    pub line: usize,
    pub column: usize,
}

impl Token {
    pub fn new(token_type: TokenType, lexeme: String, line: usize, column: usize) -> Self {
        Token { token_type, lexeme, line, column }
    }

    pub fn eof(line: usize, column: usize) -> Self {
        Token { token_type: TokenType::Eof, lexeme: String::new(), line, column }
    }
}

impl fmt::Display for TokenType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TokenType::Say => write!(f, "say"),
            TokenType::Set => write!(f, "set"),
            TokenType::If => write!(f, "if"),
            TokenType::Else => write!(f, "else"),
            TokenType::Elif => write!(f, "elif"),
            TokenType::For => write!(f, "for"),
            TokenType::While => write!(f, "while"),
            TokenType::Func => write!(f, "func"),
            TokenType::Return => write!(f, "return"),
            TokenType::Break => write!(f, "break"),
            TokenType::Continue => write!(f, "continue"),
            TokenType::Try => write!(f, "try"),
            TokenType::Catch => write!(f, "catch"),
            TokenType::Finally => write!(f, "finally"),
            TokenType::Raise => write!(f, "raise"),
            TokenType::Import => write!(f, "import"),
            TokenType::As => write!(f, "as"),
            TokenType::In => write!(f, "in"),
            TokenType::And => write!(f, "and"),
            TokenType::Or => write!(f, "or"),
            TokenType::Not => write!(f, "not"),
            TokenType::End => write!(f, "end"),
            TokenType::True => write!(f, "true"),
            TokenType::False => write!(f, "false"),
            TokenType::Null => write!(f, "null"),
            TokenType::None => write!(f, "none"),
            TokenType::Number => write!(f, "number"),
            TokenType::String => write!(f, "string"),
            TokenType::Ident => write!(f, "identifier"),
            TokenType::Plus => write!(f, "+"),
            TokenType::Minus => write!(f, "-"),
            TokenType::Star => write!(f, "*"),
            TokenType::Slash => write!(f, "/"),
            TokenType::Percent => write!(f, "%"),
            TokenType::Power => write!(f, "**"),
            TokenType::FloorDiv => write!(f, "//"),
            TokenType::Equal => write!(f, "="),
            TokenType::EqualEqual => write!(f, "=="),
            TokenType::NotEqual => write!(f, "!="),
            TokenType::Less => write!(f, "<"),
            TokenType::LessEqual => write!(f, "<="),
            TokenType::Greater => write!(f, ">"),
            TokenType::GreaterEqual => write!(f, ">="),
            TokenType::PlusEqual => write!(f, "+="),
            TokenType::MinusEqual => write!(f, "-="),
            TokenType::StarEqual => write!(f, "*="),
            TokenType::SlashEqual => write!(f, "/="),
            TokenType::LParen => write!(f, "("),
            TokenType::RParen => write!(f, ")"),
            TokenType::LBrace => write!(f, "{{"),
            TokenType::RBrace => write!(f, "}}"),
            TokenType::LBracket => write!(f, "["),
            TokenType::RBracket => write!(f, "]"),
            TokenType::Comma => write!(f, ","),
            TokenType::Dot => write!(f, "."),
            TokenType::Colon => write!(f, ":"),
            TokenType::Arrow => write!(f, "->"),
            TokenType::Newline => write!(f, "newline"),
            TokenType::Eof => write!(f, "EOF"),
        }
    }
}
