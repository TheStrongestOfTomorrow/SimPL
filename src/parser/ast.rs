use std::fmt;
use std::collections::HashMap;

use crate::lexer::token::TokenType;

#[derive(Debug, Clone)]
pub enum BinOperator {
    Add, Sub, Mul, Div, Mod, Power, FloorDiv,
    Equal, NotEqual, Less, LessEqual, Greater, GreaterEqual,
    And, Or,
}

#[derive(Debug, Clone)]
pub enum UnaryOperator {
    Negate, Not,
}

#[derive(Debug, Clone)]
pub enum Expr {
    Number(f64),
    StringLit(String),
    BoolLit(bool),
    NullLit,
    Ident(String),
    BinOp {
        left: Box<Expr>,
        op: BinOperator,
        right: Box<Expr>,
    },
    UnaryOp {
        op: UnaryOperator,
        operand: Box<Expr>,
    },
    Call {
        callee: Box<Expr>,
        args: Vec<Expr>,
    },
    MethodCall {
        object: Box<Expr>,
        method: String,
        args: Vec<Expr>,
    },
    Index {
        object: Box<Expr>,
        index: Box<Expr>,
    },
    ListLit(Vec<Expr>),
    DictLit(Vec<(String, Expr)>),
    Lambda {
        params: Vec<String>,
        body: Vec<Stmt>,
    },
    Ternary {
        condition: Box<Expr>,
        then_expr: Box<Expr>,
        else_expr: Box<Expr>,
    },
    Member {
        object: Box<Expr>,
        member: String,
    },
}

#[derive(Debug, Clone)]
pub enum Stmt {
    Say {
        value: Expr,
    },
    Assign {
        name: String,
        value: Expr,
    },
    IndexAssign {
        object: Expr,
        index: Expr,
        value: Expr,
    },
    MemberAssign {
        object: Expr,
        member: String,
        value: Expr,
    },
    AugAssign {
        name: String,
        op: TokenType,
        value: Expr,
    },
    If {
        condition: Expr,
        then_body: Vec<Stmt>,
        elif_clauses: Vec<(Expr, Vec<Stmt>)>,
        else_body: Option<Vec<Stmt>>,
    },
    For {
        var: String,
        iterable: Expr,
        body: Vec<Stmt>,
    },
    While {
        condition: Expr,
        body: Vec<Stmt>,
    },
    FuncDef {
        name: String,
        params: Vec<String>,
        defaults: Vec<Option<Expr>>,
        body: Vec<Stmt>,
    },
    Return {
        value: Option<Expr>,
    },
    Break,
    Continue,
    Try {
        try_body: Vec<Stmt>,
        catch_var: String,
        catch_body: Vec<Stmt>,
        finally_body: Option<Vec<Stmt>>,
    },
    Raise {
        value: Expr,
    },
    Import {
        module: String,
        alias: Option<String>,
    },
    ExprStmt {
        expr: Expr,
    },
    Block {
        body: Vec<Stmt>,
    },
}

// Signal types for control flow
#[derive(Debug, Clone)]
pub enum ControlFlow {
    Return(Option<crate::interpreter::values::SimPLValue>),
    Break,
    Continue,
    Raise(crate::interpreter::values::SimPLValue),
}

impl fmt::Display for BinOperator {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BinOperator::Add => write!(f, "+"),
            BinOperator::Sub => write!(f, "-"),
            BinOperator::Mul => write!(f, "*"),
            BinOperator::Div => write!(f, "/"),
            BinOperator::Mod => write!(f, "%"),
            BinOperator::Power => write!(f, "**"),
            BinOperator::FloorDiv => write!(f, "//"),
            BinOperator::Equal => write!(f, "=="),
            BinOperator::NotEqual => write!(f, "!="),
            BinOperator::Less => write!(f, "<"),
            BinOperator::LessEqual => write!(f, "<="),
            BinOperator::Greater => write!(f, ">"),
            BinOperator::GreaterEqual => write!(f, ">="),
            BinOperator::And => write!(f, "and"),
            BinOperator::Or => write!(f, "or"),
        }
    }
}
