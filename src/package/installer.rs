use std::fs;
use std::path::Path;
use crate::error::SimPLError;
use super::registry::PackageInfo;

pub struct Installer {
    lib_dir: String,
}

impl Installer {
    pub fn new(lib_dir: &str) -> Self {
        Installer { lib_dir: lib_dir.to_string() }
    }

    pub fn install(&self, info: &PackageInfo) -> Result<String, SimPLError> {
        let pkg_dir = Path::new(&self.lib_dir).join(&info.name);

        if pkg_dir.exists() {
            return Err(SimPLError::package(format!("Package '{}' is already installed. Use 'simpl update {}' to update.", info.name, info.name)));
        }

        fs::create_dir_all(&pkg_dir)
            .map_err(|e| SimPLError::io(format!("Failed to create package directory: {}", e)))?;

        // Write package code
        let code_path = pkg_dir.join("lib.simpl");
        fs::write(&code_path, &info.code)
            .map_err(|e| SimPLError::io(format!("Failed to write package code: {}", e)))?;

        // Write package metadata
        let meta = format!(
            "version: {}\nauthor: {}\ndescription: {}\ninstalled: {}\n",
            info.version, info.author, info.description,
            chrono::Local::now().to_rfc3339()
        );
        let meta_path = pkg_dir.join("package.simpl-meta");
        fs::write(&meta_path, &meta)
            .map_err(|e| SimPLError::io(format!("Failed to write package metadata: {}", e)))?;

        Ok(format!("Installed {} v{}", info.name, info.version))
    }

    pub fn update(&self, info: &PackageInfo) -> Result<String, SimPLError> {
        let pkg_dir = Path::new(&self.lib_dir).join(&info.name);

        if !pkg_dir.exists() {
            return self.install(info);
        }

        // Check current version
        let meta_path = pkg_dir.join("package.simpl-meta");
        if meta_path.exists() {
            let current_meta = fs::read_to_string(&meta_path)
                .map_err(|e| SimPLError::io(format!("Failed to read package metadata: {}", e)))?;

            for line in current_meta.lines() {
                if let Some(ver) = line.strip_prefix("version:") {
                    if ver.trim() == info.version {
                        return Ok("Already up to date".to_string());
                    }
                }
            }
        }

        // Backup current version
        let backup_dir = pkg_dir.with_extension("simpl-backup");
        if pkg_dir.exists() {
            let _ = fs::rename(&pkg_dir, &backup_dir);
        }

        // Install new version
        fs::create_dir_all(&pkg_dir)
            .map_err(|e| SimPLError::io(format!("Failed to create package directory: {}", e)))?;

        let code_path = pkg_dir.join("lib.simpl");
        fs::write(&code_path, &info.code)
            .map_err(|e| SimPLError::io(format!("Failed to write package code: {}", e)))?;

        let meta = format!(
            "version: {}\nauthor: {}\ndescription: {}\ninstalled: {}\n",
            info.version, info.author, info.description,
            chrono::Local::now().to_rfc3339()
        );
        let meta_path = pkg_dir.join("package.simpl-meta");
        fs::write(&meta_path, &meta)
            .map_err(|e| SimPLError::io(format!("Failed to write package metadata: {}", e)))?;

        // Clean up backup
        let _ = fs::remove_dir_all(&backup_dir);

        Ok(format!("Updated to v{}", info.version))
    }

    pub fn remove(&self, package: &str) -> Result<String, SimPLError> {
        let pkg_dir = Path::new(&self.lib_dir).join(package);

        if !pkg_dir.exists() {
            return Err(SimPLError::package(format!("Package '{}' is not installed", package)));
        }

        fs::remove_dir_all(&pkg_dir)
            .map_err(|e| SimPLError::io(format!("Failed to remove package: {}", e)))?;

        Ok(format!("Removed {}", package))
    }

    pub fn list_installed(&self) -> Result<Vec<String>, SimPLError> {
        let lib_path = Path::new(&self.lib_dir);

        if !lib_path.exists() {
            return Ok(Vec::new());
        }

        let mut packages = Vec::new();
        let entries = fs::read_dir(lib_path)
            .map_err(|e| SimPLError::io(format!("Failed to read lib directory: {}", e)))?;

        for entry in entries {
            if let Ok(entry) = entry {
                if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    if let Some(name) = entry.file_name().to_str() {
                        packages.push(name.to_string());
                    }
                }
            }
        }

        Ok(packages)
    }
}
