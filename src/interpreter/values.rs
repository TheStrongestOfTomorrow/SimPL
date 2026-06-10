use std::collections::HashMap;
use std::fmt;
use std::cell::RefCell;
use std::rc::Rc;

use crate::parser::ast::Stmt;

#[derive(Debug, Clone)]
pub enum SimPLValue {
    Number(f64),
    String(String),
    Bool(bool),
    Null,
    List(Vec<SimPLValue>),
    Dict(HashMap<String, SimPLValue>),
    Func {
        name: String,
        params: Vec<String>,
        defaults: Vec<Option<crate::parser::ast::Expr>>,
        body: Vec<Stmt>,
        closure: Environment,
    },
    BuiltinFunc(String),
    HttpResponse {
        status: u16,
        headers: HashMap<String, String>,
        body: String,
    },
    Module(HashMap<String, SimPLValue>),
}

impl SimPLValue {
    pub fn is_truthy(&self) -> bool {
        match self {
            SimPLValue::Null => false,
            SimPLValue::Bool(b) => *b,
            SimPLValue::Number(n) => *n != 0.0,
            SimPLValue::String(s) => !s.is_empty(),
            SimPLValue::List(l) => !l.is_empty(),
            SimPLValue::Dict(d) => !d.is_empty(),
            _ => true,
        }
    }

    pub fn type_name(&self) -> &str {
        match self {
            SimPLValue::Number(_) => "number",
            SimPLValue::String(_) => "string",
            SimPLValue::Bool(_) => "bool",
            SimPLValue::Null => "null",
            SimPLValue::List(_) => "list",
            SimPLValue::Dict(_) => "dict",
            SimPLValue::Func { .. } => "function",
            SimPLValue::BuiltinFunc(_) => "builtin",
            SimPLValue::HttpResponse { .. } => "http_response",
            SimPLValue::Module(_) => "module",
        }
    }

    pub fn to_json_string(&self) -> String {
        match self {
            SimPLValue::Null => "null".into(),
            SimPLValue::Bool(b) => if *b { "true" } else { "false" }.into(),
            SimPLValue::Number(n) => {
                if n.fract() == 0.0 {
                    format!("{}", *n as i64)
                } else {
                    format!("{}", n)
                }
            }
            SimPLValue::String(s) => format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\"")),
            SimPLValue::List(items) => {
                let parts: Vec<String> = items.iter().map(|v| v.to_json_string()).collect();
                format!("[{}]", parts.join(", "))
            }
            SimPLValue::Dict(map) => {
                let parts: Vec<String> = map.iter().map(|(k, v)| {
                    format!("\"{}\": {}", k.replace('"', "\\\""), v.to_json_string())
                }).collect();
                format!("{{{}}}", parts.join(", "))
            }
            SimPLValue::HttpResponse { status, body, .. } => {
                format!("{{\"status\": {}, \"body\": \"{}\"}}", status, body.replace('"', "\\\""))
            }
            _ => format!("\"<{}>\"", self.type_name()),
        }
    }
}

impl fmt::Display for SimPLValue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SimPLValue::Number(n) => {
                if n.fract() == 0.0 && n.is_finite() {
                    write!(f, "{}", *n as i64)
                } else {
                    write!(f, "{}", n)
                }
            }
            SimPLValue::String(s) => write!(f, "{}", s),
            SimPLValue::Bool(b) => write!(f, "{}", if *b { "true" } else { "false" }),
            SimPLValue::Null => write!(f, "null"),
            SimPLValue::List(items) => {
                let parts: Vec<String> = items.iter().map(|v| {
                    if matches!(v, SimPLValue::String(_)) {
                        format!("\"{}\"", v)
                    } else {
                        format!("{}", v)
                    }
                }).collect();
                write!(f, "[{}]", parts.join(", "))
            }
            SimPLValue::Dict(map) => {
                let parts: Vec<String> = map.iter().map(|(k, v)| {
                    if matches!(v, SimPLValue::String(_)) {
                        format!("{}: \"{}\"", k, v)
                    } else {
                        format!("{}: {}", k, v)
                    }
                }).collect();
                write!(f, "{{{}}}", parts.join(", "))
            }
            SimPLValue::Func { name, .. } => write!(f, "<func {}>", name),
            SimPLValue::BuiltinFunc(name) => write!(f, "<builtin {}>", name),
            SimPLValue::HttpResponse { status, body, .. } => {
                write!(f, "HTTP {} {}", status, body)
            }
            SimPLValue::Module(_) => write!(f, "<module>"),
        }
    }
}

impl PartialEq for SimPLValue {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (SimPLValue::Number(a), SimPLValue::Number(b)) => a == b,
            (SimPLValue::String(a), SimPLValue::String(b)) => a == b,
            (SimPLValue::Bool(a), SimPLValue::Bool(b)) => a == b,
            (SimPLValue::Null, SimPLValue::Null) => true,
            (SimPLValue::List(a), SimPLValue::List(b)) => a == b,
            (SimPLValue::Dict(a), SimPLValue::Dict(b)) => a == b,
            _ => false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Environment {
    vars: HashMap<String, SimPLValue>,
    parent: Option<Rc<RefCell<Environment>>>,
}

impl Environment {
    pub fn new() -> Self {
        Environment {
            vars: HashMap::new(),
            parent: None,
        }
    }

    pub fn with_parent(parent: Rc<RefCell<Environment>>) -> Self {
        Environment {
            vars: HashMap::new(),
            parent: Some(parent),
        }
    }

    pub fn get(&self, name: &str) -> Option<SimPLValue> {
        if let Some(val) = self.vars.get(name) {
            Some(val.clone())
        } else if let Some(ref parent) = self.parent {
            parent.borrow().get(name)
        } else {
            None
        }
    }

    pub fn set(&mut self, name: &str, value: SimPLValue) {
        self.vars.insert(name.to_string(), value);
    }

    pub fn update(&mut self, name: &str, value: SimPLValue) -> bool {
        if self.vars.contains_key(name) {
            self.vars.insert(name.to_string(), value);
            true
        } else if let Some(ref parent) = self.parent {
            parent.borrow_mut().update(name, value)
        } else {
            false
        }
    }

    pub fn define(&mut self, name: &str, value: SimPLValue) {
        self.vars.insert(name.to_string(), value);
    }

    pub fn all_vars(&self) -> HashMap<String, SimPLValue> {
        let mut result = HashMap::new();
        if let Some(ref parent) = self.parent {
            result.extend(parent.borrow().all_vars());
        }
        result.extend(self.vars.clone());
        result
    }
}
