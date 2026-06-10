pub mod ast;

pub use ast::{BinOperator, Expr, Stmt, UnaryOperator, ControlFlow};

use crate::error::SimPLError;
use crate::lexer::token::{Token, TokenType};

pub struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}

impl Parser {
    pub fn new(tokens: Vec<Token>) -> Self {
        Parser { tokens, pos: 0 }
    }

    fn peek(&self) -> &Token {
        self.tokens.get(self.pos).unwrap_or_else(|| {
            static EOF: Token = Token { token_type: TokenType::Eof, lexeme: String::new(), line: 0, column: 0 };
            &EOF
        })
    }

    fn advance(&mut self) -> Token {
        let tok = self.peek().clone();
        if self.pos < self.tokens.len() - 1 {
            self.pos += 1;
        }
        tok
    }

    fn check(&self, token_type: &TokenType) -> bool {
        &self.peek().token_type == token_type
    }

    fn match_token(&mut self, token_type: &TokenType) -> Option<Token> {
        if self.check(token_type) {
            Some(self.advance())
        } else {
            None
        }
    }

    fn expect(&mut self, token_type: &TokenType, message: &str) -> Result<Token, SimPLError> {
        if self.check(token_type) {
            Ok(self.advance())
        } else {
            let tok = self.peek();
            Err(SimPLError::parser(
                format!("Expected {}, got '{}'. {}", token_type, tok.lexeme, message),
                tok.line,
                tok.column,
            ))
        }
    }

    fn skip_newlines(&mut self) {
        while self.check(&TokenType::Newline) {
            self.advance();
        }
    }

    fn consume_newlines_or_brace(&mut self) -> Result<(), SimPLError> {
        self.skip_newlines();
        Ok(())
    }

    pub fn parse(&mut self) -> Result<Vec<Stmt>, SimPLError> {
        let mut statements = Vec::new();
        self.skip_newlines();

        while !self.check(&TokenType::Eof) {
            statements.push(self.parse_statement()?);
            self.skip_newlines();
        }

        Ok(statements)
    }

    fn parse_statement(&mut self) -> Result<Stmt, SimPLError> {
        match &self.peek().token_type {
            TokenType::Say => self.parse_say(),
            TokenType::Set => self.parse_set(),
            TokenType::If => self.parse_if(),
            TokenType::For => self.parse_for(),
            TokenType::While => self.parse_while(),
            TokenType::Func => self.parse_func_def(),
            TokenType::Return => self.parse_return(),
            TokenType::Break => {
                self.advance();
                Ok(Stmt::Break)
            }
            TokenType::Continue => {
                self.advance();
                Ok(Stmt::Continue)
            }
            TokenType::Try => self.parse_try(),
            TokenType::Raise => self.parse_raise(),
            TokenType::Import => self.parse_import(),
            _ => self.parse_expr_stmt(),
        }
    }

    fn parse_say(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'say'
        let value = self.parse_expression()?;
        Ok(Stmt::Say { value })
    }

    fn parse_set(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'set'
        let name_tok = self.expect(&TokenType::Ident, "Expected variable name after 'set'")?;
        let name = name_tok.lexeme.clone();

        // Check for index assignment: set x[0] = 5
        if self.check(&TokenType::LBracket) {
            self.advance();
            let index = self.parse_expression()?;
            self.expect(&TokenType::RBracket, "Expected ']' after index")?;
            self.expect(&TokenType::Equal, "Expected '=' after index")?;
            let value = self.parse_expression()?;
            return Ok(Stmt::IndexAssign {
                object: Expr::Ident(name),
                index,
                value,
            });
        }

        // Check for member assignment: set x.name = 5
        if self.check(&TokenType::Dot) {
            self.advance();
            let member_tok = self.expect(&TokenType::Ident, "Expected member name after '.'")?;
            self.expect(&TokenType::Equal, "Expected '=' after member name")?;
            let value = self.parse_expression()?;
            return Ok(Stmt::MemberAssign {
                object: Expr::Ident(name),
                member: member_tok.lexeme.clone(),
                value,
            });
        }

        self.expect(&TokenType::Equal, "Expected '=' after variable name")?;
        let value = self.parse_expression()?;
        Ok(Stmt::Assign { name, value })
    }

