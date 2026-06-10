use crate::error::SimPLError;
use serde::Deserialize;

const GITHUB_API: &str = "https://api.github.com/repos/TheStrongestOfTomorrow/SimPL-Libraries/issues";

#[derive(Debug, Clone, Deserialize)]
pub struct PackageInfo {
    pub name: String,
    pub version: String,
    pub author: String,
    pub description: String,
    pub code: String,
}

pub struct Registry {
    client: reqwest::blocking::Client,
}

impl Registry {
    pub fn new() -> Self {
        let client = reqwest::blocking::Client::builder()
            .user_agent("SimPL/1.0")
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .unwrap_or_else(|_| reqwest::blocking::Client::new());

        Registry { client }
    }

    pub fn fetch_package(&self, name: &str) -> Result<PackageInfo, SimPLError> {
        let url = format!("{}/{}", GITHUB_API, name);

        let resp = self.client.get(&url)
            .send()
            .map_err(|e| SimPLError::package(format!("Failed to fetch package: {}", e)))?;

        if !resp.status().is_success() {
            return Err(SimPLError::package(format!("Package '{}' not found in registry", name)));
        }

        let issue: serde_json::Value = resp.json()
            .map_err(|e| SimPLError::package(format!("Failed to parse registry response: {}", e)))?;

        // Parse the issue body as package metadata
        let body = issue["body"].as_str().unwrap_or("");
        self.parse_package_body(name, body)
    }

    pub fn search(&self, query: &str) -> Result<Vec<PackageInfo>, SimPLError> {
        let url = format!("{}?labels=library&per_page=100", GITHUB_API);

        let resp = self.client.get(&url)
            .send()
            .map_err(|e| SimPLError::package(format!("Search failed: {}", e)))?;

        if !resp.status().is_success() {
            return Err(SimPLError::package("Failed to search registry"));
        }

        let issues: serde_json::Value = resp.json()
            .map_err(|e| SimPLError::package(format!("Failed to parse search results: {}", e)))?;

        let mut results = Vec::new();

        if let Some(arr) = issues.as_array() {
            for issue in arr {
                let title = issue["title"].as_str().unwrap_or("").to_lowercase();
                if title.contains(&query.to_lowercase()) {
                    let name = issue["title"].as_str().unwrap_or("unknown").to_string();
                    let body = issue["body"].as_str().unwrap_or("");
                    if let Ok(info) = self.parse_package_body(&name, body) {
                        results.push(info);
                    }
                }
            }
        }

        Ok(results)
    }

    fn parse_package_body(&self, name: &str, body: &str) -> Result<PackageInfo, SimPLError> {
        // Expected format:
        // ---META---
        // version: 1.0.0
        // author: someone
        // description: A cool library
        // ---CODE---
        // (SimPL code here)

        let mut version = "1.0.0".to_string();
        let mut author = "unknown".to_string();
        let mut description = String::new();
        let mut code = String::new();
        let mut in_code = false;

        for line in body.lines() {
            if line.trim() == "---CODE---" {
                in_code = true;
                continue;
            }
            if line.trim() == "---META---" {
                continue;
            }

            if in_code {
                code.push_str(line);
                code.push('\n');
            } else {
                if let Some(val) = line.strip_prefix("version:") {
                    version = val.trim().to_string();
                } else if let Some(val) = line.strip_prefix("author:") {
                    author = val.trim().to_string();
                } else if let Some(val) = line.strip_prefix("description:") {
                    description = val.trim().to_string();
                }
            }
        }

        Ok(PackageInfo {
            name: name.to_string(),
            version,
            author,
            description,
            code,
        })
    }
}
