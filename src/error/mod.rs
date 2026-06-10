pub mod reporter;

use std::fmt;

#[derive(Debug, Clone)]
pub enum SimPLError {
    Lexer { message: String, line: usize, column: usize, source: String },
    Parser { message: String, line: usize, column: usize },
    Runtime { message: String, line: usize },
    Package { message: String },
    Io { message: String },
}

impl SimPLError {
    pub fn lexer(msg: impl Into<String>, line: usize, column: usize, source: impl Into<String>) -> Self {
        SimPLError::Lexer { message: msg.into(), line, column, source: source.into() }
    }

    pub fn parser(msg: impl Into<String>, line: usize, column: usize) -> Self {
        SimPLError::Parser { message: msg.into(), line, column }
    }

    pub fn runtime(msg: impl Into<String>, line: usize) -> Self {
        SimPLError::Runtime { message: msg.into(), line }
    }

    pub fn package(msg: impl Into<String>) -> Self {
        SimPLError::Package { message: msg.into() }
    }

    pub fn io(msg: impl Into<String>) -> Self {
        SimPLError::Io { message: msg.into() }
    }
}

impl fmt::Display for SimPLError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SimPLError::Lexer { message, line, column, .. } => {
                write!(f, "Lexer Error at line {}, column {}: {}", line, column, message)
            }
            SimPLError::Parser { message, line, column } => {
                write!(f, "Parse Error at line {}, column {}: {}", line, column, message)
            }
            SimPLError::Runtime { message, line } => {
                write!(f, "Runtime Error at line {}: {}", line, message)
            }
            SimPLError::Package { message } => {
                write!(f, "Package Error: {}", message)
            }
            SimPLError::Io { message } => {
                write!(f, "I/O Error: {}", message)
            }
        }
    }
}

impl std::error::Error for SimPLError {}
