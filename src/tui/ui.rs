use ratatui::{
    Frame,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
};
use super::app::App;

pub fn draw(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Title bar
            Constraint::Min(5),    // History
            Constraint::Length(3),  // Input
        ])
        .split(f.area());

    // Title bar
    let title = Paragraph::new(Line::from(vec![
        Span::styled(" SimPL ", Style::default().fg(Color::White).bg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled(" v1.0.0 ", Style::default().fg(Color::Cyan)),
        Span::raw(" "),
        Span::styled("Studio", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
    ]))
    .block(Block::default().borders(Borders::NONE));
    f.render_widget(title, chunks[0]);

    // History
    let history_items: Vec<ListItem> = app.history.iter()
        .map(|line| {
            let style = if line.starts_with('>') {
                Style::default().fg(Color::Green)
            } else if line.starts_with("Error") {
                Style::default().fg(Color::Red)
            } else {
                Style::default().fg(Color::White)
            };
            ListItem::new(Line::from(Span::styled(line.clone(), style)))
        })
        .collect();

    let history = List::new(history_items)
        .block(Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(Color::DarkGray))
        );
    f.render_widget(history, chunks[1]);

    // Input
    let input = Paragraph::new(Line::from(vec![
        Span::styled("simpl> ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::raw(app.input.clone()),
        Span::styled("|", Style::default().fg(Color::Cyan)),
    ]))
    .block(Block::default()
        .borders(Borders::TOP)
        .border_style(Style::default().fg(Color::DarkGray))
    );
    f.render_widget(input, chunks[2]);
}