    fn parse_if(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'if'
        let condition = self.parse_expression()?;
        self.consume_newlines_or_brace()?;
        let then_body = self.parse_block()?;

        let mut elif_clauses = Vec::new();
        while self.check(&TokenType::Elif) {
            self.advance();
            let elif_cond = self.parse_expression()?;
            self.consume_newlines_or_brace()?;
            let elif_body = self.parse_block()?;
            elif_clauses.push((elif_cond, elif_body));
        }

        let else_body = if self.check(&TokenType::Else) {
            self.advance();
            self.consume_newlines_or_brace()?;
            Some(self.parse_block()?)
        } else {
            None
        };

        Ok(Stmt::If {
            condition,
            then_body,
            elif_clauses,
            else_body,
        })
    }

    fn parse_for(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'for'
        let var_tok = self.expect(&TokenType::Ident, "Expected variable name after 'for'")?;
        let var = var_tok.lexeme.clone();
        self.expect(&TokenType::In, "Expected 'in' after variable name")?;
        let iterable = self.parse_expression()?;
        self.consume_newlines_or_brace()?;
        let body = self.parse_block()?;
        Ok(Stmt::For { var, iterable, body })
    }

    fn parse_while(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'while'
        let condition = self.parse_expression()?;
        self.consume_newlines_or_brace()?;
        let body = self.parse_block()?;
        Ok(Stmt::While { condition, body })
    }

    fn parse_func_def(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'func'
        let name_tok = self.expect(&TokenType::Ident, "Expected function name after 'func'")?;
        let name = name_tok.lexeme.clone();
        self.expect(&TokenType::LParen, "Expected '(' after function name")?;

        let mut params = Vec::new();
        let mut defaults = Vec::new();

        if !self.check(&TokenType::RParen) {
            loop {
                let param_tok = self.expect(&TokenType::Ident, "Expected parameter name")?;
                params.push(param_tok.lexeme.clone());

                if self.match_token(&TokenType::Equal).is_some() {
                    let default_val = self.parse_expression()?;
                    defaults.push(Some(default_val));
                } else {
                    defaults.push(None);
                }

                if self.match_token(&TokenType::Comma).is_none() {
                    break;
                }
            }
        }

        self.expect(&TokenType::RParen, "Expected ')' after parameters")?;
        self.consume_newlines_or_brace()?;
        let body = self.parse_block()?;

        Ok(Stmt::FuncDef { name, params, defaults, body })
    }

    fn parse_return(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'return'
        let value = if self.check(&TokenType::Newline) || self.check(&TokenType::Eof) || self.check(&TokenType::RBrace) {
            None
        } else {
            Some(self.parse_expression()?)
        };
        Ok(Stmt::Return { value })
    }

    fn parse_try(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'try'
        self.skip_newlines();
        self.consume_newlines_or_brace()?;
        let try_body = self.parse_block()?;
        self.skip_newlines();

        let catch_var = if self.check(&TokenType::Catch) {
            self.advance();
            let var_tok = self.expect(&TokenType::Ident, "Expected variable name after 'catch'")?;
            var_tok.lexeme.clone()
        } else {
            "err".to_string()
        };
        self.skip_newlines();
        self.consume_newlines_or_brace()?;
        let catch_body = self.parse_block()?;
        self.skip_newlines();

        let finally_body = if self.check(&TokenType::Finally) {
            self.advance();
            self.consume_newlines_or_brace()?;
            Some(self.parse_block()?)
        } else {
            None
        };

        Ok(Stmt::Try {
            try_body,
            catch_var,
            catch_body,
            finally_body,
        })
    }

    fn parse_raise(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'raise'
        let value = self.parse_expression()?;
        Ok(Stmt::Raise { value })
    }

