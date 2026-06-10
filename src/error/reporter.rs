use crate::error::SimPLError;
use colored::*;

pub fn report_error(err: &SimPLError) {
    match err {
        SimPLError::Lexer { message, line, column, source } => {
            eprintln!();
            eprintln!("  {} Lexer Error", "✖".red().bold());
            eprintln!();
            eprintln!("  {} (line {}, col {}): {}", "→".yellow(), line, column, message.white().bold());
            print_source_line(source, *line);
            eprintln!();
        }
        SimPLError::Parser { message, line, column } => {
            eprintln!();
            eprintln!("  {} Parse Error", "✖".red().bold());
            eprintln!();
            eprintln!("  {} (line {}, col {}): {}", "→".yellow(), line, column, message.white().bold());
            eprintln!();
        }
        SimPLError::Runtime { message, line } => {
            eprintln!();
            eprintln!("  {} Runtime Error", "✖".red().bold());
            eprintln!();
            eprintln!("  {} (line {}): {}", "→".yellow(), line, message.white().bold());
            eprintln!();
        }
        SimPLError::Package { message } => {
            eprintln!();
            eprintln!("  {} Package Error", "✖".red().bold());
            eprintln!();
            eprintln!("  {} {}", "→".yellow(), message.white().bold());
            eprintln!();
        }
        SimPLError::Io { message } => {
            eprintln!();
            eprintln!("  {} I/O Error", "✖".red().bold());
            eprintln!();
            eprintln!("  {} {}", "→".yellow(), message.white().bold());
            eprintln!();
        }
    }
}

fn print_source_line(source: &str, target_line: usize) {
    let lines: Vec<&str> = source.lines().collect();
    if target_line > 0 && target_line <= lines.len() {
        let line_content = lines[target_line - 1];
        eprintln!("    {} {}", format!("{} |", target_line).blue().dimmed(), line_content);
        eprintln!("    {}", "~".repeat(line_content.len() + 6).red());
    }
}
