pub mod values;

use std::collections::HashMap;
use std::io::{self, Write};
use std::cell::RefCell;
use std::rc::Rc;

use crate::error::SimPLError;
use crate::interpreter::values::{SimPLValue, Environment};
use crate::lexer::Lexer;
use crate::parser::Parser;
use crate::parser::ast::{Expr, Stmt, BinOperator, UnaryOperator, ControlFlow};

pub struct Interpreter {
    env: Rc<RefCell<Environment>>,
    source: String,
}

impl Interpreter {
    pub fn new() -> Self {
        let env = Rc::new(RefCell::new(Environment::new()));
        let mut interp = Interpreter {
            env,
            source: String::new(),
        };
        interp.register_builtins();
        interp
    }

    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = source.into();
        self
    }

    pub fn run(&mut self, source: &str) -> Result<Option<SimPLValue>, SimPLError> {
        self.source = source.to_string();
        let mut lexer = Lexer::new(source);
        let tokens = lexer.tokenize()?;
        let mut parser = Parser::new(tokens);
        let ast = parser.parse()?;
        self.execute_block(&ast)
    }

    pub fn repl_eval(&mut self, line: &str) -> Result<Option<SimPLValue>, SimPLError> {
        self.run(line)
    }

    pub fn get_env(&self) -> Rc<RefCell<Environment>> {
        self.env.clone()
    }

    fn register_builtins(&mut self) {
        let builtins: Vec<(&str, SimPLValue)> = vec![
            ("say", SimPLValue::BuiltinFunc("say".into())),
            ("input", SimPLValue::BuiltinFunc("input".into())),
            ("type", SimPLValue::BuiltinFunc("type".into())),
            ("len", SimPLValue::BuiltinFunc("len".into())),
            ("str", SimPLValue::BuiltinFunc("str".into())),
            ("num", SimPLValue::BuiltinFunc("num".into())),
            ("int", SimPLValue::BuiltinFunc("int".into())),
            ("bool", SimPLValue::BuiltinFunc("bool".into())),
            ("list", SimPLValue::BuiltinFunc("list".into())),
            ("dict", SimPLValue::BuiltinFunc("dict".into())),
            ("range", SimPLValue::BuiltinFunc("range".into())),
            ("push", SimPLValue::BuiltinFunc("push".into())),
            ("pop", SimPLValue::BuiltinFunc("pop".into())),
            ("keys", SimPLValue::BuiltinFunc("keys".into())),
            ("values", SimPLValue::BuiltinFunc("values".into())),
            ("has", SimPLValue::BuiltinFunc("has".into())),
            ("abs", SimPLValue::BuiltinFunc("abs".into())),
            ("floor", SimPLValue::BuiltinFunc("floor".into())),
            ("ceil", SimPLValue::BuiltinFunc("ceil".into())),
            ("round", SimPLValue::BuiltinFunc("round".into())),
            ("sqrt", SimPLValue::BuiltinFunc("sqrt".into())),
            ("pow", SimPLValue::BuiltinFunc("pow".into())),
            ("min", SimPLValue::BuiltinFunc("min".into())),
            ("max", SimPLValue::BuiltinFunc("max".into())),
            ("random", SimPLValue::BuiltinFunc("random".into())),
            ("upper", SimPLValue::BuiltinFunc("upper".into())),
            ("lower", SimPLValue::BuiltinFunc("lower".into())),
            ("trim", SimPLValue::BuiltinFunc("trim".into())),
            ("split", SimPLValue::BuiltinFunc("split".into())),
            ("join", SimPLValue::BuiltinFunc("join".into())),
            ("replace", SimPLValue::BuiltinFunc("replace".into())),
            ("starts_with", SimPLValue::BuiltinFunc("starts_with".into())),
            ("ends_with", SimPLValue::BuiltinFunc("ends_with".into())),
            ("contains", SimPLValue::BuiltinFunc("contains".into())),
            ("reverse", SimPLValue::BuiltinFunc("reverse".into())),
            ("sort", SimPLValue::BuiltinFunc("sort".into())),
            ("slice", SimPLValue::BuiltinFunc("slice".into())),
            ("http_get", SimPLValue::BuiltinFunc("http_get".into())),
            ("http_post", SimPLValue::BuiltinFunc("http_post".into())),
            ("json_parse", SimPLValue::BuiltinFunc("json_parse".into())),
            ("json_stringify", SimPLValue::BuiltinFunc("json_stringify".into())),
            ("time", SimPLValue::BuiltinFunc("time".into())),
            ("sleep", SimPLValue::BuiltinFunc("sleep".into())),
            ("shell", SimPLValue::BuiltinFunc("shell".into())),
        ];

        for (name, val) in builtins {
            self.env.borrow_mut().define(name, val);
        }
    }

    fn execute_block(&mut self, stmts: &[Stmt]) -> Result<Option<SimPLValue>, SimPLError> {
        let mut last_value = None;

        for stmt in stmts {
            match self.execute_stmt(stmt)? {
                Some(ControlFlow::Return(val)) => return Ok(val),
                Some(ControlFlow::Break) => return Ok(None), // Propagated up
                Some(ControlFlow::Continue) => return Ok(None),
                Some(ControlFlow::Raise(val)) => return Err(SimPLError::runtime(
                    format!("{}", val), 0
                )),
                None => {}
            }
            // For regular statements, we don't set last_value from control flow
            if let Stmt::ExprStmt { .. } = stmt {
                // Expression statements could produce values for REPL
            }
        }

        Ok(last_value)
    }

    fn execute_stmt(&mut self, stmt: &Stmt) -> Result<Option<ControlFlow>, SimPLError> {
        match stmt {
            Stmt::Say { value } => {
                let val = self.eval_expr(value)?;
                println!("{}", val);
                Ok(None)
            }
            Stmt::Assign { name, value } => {
                let val = self.eval_expr(value)?;
                // Try to update existing variable, otherwise define new
                if !self.env.borrow_mut().update(name, val.clone()) {
                    self.env.borrow_mut().define(name, val);
                }
                Ok(None)
            }
            Stmt::IndexAssign { object, index, value } => {
                let idx_val = self.eval_expr(index)?;
                let val = self.eval_expr(value)?;

                match object {
                    Expr::Ident(name) => {
                        let mut env = self.env.borrow_mut();
                        if let Some(SimPLValue::List(ref mut items)) = env.get(name) {
                            if let SimPLValue::Number(i) = idx_val {
                                let idx = i as usize;
                                if idx < items.len() {
                                    items[idx] = val;
                                } else {
                                    return Err(SimPLError::runtime(
                                        format!("Index {} out of range for list of length {}", idx, items.len()),
                                        0,
                                    ));
                                }
                            } else {
                                return Err(SimPLError::runtime("List index must be a number", 0));
                            }
                        } else if let Some(SimPLValue::Dict(ref mut map)) = env.get(name) {
                            if let SimPLValue::String(key) = idx_val {
                                map.insert(key, val);
                            } else {
                                return Err(SimPLError::runtime("Dict key must be a string", 0));
                            }
                        } else {
                            return Err(SimPLError::runtime(format!("Cannot index-assign to '{}'", name), 0));
                        }
                    }
                    _ => return Err(SimPLError::runtime("Invalid index assignment target", 0)),
                }
                Ok(None)
            }
            Stmt::MemberAssign { object, member, value } => {
                let val = self.eval_expr(value)?;
                match object {
                    Expr::Ident(name) => {
                        let mut env = self.env.borrow_mut();
                        if let Some(SimPLValue::Dict(ref mut map)) = env.get(name) {
                            map.insert(member.clone(), val);
                        } else {
                            return Err(SimPLError::runtime(format!("Cannot set member '{}' on non-dict", member), 0));
                        }
                    }
                    _ => return Err(SimPLError::runtime("Invalid member assignment target", 0)),
                }
                Ok(None)
            }
            Stmt::AugAssign { name, op, value } => {
                let current = self.env.borrow().get(name)
                    .ok_or_else(|| SimPLError::runtime(format!("Undefined variable '{}'", name), 0))?;
                let rhs = self.eval_expr(value)?;

                let result = match (current, op) {
                    (SimPLValue::Number(a), crate::lexer::token::TokenType::PlusEqual) => {
                        if let SimPLValue::Number(b) = rhs { SimPLValue::Number(a + b) }
                        else if let SimPLValue::String(b) = rhs { SimPLValue::String(format!("{}{}", a, b)) }
                        else { return Err(SimPLError::runtime("Invalid operand for +=", 0)); }
                    }
                    (SimPLValue::String(a), crate::lexer::token::TokenType::PlusEqual) => {
                        if let SimPLValue::String(b) = rhs { SimPLValue::String(format!("{}{}", a, b)) }
                        else { SimPLValue::String(format!("{}{}", a, rhs)) }
                    }
                    (SimPLValue::Number(a), crate::lexer::token::TokenType::MinusEqual) => {
                        if let SimPLValue::Number(b) = rhs { SimPLValue::Number(a - b) }
                        else { return Err(SimPLError::runtime("Invalid operand for -=", 0)); }
                    }
                    (SimPLValue::Number(a), crate::lexer::token::TokenType::StarEqual) => {
                        if let SimPLValue::Number(b) = rhs { SimPLValue::Number(a * b) }
                        else { return Err(SimPLError::runtime("Invalid operand for *=", 0)); }
                    }
                    (SimPLValue::Number(a), crate::lexer::token::TokenType::SlashEqual) => {
                        if let SimPLValue::Number(b) = rhs {
                            if b == 0.0 { return Err(SimPLError::runtime("Division by zero", 0)); }
                            SimPLValue::Number(a / b)
                        } else { return Err(SimPLError::runtime("Invalid operand for /=", 0)); }
                    }
                    _ => return Err(SimPLError::runtime("Invalid augmented assignment", 0)),
                };

                self.env.borrow_mut().update(name, result);
                Ok(None)
            }
            Stmt::If { condition, then_body, elif_clauses, else_body } => {
                let cond = self.eval_expr(condition)?;
                if cond.is_truthy() {
                    return self.execute_block(then_body).map(|v| Some(ControlFlow::Return(v)));
                }

                for (elif_cond, elif_body) in elif_clauses {
                    let ec = self.eval_expr(elif_cond)?;
                    if ec.is_truthy() {
                        return self.execute_block(elif_body).map(|v| Some(ControlFlow::Return(v)));
                    }
                }

                if let Some(else_body) = else_body {
                    return self.execute_block(else_body).map(|v| Some(ControlFlow::Return(v)));
                }

                Ok(None)
            }
            Stmt::For { var, iterable, body } => {
                let iter_val = self.eval_expr(iterable)?;
                match iter_val {
                    SimPLValue::List(items) => {
                        for item in items {
                            self.env.borrow_mut().define(var, item);
                            match self.execute_block(body) {
                                Ok(_) => {}
                                Err(SimPLError::Runtime { message, line: _ }) => {
                                    if message == "__break__" { break; }
                                    if message == "__continue__" { continue; }
                                    return Err(SimPLError::runtime(message, 0));
                                }
                                Err(e) => return Err(e),
                            }
                        }
                    }
                    SimPLValue::Dict(map) => {
                        for key in map.keys() {
                            self.env.borrow_mut().define(var, SimPLValue::String(key.clone()));
                            match self.execute_block(body) {
                                Ok(_) => {}
                                Err(SimPLError::Runtime { message, line: _ }) => {
                                    if message == "__break__" { break; }
                                    if message == "__continue__" { continue; }
                                    return Err(SimPLError::runtime(message, 0));
                                }
                                Err(e) => return Err(e),
                            }
                        }
                    }
                    SimPLValue::String(s) => {
                        for ch in s.chars() {
                            self.env.borrow_mut().define(var, SimPLValue::String(ch.to_string()));
                            match self.execute_block(body) {
                                Ok(_) => {}
                                Err(SimPLError::Runtime { message, line: _ }) => {
                                    if message == "__break__" { break; }
                                    if message == "__continue__" { continue; }
                                    return Err(SimPLError::runtime(message, 0));
                                }
                                Err(e) => return Err(e),
                            }
                        }
                    }
                    _ => return Err(SimPLError::runtime(format!("Cannot iterate over {}", iter_val.type_name()), 0)),
                }
                Ok(None)
            }
            Stmt::While { condition, body } => {
                loop {
                    let cond = self.eval_expr(condition)?;
                    if !cond.is_truthy() { break; }
                    match self.execute_block(body) {
                        Ok(_) => {}
                        Err(SimPLError::Runtime { message, line: _ }) => {
                            if message == "__break__" { break; }
                            if message == "__continue__" { continue; }
                            return Err(SimPLError::runtime(message, 0));
                        }
                        Err(e) => return Err(e),
                    }
                }
                Ok(None)
            }
            Stmt::FuncDef { name, params, defaults, body } => {
                let func = SimPLValue::Func {
                    name: name.clone(),
                    params: params.clone(),
                    defaults: defaults.clone(),
                    body: body.clone(),
                    closure: Environment::new(),
                };
                self.env.borrow_mut().define(name, func);
                Ok(None)
            }
            Stmt::Return { value } => {
                let val = if let Some(expr) = value {
                    Some(self.eval_expr(expr)?)
                } else {
                    None
                };
                Ok(Some(ControlFlow::Return(val)))
            }
            Stmt::Break => Err(SimPLError::runtime("__break__", 0)),
            Stmt::Continue => Err(SimPLError::runtime("__continue__", 0)),
            Stmt::Try { try_body, catch_var, catch_body, finally_body } => {
                let result = self.execute_block(try_body);
                match result {
                    Err(e) => {
                        let err_val = SimPLValue::String(e.to_string());
                        self.env.borrow_mut().define(catch_var, err_val);
                        self.execute_block(catch_body)?;
                    }
                    Ok(_) => {}
                }
                if let Some(finally_body) = finally_body {
                    self.execute_block(finally_body)?;
                }
                Ok(None)
            }
            Stmt::Raise { value } => {
                let val = self.eval_expr(value)?;
                Err(SimPLError::runtime(format!("{}", val), 0))
            }
            Stmt::Import { module, alias } => {
                let var_name = alias.as_deref().unwrap_or(module);
                // Try to load from stdlib
                let stdlib_path = format!("stdlib/{}.simpl", module);
                if let Ok(content) = std::fs::read_to_string(&stdlib_path) {
                    let mut child_env = Rc::new(RefCell::new(Environment::with_parent(self.env.clone())));
                    let mut child_interp = Interpreter::new();
                    child_interp.env = child_env.clone();
                    child_interp.run(&content)?;
                    let module_vars = child_interp.env.borrow().all_vars();
                    self.env.borrow_mut().define(var_name, SimPLValue::Module(module_vars));
                } else {
                    return Err(SimPLError::runtime(format!("Module '{}' not found", module), 0));
                }
                Ok(None)
            }
            Stmt::ExprStmt { expr } => {
                self.eval_expr(expr)?;
                Ok(None)
            }
            Stmt::Block { body } => {
                self.execute_block(body)?;
                Ok(None)
            }
        }
    }

    fn eval_expr(&mut self, expr: &Expr) -> Result<SimPLValue, SimPLError> {
        match expr {
            Expr::Number(n) => Ok(SimPLValue::Number(*n)),
            Expr::StringLit(s) => Ok(SimPLValue::String(s.clone())),
            Expr::BoolLit(b) => Ok(SimPLValue::Bool(*b)),
            Expr::NullLit => Ok(SimPLValue::Null),
            Expr::Ident(name) => {
                self.env.borrow().get(name)
                    .ok_or_else(|| SimPLError::runtime(format!("Undefined variable '{}'", name), 0))
            }
            Expr::BinOp { left, op, right } => {
                let lval = self.eval_expr(left)?;
                let rval = self.eval_expr(right)?;
                self.eval_binop(&lval, op, &rval)
            }
            Expr::UnaryOp { op, operand } => {
                let val = self.eval_expr(operand)?;
                match op {
                    UnaryOperator::Negate => {
                        if let SimPLValue::Number(n) = val {
                            Ok(SimPLValue::Number(-n))
                        } else {
                            Err(SimPLError::runtime(format!("Cannot negate {}", val.type_name()), 0))
                        }
                    }
                    UnaryOperator::Not => Ok(SimPLValue::Bool(!val.is_truthy())),
                }
            }
            Expr::Call { callee, args } => {
                let arg_vals: Result<Vec<SimPLValue>, SimPLError> =
                    args.iter().map(|a| self.eval_expr(a)).collect();
                let arg_vals = arg_vals?;

                match callee.as_ref() {
                    Expr::Ident(name) => {
                        let func = self.env.borrow().get(name)
                            .ok_or_else(|| SimPLError::runtime(format!("Undefined function '{}'", name), 0))?;
                        self.call_function(func, arg_vals, name)
                    }
                    _ => {
                        let func = self.eval_expr(callee)?;
                        self.call_function(func, arg_vals, "<lambda>")
                    }
                }
            }
            Expr::MethodCall { object, method, args } => {
                let obj = self.eval_expr(object)?;
                let arg_vals: Result<Vec<SimPLValue>, SimPLError> =
                    args.iter().map(|a| self.eval_expr(a)).collect();
                let arg_vals = arg_vals?;
                self.call_method(obj, method, arg_vals)
            }
            Expr::Index { object, index } => {
                let obj = self.eval_expr(object)?;
                let idx = self.eval_expr(index)?;
                match (&obj, &idx) {
                    (SimPLValue::List(items), SimPLValue::Number(n)) => {
                        let i = *n as usize;
                        if i < items.len() {
                            Ok(items[i].clone())
                        } else {
                            Err(SimPLError::runtime(format!("Index {} out of range", i), 0))
                        }
                    }
                    (SimPLValue::Dict(map), SimPLValue::String(key)) => {
                        map.get(key).cloned()
                            .ok_or_else(|| SimPLError::runtime(format!("Key '{}' not found in dict", key), 0))
                    }
                    (SimPLValue::String(s), SimPLValue::Number(n)) => {
                        let i = *n as usize;
                        let chars: Vec<char> = s.chars().collect();
                        if i < chars.len() {
                            Ok(SimPLValue::String(chars[i].to_string()))
                        } else {
                            Err(SimPLError::runtime(format!("Index {} out of range for string", i), 0))
                        }
                    }
                    (SimPLValue::HttpResponse { body, .. }, SimPLValue::String(key)) => {
                        match key.as_str() {
                            "status" => Ok(SimPLValue::Number(obj.extract_status() as f64)),
                            "body" => Ok(SimPLValue::String(body.clone())),
                            "headers" => {
                                if let SimPLValue::HttpResponse { headers, .. } = &obj {
                                    let mut map = HashMap::new();
                                    for (k, v) in headers {
                                        map.insert(k.clone(), SimPLValue::String(v.clone()));
                                    }
                                    Ok(SimPLValue::Dict(map))
                                } else { unreachable!() }
                            }
                            _ => Err(SimPLError::runtime(format!("HttpResponse has no property '{}'", key), 0)),
                        }
                    }
                    _ => Err(SimPLError::runtime(format!("Cannot index {} with {}", obj.type_name(), idx.type_name()), 0)),
                }
            }
            Expr::ListLit(elements) => {
                let mut vals = Vec::new();
                for e in elements {
                    vals.push(self.eval_expr(e)?);
                }
                Ok(SimPLValue::List(vals))
            }
            Expr::DictLit(pairs) => {
                let mut map = HashMap::new();
                for (key, val_expr) in pairs {
                    let val = self.eval_expr(val_expr)?;
                    map.insert(key.clone(), val);
                }
                Ok(SimPLValue::Dict(map))
            }
            Expr::Member { object, member } => {
                let obj = self.eval_expr(object)?;
                match (&obj, member.as_str()) {
                    (SimPLValue::HttpResponse { status, body, .. }, "status") => Ok(SimPLValue::Number(*status as f64)),
                    (SimPLValue::HttpResponse { body: b, .. }, "body") => Ok(SimPLValue::String(b.clone())),
                    (SimPLValue::Module(map), name) => {
                        map.get(name).cloned()
                            .ok_or_else(|| SimPLError::runtime(format!("Module has no member '{}'", name), 0))
                    }
                    (SimPLValue::Dict(map), name) => {
                        map.get(name).cloned()
                            .ok_or_else(|| SimPLError::runtime(format!("Dict has no key '{}'", name), 0))
                    }
                    _ => Err(SimPLError::runtime(format!("Cannot access member '{}' on {}", member, obj.type_name()), 0)),
                }
            }
            Expr::Lambda { .. } => {
                Err(SimPLError::runtime("Lambda expressions not yet supported", 0))
            }
            Expr::Ternary { .. } => {
                Err(SimPLError::runtime("Ternary expressions not yet supported", 0))
            }
        }
    }

    fn eval_binop(&self, left: &SimPLValue, op: &BinOperator, right: &SimPLValue) -> Result<SimPLValue, SimPLError> {
        match op {
            BinOperator::Add => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Number(a + b)),
                (SimPLValue::String(a), SimPLValue::String(b)) => Ok(SimPLValue::String(format!("{}{}", a, b))),
                (SimPLValue::String(a), b) => Ok(SimPLValue::String(format!("{}{}", a, b))),
                (a, SimPLValue::String(b)) => Ok(SimPLValue::String(format!("{}{}", a, b))),
                (SimPLValue::List(a), SimPLValue::List(b)) => {
                    let mut combined = a.clone();
                    combined.extend(b.clone());
                    Ok(SimPLValue::List(combined))
                }
                _ => Err(SimPLError::runtime(format!("Cannot add {} and {}", left.type_name(), right.type_name()), 0)),
            },
            BinOperator::Sub => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Number(a - b)),
                _ => Err(SimPLError::runtime(format!("Cannot subtract {} from {}", right.type_name(), left.type_name()), 0)),
            },
            BinOperator::Mul => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Number(a * b)),
                (SimPLValue::String(a), SimPLValue::Number(b)) => Ok(SimPLValue::String(a.repeat(*b as usize))),
                (SimPLValue::List(a), SimPLValue::Number(b)) => {
                    let mut combined = Vec::new();
                    for _ in 0..(*b as usize) {
                        combined.extend(a.clone());
                    }
                    Ok(SimPLValue::List(combined))
                }
                _ => Err(SimPLError::runtime(format!("Cannot multiply {} by {}", left.type_name(), right.type_name()), 0)),
            },
            BinOperator::Div => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => {
                    if *b == 0.0 { return Err(SimPLError::runtime("Division by zero", 0)); }
                    Ok(SimPLValue::Number(a / b))
                }
                _ => Err(SimPLError::runtime(format!("Cannot divide {} by {}", left.type_name(), right.type_name()), 0)),
            },
            BinOperator::Mod => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Number(a % b)),
                _ => Err(SimPLError::runtime("Modulo requires numbers", 0)),
            },
            BinOperator::Power => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Number(a.powf(*b))),
                _ => Err(SimPLError::runtime("Power requires numbers", 0)),
            },
            BinOperator::FloorDiv => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => {
                    if *b == 0.0 { return Err(SimPLError::runtime("Division by zero", 0)); }
                    Ok(SimPLValue::Number((a / b).floor()))
                }
                _ => Err(SimPLError::runtime("Floor division requires numbers", 0)),
            },
            BinOperator::Equal => Ok(SimPLValue::Bool(left == right)),
            BinOperator::NotEqual => Ok(SimPLValue::Bool(left != right)),
            BinOperator::Less => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Bool(a < b)),
                (SimPLValue::String(a), SimPLValue::String(b)) => Ok(SimPLValue::Bool(a < b)),
                _ => Err(SimPLError::runtime("Cannot compare with <", 0)),
            },
            BinOperator::LessEqual => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Bool(a <= b)),
                (SimPLValue::String(a), SimPLValue::String(b)) => Ok(SimPLValue::Bool(a <= b)),
                _ => Err(SimPLError::runtime("Cannot compare with <=", 0)),
            },
            BinOperator::Greater => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Bool(a > b)),
                (SimPLValue::String(a), SimPLValue::String(b)) => Ok(SimPLValue::Bool(a > b)),
                _ => Err(SimPLError::runtime("Cannot compare with >", 0)),
            },
            BinOperator::GreaterEqual => match (left, right) {
                (SimPLValue::Number(a), SimPLValue::Number(b)) => Ok(SimPLValue::Bool(a >= b)),
                (SimPLValue::String(a), SimPLValue::String(b)) => Ok(SimPLValue::Bool(a >= b)),
                _ => Err(SimPLError::runtime("Cannot compare with >=", 0)),
            },
            BinOperator::And => Ok(SimPLValue::Bool(left.is_truthy() && right.is_truthy())),
            BinOperator::Or => {
                if left.is_truthy() {
                    Ok(left.clone())
                } else {
                    Ok(right.clone())
                }
            }
        }
    }

    fn call_function(&mut self, func: SimPLValue, args: Vec<SimPLValue>, name: &str) -> Result<SimPLValue, SimPLError> {
        match func {
            SimPLValue::BuiltinFunc(bname) => self.call_builtin(&bname, args),
            SimPLValue::Func { params, defaults, body, closure, .. } => {
                let parent_env = Rc::new(RefCell::new(closure));
                let call_env = Rc::new(RefCell::new(Environment::with_parent(self.env.clone())));

                // Bind parameters
                for (i, param) in params.iter().enumerate() {
                    if i < args.len() {
                        call_env.borrow_mut().define(param, args[i].clone());
                    } else if let Some(Some(default_expr)) = defaults.get(i) {
                        // Evaluate default in the current environment
                        let val = self.eval_expr(default_expr)?;
                        call_env.borrow_mut().define(param, val);
                    } else {
                        return Err(SimPLError::runtime(
                            format!("Function '{}' expects {} arguments, got {}", name, params.len(), args.len()),
                            0,
                        ));
                    }
                }

                // Execute body in new scope
                let old_env = self.env.clone();
                self.env = call_env;
                let result = self.execute_block(&body);
                self.env = old_env;

                match result {
                    Ok(Some(val)) => Ok(val),
                    Ok(None) => Ok(SimPLValue::Null),
                    Err(SimPLError::Runtime { message, .. }) => {
                        if message == "__break__" || message == "__continue__" {
                            Err(SimPLError::runtime(format!("'{}' outside of loop", message.trim_matches('_')), 0))
                        } else {
                            Err(SimPLError::runtime(message, 0))
                        }
                    }
                    Err(e) => Err(e),
                }
            }
            _ => Err(SimPLError::runtime(format!("'{}' is not a function", name), 0)),
        }
    }

    fn call_method(&mut self, obj: SimPLValue, method: &str, args: Vec<SimPLValue>) -> Result<SimPLValue, SimPLError> {
        match (&obj, method) {
            // String methods
            (SimPLValue::String(s), "upper") => Ok(SimPLValue::String(s.to_uppercase())),
            (SimPLValue::String(s), "lower") => Ok(SimPLValue::String(s.to_lowercase())),
            (SimPLValue::String(s), "trim") => Ok(SimPLValue::String(s.trim().to_string())),
            (SimPLValue::String(s), "split") => {
                let sep = args.first().and_then(|v| if let SimPLValue::String(s) = v { Some(s.clone()) } else { None })
                    .unwrap_or_else(|| " ".to_string());
                let parts: Vec<SimPLValue> = s.split(&sep).map(|p| SimPLValue::String(p.to_string())).collect();
                Ok(SimPLValue::List(parts))
            }
            (SimPLValue::String(s), "replace") => {
                if args.len() >= 2 {
                    let from = match &args[0] { SimPLValue::String(s) => s.clone(), _ => return Err(SimPLError::runtime("replace() requires string arguments", 0)) };
                    let to = match &args[1] { SimPLValue::String(s) => s.clone(), _ => return Err(SimPLError::runtime("replace() requires string arguments", 0)) };
                    Ok(SimPLValue::String(s.replace(&from, &to)))
                } else {
                    Err(SimPLError::runtime("replace() requires 2 arguments", 0))
                }
            }
            (SimPLValue::String(s), "starts_with") => {
                if let Some(SimPLValue::String(prefix)) = args.first() {
                    Ok(SimPLValue::Bool(s.starts_with(prefix.as_str())))
                } else {
                    Err(SimPLError::runtime("starts_with() requires a string argument", 0))
                }
            }
            (SimPLValue::String(s), "ends_with") => {
                if let Some(SimPLValue::String(suffix)) = args.first() {
                    Ok(SimPLValue::Bool(s.ends_with(suffix.as_str())))
                } else {
                    Err(SimPLError::runtime("ends_with() requires a string argument", 0))
                }
            }
            (SimPLValue::String(s), "contains") => {
                if let Some(SimPLValue::String(substr)) = args.first() {
                    Ok(SimPLValue::Bool(s.contains(substr.as_str())))
                } else {
                    Err(SimPLError::runtime("contains() requires a string argument", 0))
                }
            }
            (SimPLValue::String(s), "reverse") => Ok(SimPLValue::String(s.chars().rev().collect())),
            (SimPLValue::String(s), "len") => Ok(SimPLValue::Number(s.len() as f64)),

            // List methods
            (SimPLValue::List(items), "push") => {
                let mut new_list = items.clone();
                if let Some(val) = args.first() {
                    new_list.push(val.clone());
                }
                Ok(SimPLValue::List(new_list))
            }
            (SimPLValue::List(items), "pop") => {
                let mut new_list = items.clone();
                match new_list.pop() {
                    Some(val) => Ok(val),
                    None => Err(SimPLError::runtime("Cannot pop from empty list", 0)),
                }
            }
            (SimPLValue::List(items), "len") => Ok(SimPLValue::Number(items.len() as f64)),
            (SimPLValue::List(items), "reverse") => Ok(SimPLValue::List(items.iter().cloned().rev().collect())),
            (SimPLValue::List(items), "sort") => {
                let mut new_list = items.clone();
                new_list.sort_by(|a, b| {
                    match (a, b) {
                        (SimPLValue::Number(x), SimPLValue::Number(y)) => x.partial_cmp(y).unwrap_or(std::cmp::Ordering::Equal),
                        (SimPLValue::String(x), SimPLValue::String(y)) => x.cmp(y),
                        _ => std::cmp::Ordering::Equal,
                    }
                });
                Ok(SimPLValue::List(new_list))
            }
            (SimPLValue::List(items), "join") => {
                let sep = args.first().and_then(|v| if let SimPLValue::String(s) = v { Some(s.clone()) } else { None })
                    .unwrap_or_else(|| ", ".to_string());
                let parts: Vec<String> = items.iter().map(|v| format!("{}", v)).collect();
                Ok(SimPLValue::String(parts.join(&sep)))
            }
            (SimPLValue::List(items), "contains") => {
                if let Some(val) = args.first() {
                    Ok(SimPLValue::Bool(items.contains(val)))
                } else {
                    Err(SimPLError::runtime("contains() requires an argument", 0))
                }
            }
            (SimPLValue::List(items), "slice") => {
                let start = args.first().and_then(|v| if let SimPLValue::Number(n) = v { Some(*n as usize) } else { None }).unwrap_or(0);
                let end = args.get(1).and_then(|v| if let SimPLValue::Number(n) = v { Some(*n as usize) } else { None }).unwrap_or(items.len());
                Ok(SimPLValue::List(items[start.min(items.len())..end.min(items.len())].to_vec()))
            }

            // Dict methods
            (SimPLValue::Dict(map), "keys") => {
                let keys: Vec<SimPLValue> = map.keys().map(|k| SimPLValue::String(k.clone())).collect();
                Ok(SimPLValue::List(keys))
            }
            (SimPLValue::Dict(map), "values") => {
                let values: Vec<SimPLValue> = map.values().cloned().collect();
                Ok(SimPLValue::List(values))
            }
            (SimPLValue::Dict(map), "has") => {
                if let Some(SimPLValue::String(key)) = args.first() {
                    Ok(SimPLValue::Bool(map.contains_key(key)))
                } else {
                    Err(SimPLError::runtime("has() requires a string key", 0))
                }
            }
            (SimPLValue::Dict(map), "len") => Ok(SimPLValue::Number(map.len() as f64)),
            (SimPLValue::Dict(map), "remove") => {
                let mut new_map = map.clone();
                if let Some(SimPLValue::String(key)) = args.first() {
                    new_map.remove(key);
                    Ok(SimPLValue::Dict(new_map))
                } else {
                    Err(SimPLError::runtime("remove() requires a string key", 0))
                }
            }
            (SimPLValue::Dict(map), "merge") => {
                let mut new_map = map.clone();
                if let Some(SimPLValue::Dict(other)) = args.first() {
                    for (k, v) in other {
                        new_map.insert(k.clone(), v.clone());
                    }
                }
                Ok(SimPLValue::Dict(new_map))
            }

            // HttpResponse methods
            (SimPLValue::HttpResponse { .. }, "json") => {
                if let SimPLValue::HttpResponse { body, .. } = &obj {
                    let parsed: Result<serde_json::Value, _> = serde_json::from_str(body);
                    match parsed {
                        Ok(v) => Ok(json_to_simpl(v)),
                        Err(_) => Err(SimPLError::runtime("Response body is not valid JSON", 0)),
                    }
                } else { unreachable!() }
            }
            (SimPLValue::HttpResponse { status, .. }, "ok") => Ok(SimPLValue::Bool(*status >= 200 && *status < 300)),

            _ => Err(SimPLError::runtime(format!("No method '{}' on {}", method, obj.type_name()), 0)),
        }
    }

    fn call_builtin(&mut self, name: &str, args: Vec<SimPLValue>) -> Result<SimPLValue, SimPLError> {
        match name {
            "say" => {
                let output = args.first().map(|v| format!("{}", v)).unwrap_or_else(|| "null".to_string());
                println!("{}", output);
                Ok(SimPLValue::Null)
            }
            "input" => {
                let prompt = args.first().map(|v| format!("{}", v)).unwrap_or_default();
                print!("{}", prompt);
                io::stdout().flush().map_err(|e| SimPLError::io(e.to_string()))?;
                let mut buf = String::new();
                io::stdin().read_line(&mut buf).map_err(|e| SimPLError::io(e.to_string()))?;
                Ok(SimPLValue::String(buf.trim_end().to_string()))
            }
            "type" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("type() requires 1 argument", 0))?;
                Ok(SimPLValue::String(val.type_name().to_string()))
            }
            "len" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("len() requires 1 argument", 0))?;
                match val {
                    SimPLValue::String(s) => Ok(SimPLValue::Number(s.len() as f64)),
                    SimPLValue::List(l) => Ok(SimPLValue::Number(l.len() as f64)),
                    SimPLValue::Dict(d) => Ok(SimPLValue::Number(d.len() as f64)),
                    _ => Err(SimPLError::runtime(format!("len() not supported for {}", val.type_name()), 0)),
                }
            }
            "str" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("str() requires 1 argument", 0))?;
                Ok(SimPLValue::String(format!("{}", val)))
            }
            "num" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("num() requires 1 argument", 0))?;
                match val {
                    SimPLValue::Number(n) => Ok(SimPLValue::Number(*n)),
                    SimPLValue::String(s) => {
                        s.parse::<f64>().map(SimPLValue::Number)
                            .map_err(|_| SimPLError::runtime(format!("Cannot convert '{}' to number", s), 0))
                    }
                    SimPLValue::Bool(b) => Ok(SimPLValue::Number(if *b { 1.0 } else { 0.0 })),
                    _ => Err(SimPLError::runtime(format!("Cannot convert {} to number", val.type_name()), 0)),
                }
            }
            "int" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("int() requires 1 argument", 0))?;
                match val {
                    SimPLValue::Number(n) => Ok(SimPLValue::Number(n.floor())),
                    SimPLValue::String(s) => {
                        s.parse::<f64>().map(|n| SimPLValue::Number(n.floor()))
                            .map_err(|_| SimPLError::runtime(format!("Cannot convert '{}' to int", s), 0))
                    }
                    _ => Err(SimPLError::runtime(format!("Cannot convert {} to int", val.type_name()), 0)),
                }
            }
            "bool" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("bool() requires 1 argument", 0))?;
                Ok(SimPLValue::Bool(val.is_truthy()))
            }
            "list" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("list() requires 1 argument", 0))?;
                match val {
                    SimPLValue::List(_) => Ok(val.clone()),
                    SimPLValue::String(s) => {
                        Ok(SimPLValue::List(s.chars().map(|c| SimPLValue::String(c.to_string())).collect()))
                    }
                    SimPLValue::Dict(map) => {
                        Ok(SimPLValue::List(map.keys().map(|k| SimPLValue::String(k.clone())).collect()))
                    }
                    _ => Ok(SimPLValue::List(vec![val.clone()])),
                }
            }
            "dict" => {
                Ok(SimPLValue::Dict(HashMap::new()))
            }
            "range" => {
                let (start, end, step) = match args.len() {
                    1 => {
                        let end = match &args[0] {
                            SimPLValue::Number(n) => *n as i64,
                            _ => return Err(SimPLError::runtime("range() requires numbers", 0)),
                        };
                        (0, end, 1)
                    }
                    2 => {
                        let start = match &args[0] {
                            SimPLValue::Number(n) => *n as i64,
                            _ => return Err(SimPLError::runtime("range() requires numbers", 0)),
                        };
                        let end = match &args[1] {
                            SimPLValue::Number(n) => *n as i64,
                            _ => return Err(SimPLError::runtime("range() requires numbers", 0)),
                        };
                        (start, end, 1)
                    }
                    3 => {
                        let start = match &args[0] { SimPLValue::Number(n) => *n as i64, _ => return Err(SimPLError::runtime("range() requires numbers", 0)) };
                        let end = match &args[1] { SimPLValue::Number(n) => *n as i64, _ => return Err(SimPLError::runtime("range() requires numbers", 0)) };
                        let step = match &args[2] { SimPLValue::Number(n) => *n as i64, _ => return Err(SimPLError::runtime("range() requires numbers", 0)) };
                        (start, end, step)
                    }
                    _ => return Err(SimPLError::runtime("range() requires 1-3 arguments", 0)),
                };
                let mut items = Vec::new();
                if step > 0 {
                    let mut i = start;
                    while i < end {
                        items.push(SimPLValue::Number(i as f64));
                        i += step;
                    }
                } else if step < 0 {
                    let mut i = start;
                    while i > end {
                        items.push(SimPLValue::Number(i as f64));
                        i += step;
                    }
                }
                Ok(SimPLValue::List(items))
            }
            "push" => {
                if args.len() < 2 {
                    return Err(SimPLError::runtime("push() requires a list and a value", 0));
                }
                if let SimPLValue::List(ref mut items) = args[0].clone() {
                    // Can't mutate in place through builtin, return new list
                    let mut new_list = items.clone();
                    new_list.push(args[1].clone());
                    Ok(SimPLValue::List(new_list))
                } else {
                    Err(SimPLError::runtime("push() first argument must be a list", 0))
                }
            }
            "pop" => {
                if let SimPLValue::List(ref mut items) = args[0].clone() {
                    let mut new_list = items.clone();
                    match new_list.pop() {
                        Some(val) => Ok(val),
                        None => Err(SimPLError::runtime("Cannot pop from empty list", 0)),
                    }
                } else {
                    Err(SimPLError::runtime("pop() requires a list", 0))
                }
            }
            "keys" => {
                if let SimPLValue::Dict(map) = &args[0] {
                    Ok(SimPLValue::List(map.keys().map(|k| SimPLValue::String(k.clone())).collect()))
                } else {
                    Err(SimPLError::runtime("keys() requires a dict", 0))
                }
            }
            "values" => {
                if let SimPLValue::Dict(map) = &args[0] {
                    Ok(SimPLValue::List(map.values().cloned().collect()))
                } else {
                    Err(SimPLError::runtime("values() requires a dict", 0))
                }
            }
            "has" => {
                if args.len() < 2 { return Err(SimPLError::runtime("has() requires 2 arguments", 0)); }
                match &args[0] {
                    SimPLValue::Dict(map) => {
                        if let SimPLValue::String(key) = &args[1] {
                            Ok(SimPLValue::Bool(map.contains_key(key)))
                        } else {
                            Err(SimPLError::runtime("has() key must be a string", 0))
                        }
                    }
                    SimPLValue::List(items) => Ok(SimPLValue::Bool(items.contains(&args[1]))),
                    SimPLValue::String(s) => {
                        if let SimPLValue::String(substr) = &args[1] {
                            Ok(SimPLValue::Bool(s.contains(substr.as_str())))
                        } else {
                            Err(SimPLError::runtime("has() substring must be a string", 0))
                        }
                    }
                    _ => Err(SimPLError::runtime("has() not supported for this type", 0)),
                }
            }
            "abs" => {
                if let SimPLValue::Number(n) = args.first().ok_or_else(|| SimPLError::runtime("abs() requires 1 argument", 0))? {
                    Ok(SimPLValue::Number(n.abs()))
                } else {
                    Err(SimPLError::runtime("abs() requires a number", 0))
                }
            }
            "floor" => {
                if let SimPLValue::Number(n) = args.first().ok_or_else(|| SimPLError::runtime("floor() requires 1 argument", 0))? {
                    Ok(SimPLValue::Number(n.floor()))
                } else {
                    Err(SimPLError::runtime("floor() requires a number", 0))
                }
            }
            "ceil" => {
                if let SimPLValue::Number(n) = args.first().ok_or_else(|| SimPLError::runtime("ceil() requires 1 argument", 0))? {
                    Ok(SimPLValue::Number(n.ceil()))
                } else {
                    Err(SimPLError::runtime("ceil() requires a number", 0))
                }
            }
            "round" => {
                if let SimPLValue::Number(n) = args.first().ok_or_else(|| SimPLError::runtime("round() requires 1 argument", 0))? {
                    Ok(SimPLValue::Number(n.round()))
                } else {
                    Err(SimPLError::runtime("round() requires a number", 0))
                }
            }
            "sqrt" => {
                if let SimPLValue::Number(n) = args.first().ok_or_else(|| SimPLError::runtime("sqrt() requires 1 argument", 0))? {
                    Ok(SimPLValue::Number(n.sqrt()))
                } else {
                    Err(SimPLError::runtime("sqrt() requires a number", 0))
                }
            }
            "pow" => {
                if args.len() < 2 { return Err(SimPLError::runtime("pow() requires 2 arguments", 0)); }
                if let (SimPLValue::Number(a), SimPLValue::Number(b)) = (&args[0], &args[1]) {
                    Ok(SimPLValue::Number(a.powf(*b)))
                } else {
                    Err(SimPLError::runtime("pow() requires numbers", 0))
                }
            }
            "min" => {
                if let SimPLValue::List(items) = args.first().ok_or_else(|| SimPLError::runtime("min() requires a list", 0))? {
                    let nums: Vec<f64> = items.iter().filter_map(|v| if let SimPLValue::Number(n) = v { Some(*n) } else { None }).collect();
                    nums.iter().cloned().reduce(f64::min)
                        .map(SimPLValue::Number)
                        .ok_or_else(|| SimPLError::runtime("min() list has no numbers", 0))
                } else {
                    Err(SimPLError::runtime("min() requires a list of numbers", 0))
                }
            }
            "max" => {
                if let SimPLValue::List(items) = args.first().ok_or_else(|| SimPLError::runtime("max() requires a list", 0))? {
                    let nums: Vec<f64> = items.iter().filter_map(|v| if let SimPLValue::Number(n) = v { Some(*n) } else { None }).collect();
                    nums.iter().cloned().reduce(f64::max)
                        .map(SimPLValue::Number)
                        .ok_or_else(|| SimPLError::runtime("max() list has no numbers", 0))
                } else {
                    Err(SimPLError::runtime("max() requires a list of numbers", 0))
                }
            }
            "random" => {
                use std::time::SystemTime;
                let seed = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos();
                let val = ((seed as f64 * 12.9898 + 78.233).sin() * 43758.5453).fract().abs();
                if let Some(SimPLValue::Number(max)) = args.first() {
                    Ok(SimPLValue::Number((val * max).floor()))
                } else {
                    Ok(SimPLValue::Number(val))
                }
            }
            "upper" | "lower" | "trim" | "split" | "join" | "replace" | "starts_with" | "ends_with" | "contains" | "reverse" | "sort" | "slice" => {
                // These are method-style builtins, also callable as functions
                if args.is_empty() {
                    return Err(SimPLError::runtime(format!("{}() requires arguments", name), 0));
                }
                let obj = args[0].clone();
                let method_args = args[1..].to_vec();
                self.call_method(obj, name, method_args)
            }
            "http_get" => {
                let url = args.first().ok_or_else(|| SimPLError::runtime("http_get() requires a URL", 0))?;
                if let SimPLValue::String(url_str) = url {
                    self.http_get(&url_str)
                } else {
                    Err(SimPLError::runtime("http_get() URL must be a string", 0))
                }
            }
            "http_post" => {
                if args.len() < 2 {
                    return Err(SimPLError::runtime("http_post() requires URL and body", 0));
                }
                let url = match &args[0] { SimPLValue::String(s) => s.clone(), _ => return Err(SimPLError::runtime("http_post() URL must be a string", 0)) };
                let body = match &args[1] {
                    SimPLValue::String(s) => s.clone(),
                    other => other.to_json_string(),
                };
                self.http_post(&url, &body)
            }
            "json_parse" => {
                let json_str = args.first().ok_or_else(|| SimPLError::runtime("json_parse() requires a string", 0))?;
                if let SimPLValue::String(s) = json_str {
                    let parsed: Result<serde_json::Value, _> = serde_json::from_str(&s);
                    match parsed {
                        Ok(v) => Ok(json_to_simpl(v)),
                        Err(e) => Err(SimPLError::runtime(format!("Invalid JSON: {}", e), 0)),
                    }
                } else {
                    Err(SimPLError::runtime("json_parse() requires a string", 0))
                }
            }
            "json_stringify" => {
                let val = args.first().ok_or_else(|| SimPLError::runtime("json_stringify() requires a value", 0))?;
                Ok(SimPLValue::String(val.to_json_string()))
            }
            "time" => {
                use std::time::SystemTime;
                let now = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs();
                Ok(SimPLValue::Number(now as f64))
            }
            "sleep" => {
                if let Some(SimPLValue::Number(ms)) = args.first() {
                    std::thread::sleep(std::time::Duration::from_millis(*ms as u64));
                    Ok(SimPLValue::Null)
                } else {
                    Err(SimPLError::runtime("sleep() requires a number (milliseconds)", 0))
                }
            }
            "shell" => {
                if let Some(SimPLValue::String(cmd)) = args.first() {
                    let output = std::process::Command::new("sh")
                        .arg("-c")
                        .arg(&cmd)
                        .output();
                    match output {
                        Ok(out) => {
                            let stdout = String::from_utf8_lossy(&out.stdout).to_string();
                            let stderr = String::from_utf8_lossy(&out.stderr).to_string();
                            let mut result = HashMap::new();
                            result.insert("stdout".into(), SimPLValue::String(stdout));
                            result.insert("stderr".into(), SimPLValue::String(stderr));
                            result.insert("exit_code".into(), SimPLValue::Number(out.status.code().unwrap_or(-1) as f64));
                            Ok(SimPLValue::Dict(result))
                        }
                        Err(e) => Err(SimPLError::runtime(format!("Shell command failed: {}", e), 0)),
                    }
                } else {
                    Err(SimPLError::runtime("shell() requires a string command", 0))
                }
            }
            _ => Err(SimPLError::runtime(format!("Unknown builtin '{}'", name), 0)),
        }
    }

    fn http_get(&self, url: &str) -> Result<SimPLValue, SimPLError> {
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| SimPLError::runtime(format!("HTTP client error: {}", e), 0))?;

        let resp = client.get(url).send()
            .map_err(|e| SimPLError::runtime(format!("HTTP GET failed: {}", e), 0))?;

        let status = resp.status().as_u16();
        let headers: HashMap<String, String> = resp.headers().iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        let body = resp.text().unwrap_or_default();

        Ok(SimPLValue::HttpResponse { status, headers, body })
    }

    fn http_post(&self, url: &str, body: &str) -> Result<SimPLValue, SimPLError> {
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| SimPLError::runtime(format!("HTTP client error: {}", e), 0))?;

        let resp = client.post(url)
            .header("Content-Type", "application/json")
            .body(body.to_string())
            .send()
            .map_err(|e| SimPLError::runtime(format!("HTTP POST failed: {}", e), 0))?;

        let status = resp.status().as_u16();
        let headers: HashMap<String, String> = resp.headers().iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        let resp_body = resp.text().unwrap_or_default();

        Ok(SimPLValue::HttpResponse { status, headers, body: resp_body })
    }
}

// Helper: convert serde_json::Value to SimPLValue
fn json_to_simpl(val: serde_json::Value) -> SimPLValue {
    match val {
        serde_json::Value::Null => SimPLValue::Null,
        serde_json::Value::Bool(b) => SimPLValue::Bool(b),
        serde_json::Value::Number(n) => {
            if let Some(f) = n.as_f64() {
                SimPLValue::Number(f)
            } else {
                SimPLValue::Null
            }
        }
        serde_json::Value::String(s) => SimPLValue::String(s),
        serde_json::Value::Array(arr) => {
            SimPLValue::List(arr.into_iter().map(json_to_simpl).collect())
        }
        serde_json::Value::Object(obj) => {
            let mut map = HashMap::new();
            for (k, v) in obj {
                map.insert(k, json_to_simpl(v));
            }
            SimPLValue::Dict(map)
        }
    }
}

impl SimPLValue {
    fn extract_status(&self) -> u16 {
        if let SimPLValue::HttpResponse { status, .. } = self {
            *status
        } else {
            0
        }
    }
}