    fn parse_import(&mut self) -> Result<Stmt, SimPLError> {
        self.advance(); // consume 'import'
        let module_tok = self.expect(&TokenType::Ident, "Expected module name after 'import'")?;
        let module = module_tok.lexeme.clone();

        let alias = if self.check(&TokenType::As) {
            self.advance();
            let alias_tok = self.expect(&TokenType::Ident, "Expected alias after 'as'")?;
            Some(alias_tok.lexeme.clone())
        } else {
            None
        };

        Ok(Stmt::Import { module, alias })
    }

    fn parse_expr_stmt(&mut self) -> Result<Stmt, SimPLError> {
        let expr = self.parse_expression()?;

        // Check for assignment: ident = expr
        if let Expr::Ident(name) = &expr {
            if self.check(&TokenType::Equal) {
                self.advance();
                let value = self.parse_expression()?;
                return Ok(Stmt::Assign { name: name.clone(), value });
            }
            // Augmented assignment
            for tt in &[TokenType::PlusEqual, TokenType::MinusEqual, TokenType::StarEqual, TokenType::SlashEqual] {
                if self.check(tt) {
                    let op = self.advance().token_type.clone();
                    let value = self.parse_expression()?;
                    return Ok(Stmt::AugAssign { name: name.clone(), op, value });
                }
            }
        }

        // Check for index assignment: expr[index] = value
        if let Expr::Index { object, index } = &expr {
            if self.check(&TokenType::Equal) {
                self.advance();
                let value = self.parse_expression()?;
                return Ok(Stmt::IndexAssign {
                    object: *object.clone(),
                    index: *index.clone(),
                    value,
                });
            }
        }

        Ok(Stmt::ExprStmt { expr })
    }

    fn parse_block(&mut self) -> Result<Vec<Stmt>, SimPLError> {
        let mut stmts = Vec::new();

        // If we started with {, parse until }
        let has_brace = if self.check(&TokenType::LBrace) {
            self.advance();
            self.skip_newlines();
            true
        } else {
            false
        };

        let end_token = if has_brace {
            TokenType::RBrace
        } else {
            TokenType::End
        };

        loop {
            self.skip_newlines();
            // Check for 'end' keyword (block terminator without braces)
            if !has_brace && self.check(&TokenType::End) {
                self.advance(); // consume 'end'
                break;
            }
            if self.check(&end_token) || self.check(&TokenType::Eof) {
                if has_brace {
                    break;
                } else {
                    // Without braces and no 'end', we also stop at EOF
                    break;
                }
            }
            // Stop at keywords that end blocks
            if !has_brace && matches!(self.peek().token_type,
                TokenType::Else | TokenType::Elif | TokenType::Catch | TokenType::Finally
            ) {
                break;
            }

            stmts.push(self.parse_statement()?);
            self.skip_newlines();
        }

        if has_brace {
            self.expect(&TokenType::RBrace, "Expected '}' to close block")?;
        }

        Ok(stmts)
    }

    pub fn parse_expression(&mut self) -> Result<Expr, SimPLError> {
        self.parse_ternary()
    }

    fn parse_ternary(&mut self) -> Result<Expr, SimPLError> {
        let expr = self.parse_or()?;

        if self.check(&TokenType::Colon) {
            // Check if this looks like a dict literal (previous token was a key)
            // Don't parse as ternary in dict context
            return Ok(expr);
        }

        Ok(expr)
    }

