pub struct App {
    pub input: String,
    pub history: Vec<String>,
    pub title: String,
}

impl App {
    pub fn new() -> Self {
        App {
            input: String::new(),
            history: vec![
                "SimPL v1.0.0 - Interactive REPL".into(),
                "Type 'exit' or press Esc to quit".into(),
                "".into(),
            ],
            title: "SimPL Studio".into(),
        }
    }
}
