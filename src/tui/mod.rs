pub mod app;
pub mod ui;

use crate::interpreter::Interpreter;
use crate::error::SimPLError;
use crate::error::reporter::report_error;

pub fn run_tui() -> Result<(), SimPLError> {
    let mut app = app::App::new();
    let mut interpreter = Interpreter::new();

    // Set up terminal
    crossterm::execute!(
        std::io::stdout(),
        crossterm::terminal::EnterAlternateScreen,
        crossterm::event::EnableMouseCapture
    ).map_err(|e| SimPLError::io(format!("Failed to enter alternate screen: {}", e)))?;

    crossterm::terminal::enable_raw_mode()
        .map_err(|e| SimPLError::io(format!("Failed to enable raw mode: {}", e)))?;

    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = ratatui::Terminal::new(backend)
        .map_err(|e| SimPLError::io(format!("Failed to create terminal: {}", e)))?;

    // Main loop
    loop {
        terminal.draw(|f| {
            ui::draw(f, &app);
        }).map_err(|e| SimPLError::io(format!("Draw error: {}", e)))?;

        if crossterm::event::poll(std::time::Duration::from_millis(100))
            .map_err(|e| SimPLError::io(format!("Event poll error: {}", e)))?
        {
            if let crossterm::event::Event::Key(key) = crossterm::event::read()
                .map_err(|e| SimPLError::io(format!("Event read error: {}", e)))?
            {
                use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

                match key {
                    KeyEvent { code: KeyCode::Esc, .. } => break,
                    KeyEvent { code: KeyCode::Enter, modifiers: KeyModifiers::NONE, .. } => {
                        let input = app.input.clone();
                        if input.trim() == "exit" || input.trim() == "quit" {
                            break;
                        }
                        app.history.push(format!("> {}", input));
                        match interpreter.repl_eval(&input) {
                            Ok(Some(val)) => {
                                app.history.push(format!("{}", val));
                            }
                            Ok(None) => {}
                            Err(e) => {
                                app.history.push(format!("Error: {}", e));
                            }
                        }
                        app.input.clear();
                    }
                    KeyEvent { code: KeyCode::Char(c), .. } => {
                        app.input.push(c);
                    }
                    KeyEvent { code: KeyCode::Backspace, .. } => {
                        app.input.pop();
                    }
                    _ => {}
                }
            }
        }
    }

    // Restore terminal
    crossterm::terminal::disable_raw_mode()
        .map_err(|e| SimPLError::io(format!("Failed to disable raw mode: {}", e)))?;

    crossterm::execute!(
        std::io::stdout(),
        crossterm::terminal::LeaveAlternateScreen,
        crossterm::event::DisableMouseCapture
    ).map_err(|e| SimPLError::io(format!("Failed to leave alternate screen: {}", e)))?;

    Ok(())
}
