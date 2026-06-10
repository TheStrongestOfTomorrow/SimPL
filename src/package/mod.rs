pub mod registry;
pub mod installer;

use crate::error::SimPLError;

pub struct PackageManager {
    registry: registry::Registry,
    lib_dir: String,
}

impl PackageManager {
    pub fn new() -> Self {
        let lib_dir = dirs::home_dir()
            .map(|p| p.join(".simpl/libs").to_string_lossy().to_string())
            .unwrap_or_else(|| "~/.simpl/libs".to_string());

        PackageManager {
            registry: registry::Registry::new(),
            lib_dir,
        }
    }

    pub fn install(&self, package: &str) -> Result<String, SimPLError> {
        let info = self.registry.fetch_package(package)?;
        let installer = installer::Installer::new(&self.lib_dir);
        installer.install(&info)
    }

    pub fn update(&self, package: &str) -> Result<String, SimPLError> {
        let info = self.registry.fetch_package(package)?;
        let installer = installer::Installer::new(&self.lib_dir);
        installer.update(&info)
    }

    pub fn remove(&self, package: &str) -> Result<String, SimPLError> {
        let installer = installer::Installer::new(&self.lib_dir);
        installer.remove(package)
    }

    pub fn list(&self) -> Result<Vec<String>, SimPLError> {
        let installer = installer::Installer::new(&self.lib_dir);
        installer.list_installed()
    }

    pub fn search(&self, query: &str) -> Result<Vec<registry::PackageInfo>, SimPLError> {
        self.registry.search(query)
    }

    pub fn update_all(&self) -> Result<String, SimPLError> {
        let installer = installer::Installer::new(&self.lib_dir);
        let installed = installer.list_installed()?;
        let mut results = Vec::new();

        for pkg in installed {
            match self.registry.fetch_package(&pkg) {
                Ok(info) => {
                    match installer.update(&info) {
                        Ok(msg) => results.push(format!("{}: {}", pkg, msg)),
                        Err(e) => results.push(format!("{}: FAILED - {}", pkg, e)),
                    }
                }
                Err(e) => results.push(format!("{}: FAILED - {}", pkg, e)),
            }
        }

        Ok(results.join("\n"))
    }
}