    fn parse_or(&mut self) -> Result<Expr, SimPLError> {
        let mut left = self.parse_and()?;
        while self.match_token(&TokenType::Or).is_some() {
            let right = self.parse_and()?;
            left = Expr::BinOp {
                left: Box::new(left),
                op: BinOperator::Or,
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_and(&mut self) -> Result<Expr, SimPLError> {
        let mut left = self.parse_equality()?;
        while self.match_token(&TokenType::And).is_some() {
            let right = self.parse_equality()?;
            left = Expr::BinOp {
                left: Box::new(left),
                op: BinOperator::And,
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_equality(&mut self) -> Result<Expr, SimPLError> {
        let mut left = self.parse_comparison()?;
        loop {
            let op = if self.match_token(&TokenType::EqualEqual).is_some() {
                BinOperator::Equal
            } else if self.match_token(&TokenType::NotEqual).is_some() {
                BinOperator::NotEqual
            } else {
                break;
            };
            let right = self.parse_comparison()?;
            left = Expr::BinOp {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_comparison(&mut self) -> Result<Expr, SimPLError> {
        let mut left = self.parse_addition()?;
        loop {
            let op = if self.match_token(&TokenType::Less).is_some() {
                BinOperator::Less
            } else if self.match_token(&TokenType::LessEqual).is_some() {
                BinOperator::LessEqual
            } else if self.match_token(&TokenType::Greater).is_some() {
                BinOperator::Greater
            } else if self.match_token(&TokenType::GreaterEqual).is_some() {
                BinOperator::GreaterEqual
            } else {
                break;
            };
            let right = self.parse_addition()?;
            left = Expr::BinOp {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_addition(&mut self) -> Result<Expr, SimPLError> {
        let mut left = self.parse_multiplication()?;
        loop {
            let op = if self.match_token(&TokenType::Plus).is_some() {
                BinOperator::Add
            } else if self.match_token(&TokenType::Minus).is_some() {
                BinOperator::Sub
            } else {
                break;
            };
            let right = self.parse_multiplication()?;
            left = Expr::BinOp {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_multiplication(&mut self) -> Result<Expr, SimPLError> {
        let mut left = self.parse_power()?;
        loop {
            let op = if self.match_token(&TokenType::Star).is_some() {
                BinOperator::Mul
            } else if self.match_token(&TokenType::Slash).is_some() {
                BinOperator::Div
            } else if self.match_token(&TokenType::Percent).is_some() {
                BinOperator::Mod
            } else if self.match_token(&TokenType::FloorDiv).is_some() {
                BinOperator::FloorDiv
            } else {
                break;
            };
            let right = self.parse_power()?;
            left = Expr::BinOp {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn parse_power(&mut self) -> Result<Expr, SimPLError> {
        let left = self.parse_unary()?;
        if self.match_token(&TokenType::Power).is_some() {
            let right = self.parse_unary()?; // Right-associative
            Ok(Expr::BinOp {
                left: Box::new(left),
                op: BinOperator::Power,
                right: Box::new(right),
            })
        } else {
            Ok(left)
        }
    }

    fn parse_unary(&mut self) -> Result<Expr, SimPLError> {
        if self.match_token(&TokenType::Minus).is_some() {
            let operand = self.parse_unary()?;
            Ok(Expr::UnaryOp {
                op: UnaryOperator::Negate,
                operand: Box::new(operand),
            })
        } else if self.match_token(&TokenType::Not).is_some() {
            let operand = self.parse_unary()?;
            Ok(Expr::UnaryOp {
                op: UnaryOperator::Not,
                operand: Box::new(operand),
            })
        } else {
            self.parse_call()
        }
    }

    fn parse_call(&mut self) -> Result<Expr, SimPLError> {
        let mut expr = self.parse_primary()?;

        loop {
            if self.check(&TokenType::LParen) {
                // Function call
                self.advance();
                let mut args = Vec::new();
                if !self.check(&TokenType::RParen) {
                    loop {
                        args.push(self.parse_expression()?);
                        if self.match_token(&TokenType::Comma).is_none() {
                            break;
                        }
                    }
                }
                self.expect(&TokenType::RParen, "Expected ')' after arguments")?;
                expr = Expr::Call {
                    callee: Box::new(expr),
                    args,
                };
            } else if self.check(&TokenType::Dot) {
                // Method call or member access
                self.advance();
                let member_tok = self.expect(&TokenType::Ident, "Expected member name after '.'")?;
                let member = member_tok.lexeme.clone();

                if self.check(&TokenType::LParen) {
                    // Method call
                    self.advance();
                    let mut args = Vec::new();
                    if !self.check(&TokenType::RParen) {
                        loop {
                            args.push(self.parse_expression()?);
                            if self.match_token(&TokenType::Comma).is_none() {
                                break;
                            }
                        }
                    }
                    self.expect(&TokenType::RParen, "Expected ')' after arguments")?;
                    expr = Expr::MethodCall {
                        object: Box::new(expr),
                        method: member,
                        args,
                    };
                } else {
                    // Member access
                    expr = Expr::Member {
                        object: Box::new(expr),
                        member,
                    };
                }
            } else if self.check(&TokenType::LBracket) {
                // Index access
                self.advance();
                let index = self.parse_expression()?;
                self.expect(&TokenType::RBracket, "Expected ']' after index")?;
                expr = Expr::Index {
                    object: Box::new(expr),
                    index: Box::new(index),
                };
            } else {
                break;
            }
        }

        Ok(expr)
    }

    fn parse_primary(&mut self) -> Result<Expr, SimPLError> {
        let tok = self.peek().clone();

        match &tok.token_type {
            TokenType::Number => {
                self.advance();
                let n: f64 = tok.lexeme.parse().map_err(|_| {
                    SimPLError::parser(format!("Invalid number: {}", tok.lexeme), tok.line, tok.column)
                })?;
                Ok(Expr::Number(n))
            }
            TokenType::String => {
                self.advance();
                Ok(Expr::StringLit(tok.lexeme.clone()))
            }
            TokenType::True => {
                self.advance();
                Ok(Expr::BoolLit(true))
            }
            TokenType::False => {
                self.advance();
                Ok(Expr::BoolLit(false))
            }
            TokenType::Null | TokenType::None => {
                self.advance();
                Ok(Expr::NullLit)
            }
            TokenType::Ident => {
                self.advance();
                Ok(Expr::Ident(tok.lexeme.clone()))
            }
            TokenType::LParen => {
                self.advance();
                let expr = self.parse_expression()?;
                self.expect(&TokenType::RParen, "Expected ')' after expression")?;
                Ok(expr)
            }
            TokenType::LBracket => {
                self.parse_list()
            }
            TokenType::LBrace => {
                self.parse_dict()
            }
            _ => Err(SimPLError::parser(
                format!("Unexpected token: '{}'", tok.lexeme),
                tok.line,
                tok.column,
            )),
        }
    }

    fn parse_list(&mut self) -> Result<Expr, SimPLError> {
        self.advance(); // consume '['
        self.skip_newlines();
        let mut elements = Vec::new();

        if !self.check(&TokenType::RBracket) {
            loop {
                self.skip_newlines();
                elements.push(self.parse_expression()?);
                self.skip_newlines();
                if self.match_token(&TokenType::Comma).is_none() {
                    break;
                }
            }
        }

        self.skip_newlines();
        self.expect(&TokenType::RBracket, "Expected ']' to close list")?;
        Ok(Expr::ListLit(elements))
    }

    fn parse_dict(&mut self) -> Result<Expr, SimPLError> {
        self.advance(); // consume '{'
        self.skip_newlines();
        let mut pairs = Vec::new();

        if !self.check(&TokenType::RBrace) {
            loop {
                self.skip_newlines();
                // Key can be a string literal or identifier
                let key = if self.check(&TokenType::String) {
                    let tok = self.advance();
                    tok.lexeme.clone()
                } else if self.check(&TokenType::Ident) {
                    let tok = self.advance();
                    tok.lexeme.clone()
                } else {
                    let tok = self.peek();
                    return Err(SimPLError::parser(
                        format!("Expected dictionary key, got '{}'", tok.lexeme),
                        tok.line,
                        tok.column,
                    ));
                };

                self.expect(&TokenType::Colon, "Expected ':' after dictionary key")?;
                let value = self.parse_expression()?;
                pairs.push((key, value));

                self.skip_newlines();
                if self.match_token(&TokenType::Comma).is_none() {
                    break;
                }
            }
        }

        self.skip_newlines();
        self.expect(&TokenType::RBrace, "Expected '}' to close dict")?;
        Ok(Expr::DictLit(pairs))
    }
}
