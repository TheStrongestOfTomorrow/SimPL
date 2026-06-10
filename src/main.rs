mod lexer;
mod parser;
mod interpreter;
mod package;
mod tui;
mod error;

use std::fs;
use std::io::{self, Write};
use std::path::Path;

use clap::{Parser, Subcommand};
use colored::*;

use error::reporter::report_error;
use interpreter::Interpreter;

const VERSION: &str = "1.0.0";
const BANNER: &str = r#"
  ____                  _ _____
 / ___|  ___  _ __  __| |_   _| __ __ _  ___
 \___ \ / _ \| '_ \/ _` | | || '__/ _` |/ _ \
  ___) | (_) | | | (_| | | || | | (_| |  __/
 |____/ \___/|_|  \__,_| |_||_|  \__,_|\___|
                                    vVERSION
"#;

#[derive(Parser)]
#[command(name = "simpl", version = VERSION, about = "SimPL - A simple, powerful programming language")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// File to run directly
    file: Option<String>,
}

#[derive(Subcommand)]
enum Commands {
    /// Run a SimPL file
    Run {
        /// The .simpl file to run
        file: String,
        /// Syntax flavor to use (simpl, python, rust, go, javascript, ruby)
        #[arg(long, default_value = "simpl")]
        flavor: String,
    },
    /// Start interactive REPL
    Repl {
        /// Syntax flavor to use
        #[arg(long, default_value = "simpl")]
        flavor: String,
    },
    /// Open SimPL Studio (TUI IDE)
    Studio,
    /// Install a package from the registry
    Install {
        /// Package name
        package: String,
    },
    /// Update a package or all packages
    Update {
        /// Package name (omit to update all)
        package: Option<String>,
    },
    /// Remove an installed package
    Remove {
        /// Package name
        package: String,
    },
    /// List installed packages
    List,
    /// Search for packages
    Search {
        /// Search query
        query: String,
    },
    /// Show version info
    Version,
}

fn main() {
    let cli = Cli::parse();

    let result = match cli.command {
        Some(Commands::Run { file, flavor }) => run_file(&file, &flavor),
        Some(Commands::Repl { flavor }) => run_repl(&flavor),
        Some(Commands::Studio) => run_studio(),
        Some(Commands::Install { package }) => install_package(&package),
        Some(Commands::Update { package }) => update_package(package.as_deref()),
        Some(Commands::Remove { package }) => remove_package(&package),
        Some(Commands::List) => list_packages(),
        Some(Commands::Search { query }) => search_packages(&query),
        Some(Commands::Version) => {
            println!("{}", BANNER.replace("VERSION", VERSION));
            Ok(())
        }
        None => {
            if let Some(file) = cli.file {
                run_file(&file, "simpl")
            } else {
                run_repl("simpl")
            }
        }
    };

    if let Err(e) = result {
        report_error(&e);
        std::process::exit(1);
    }
}

fn run_file(path: &str, flavor: &str) -> Result<(), error::SimPLError> {
    let source = fs::read_to_string(path)
        .map_err(|e| error::SimPLError::io(format!("Cannot read file '{}': {}", path, e)))?;

    let mut interpreter = Interpreter::new();
    interpreter.run(&source)?;
    Ok(())
}

fn run_repl(flavor: &str) -> Result<(), error::SimPLError> {
    let banner = BANNER.replace("VERSION", VERSION);
    println!("{}", banner.cyan());
    println!("  Interactive REPL | Type 'exit' to quit | Flavor: {}", flavor.yellow());
    println!();

    let mut interpreter = Interpreter::new();
    let mut rl_count = 0;

    loop {
        rl_count += 1;
        print!("{} ", format!("simpl[{}]>", rl_count).cyan().bold());
        io::stdout().flush().map_err(|e| error::SimPLError::io(e.to_string()))?;

        let mut input = String::new();
        io::stdin().read_line(&mut input).map_err(|e| error::SimPLError::io(e.to_string()))?;
        let input = input.trim();

        if input.is_empty() {
            continue;
        }
        if input == "exit" || input == "quit" {
            println!("  {}", "Goodbye!".green());
            break;
        }
        if input == "help" {
            print_repl_help();
            continue;
        }
        if input == "clear" {
            print!("\x1B[2J\x1B[1;1H");
            continue;
        }
        if input.starts_with("!") {
            // Shell command
            let cmd = &input[1..];
            let output = std::process::Command::new("sh")
                .arg("-c")
                .arg(cmd)
                .output();
            match output {
                Ok(out) => {
                    println!("{}", String::from_utf8_lossy(&out.stdout));
                    if !out.stderr.is_empty() {
                        eprintln!("{}", String::from_utf8_lossy(&out.stderr));
                    }
                }
                Err(e) => println!("  {} {}", "Error:".red(), e),
            }
            continue;
        }

        match interpreter.repl_eval(input) {
            Ok(Some(val)) => println!("  {}", format!("{}", val).green()),
            Ok(None) => {}
            Err(e) => {
                report_error(&e);
            }
        }
    }

    Ok(())
}

fn run_studio() -> Result<(), error::SimPLError> {
    tui::run_tui()
}

fn install_package(name: &str) -> Result<(), error::SimPLError> {
    let pm = package::PackageManager::new();
    let result = pm.install(name)?;
    println!("  {} {}", "✓".green(), result);
    Ok(())
}

fn update_package(name: Option<&str>) -> Result<(), error::SimPLError> {
    let pm = package::PackageManager::new();
    let result = match name {
        Some(pkg) => pm.update(pkg)?,
        None => pm.update_all()?,
    };
    println!("  {} {}", "✓".green(), result);
    Ok(())
}

fn remove_package(name: &str) -> Result<(), error::SimPLError> {
    let pm = package::PackageManager::new();
    let result = pm.remove(name)?;
    println!("  {} {}", "✓".green(), result);
    Ok(())
}

fn list_packages() -> Result<(), error::SimPLError> {
    let pm = package::PackageManager::new();
    let packages = pm.list()?;

    if packages.is_empty() {
        println!("  {} No packages installed", "ℹ".yellow());
    } else {
        println!("  {} Installed packages:", "📦".to_string().yellow());
        for pkg in packages {
            println!("    • {}", pkg.green());
        }
    }
    Ok(())
}

fn search_packages(query: &str) -> Result<(), error::SimPLError> {
    let pm = package::PackageManager::new();
    let results = pm.search(query)?;

    if results.is_empty() {
        println!("  {} No packages found for '{}'", "ℹ".yellow(), query);
    } else {
        println!("  {} Search results for '{}':", "🔍".to_string().yellow(), query);
        for pkg in results {
            println!("    {} v{} - {} (by {})",
                pkg.name.green().bold(),
                pkg.version.yellow(),
                pkg.description,
                pkg.author.cyan()
            );
        }
    }
    Ok(())
}

fn print_repl_help() {
    println!();
    println!("  {} SimPL REPL Commands:", "📖".to_string().cyan().bold());
    println!("    {}              - Exit the REPL", "exit/quit".yellow());
    println!("    {}              - Clear the screen", "clear".yellow());
    println!("    {}              - Show this help", "help".yellow());
    println!("    {} <cmd>        - Run shell command", "!<cmd>".yellow());
    println!();
    println!("  {} SimPL Language:", "📖".to_string().cyan().bold());
    println!("    {} <expr>       - Print a value", "say".yellow());
    println!("    {} x = <expr>   - Set a variable", "set".yellow());
    println!("    {} <cond> {{ }}   - Conditional", "if".yellow());
    println!("    {} x in <iter> {{ }} - For loop", "for".yellow());
    println!("    {} <cond> {{ }}  - While loop", "while".yellow());
    println!("    {} f(a, b) {{ }} - Define function", "func".yellow());
    println!("    {} <cond> {{ }}  - Try/catch", "try".yellow());
    println!("    {} <expr>       - Raise error", "raise".yellow());
    println!("    {} <module>     - Import module", "import".yellow());
    println!();
    println!("  {} Built-in functions:", "📖".to_string().cyan().bold());
    println!("    say, input, type, len, str, num, int, bool");
    println!("    range, push, pop, keys, values, has");
    println!("    abs, floor, ceil, round, sqrt, pow, min, max");
    println!("    upper, lower, trim, split, join, replace");
    println!("    http_get, http_post, json_parse, json_stringify");
    println!("    time, sleep, shell");
    println!();
}
