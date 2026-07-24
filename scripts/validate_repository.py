#!/usr/bin/env python3
"""Validate the marketplace without third-party Python dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
PLATFORMS = {"windows", "macos", "linux"}
TEXT_SUFFIXES = {
    "",
    ".json",
    ".md",
    ".py",
    ".ps1",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache"}
SECRET_PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"
    ),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"
    ),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}


class Validator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def load_json(self, relative: str) -> Any:
        path = self.root / relative
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.error(f"missing JSON file: {relative}")
        except UnicodeDecodeError as exc:
            self.error(f"not UTF-8: {relative}: {exc}")
        except json.JSONDecodeError as exc:
            self.error(f"invalid JSON: {relative}: {exc}")
        return {}

    def validate_text_and_secrets(self) -> None:
        for path in self.root.rglob("*"):
            if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name != "LICENSE":
                continue
            relative = path.relative_to(self.root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                self.error(f"not UTF-8: {relative}: {exc}")
                continue
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    self.error(f"possible {label} in {relative}")
            placeholder_marker = "[" + "TODO:"
            if placeholder_marker in text:
                self.error(f"placeholder marker in {relative}")

    def validate_skill(self, skill_path: Path, seen_names: set[str]) -> None:
        relative = skill_path.relative_to(self.root).as_posix()
        skill_md = skill_path / "SKILL.md"
        if not skill_md.is_file():
            self.error(f"missing SKILL.md: {relative}")
            return
        try:
            text = skill_md.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            self.error(f"not UTF-8: {relative}/SKILL.md: {exc}")
            return
        match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
        if not match:
            self.error(f"invalid YAML frontmatter: {relative}/SKILL.md")
            return
        metadata: dict[str, str] = {}
        for line in match.group(1).splitlines():
            if ":" not in line:
                self.error(f"invalid frontmatter line in {relative}/SKILL.md: {line}")
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"\'')
        if set(metadata) != {"name", "description"}:
            self.error(
                f"frontmatter must contain only name and description: {relative}/SKILL.md"
            )
        name = metadata.get("name", "")
        if not NAME_RE.fullmatch(name):
            self.error(f"invalid skill name {name!r}: {relative}/SKILL.md")
        if name != skill_path.name:
            self.error(f"skill folder/name mismatch: {relative} vs {name!r}")
        if name in seen_names:
            self.error(f"duplicate skill name: {name}")
        seen_names.add(name)
        if not metadata.get("description"):
            self.error(f"empty skill description: {relative}/SKILL.md")
        if not (skill_path / "agents" / "openai.yaml").is_file():
            self.error(f"missing agents/openai.yaml: {relative}")

    def validate_dependency(
        self, package_id: str, dependency: Any, platforms: set[str]
    ) -> None:
        if not isinstance(dependency, dict):
            self.error(f"dependency must be an object: {package_id}")
            return
        required = {
            "name",
            "purpose",
            "required",
            "modifiesSystem",
            "detect",
            "install",
            "verify",
        }
        if set(dependency) != required:
            self.error(
                f"dependency fields for {package_id} must be exactly {sorted(required)}"
            )
            return
        if not isinstance(dependency["required"], bool) or not isinstance(
            dependency["modifiesSystem"], bool
        ):
            self.error(f"dependency booleans invalid: {package_id}/{dependency.get('name')}")
        for phase in ("detect", "install", "verify"):
            commands = dependency.get(phase)
            if not isinstance(commands, dict):
                self.error(f"dependency {phase} must be an object: {package_id}")
                continue
            missing = platforms - set(commands)
            extra = set(commands) - PLATFORMS
            if missing:
                self.error(
                    f"dependency {phase} missing {sorted(missing)}: {package_id}"
                )
            if extra:
                self.error(
                    f"dependency {phase} has unsupported platforms {sorted(extra)}: {package_id}"
                )
            if any(not isinstance(command, str) or not command.strip() for command in commands.values()):
                self.error(f"dependency {phase} has empty command: {package_id}")

    def validate_delivery(
        self, package_id: str, delivery: Any, platforms: set[str]
    ) -> None:
        if not isinstance(delivery, dict):
            self.error(f"delivery must be an object: {package_id}")
            return
        required = {
            "type",
            "releaseTag",
            "assetName",
            "assetUrl",
            "sha256",
            "installerPaths",
            "activation",
        }
        if set(delivery) != required:
            self.error(f"delivery fields invalid: {package_id}")
            return
        if delivery.get("type") != "licensed-github-release":
            self.error(f"unsupported delivery type: {package_id}")
        asset_name = delivery.get("assetName", "")
        asset_url = delivery.get("assetUrl", "")
        release_tag = delivery.get("releaseTag", "")
        expected_url = (
            "https://github.com/NewbieCheng/company-skills-marketplace/releases/"
            f"download/{release_tag}/{asset_name}"
        )
        if asset_url != expected_url:
            self.error(f"licensed release URL mismatch: {package_id}")
        sha256 = delivery.get("sha256", "")
        if not isinstance(sha256, str) or not re.fullmatch(r"[A-Fa-f0-9]{64}", sha256):
            self.error(f"invalid licensed release SHA-256: {package_id}")

        installer_paths = delivery.get("installerPaths")
        if not isinstance(installer_paths, dict):
            self.error(f"installerPaths must be an object: {package_id}")
        else:
            if set(installer_paths) != platforms:
                self.error(
                    f"installerPaths must match platforms: {package_id}"
                )
            for platform, relative in installer_paths.items():
                if platform not in PLATFORMS:
                    self.error(f"unsupported installer platform: {package_id}/{platform}")
                    continue
                if (
                    not isinstance(relative, str)
                    or Path(relative).is_absolute()
                    or ".." in Path(relative).parts
                    or not (self.root / relative).is_file()
                ):
                    self.error(f"missing or unsafe installer path: {package_id}/{relative}")

        activation = delivery.get("activation")
        activation_fields = {
            "productId",
            "licenseMajor",
            "binding",
            "requestCodePrefix",
            "activationCodePrefix",
            "promptAfterInstall",
            "activationStoredLocally",
            "reusableOnAnotherDevice",
        }
        if not isinstance(activation, dict) or set(activation) != activation_fields:
            self.error(f"activation fields invalid: {package_id}")
            return
        if activation.get("binding") != "device":
            self.error(f"activation must use device binding: {package_id}")
        if activation.get("activationStoredLocally") is not True:
            self.error(f"activation must be stored locally: {package_id}")
        if activation.get("reusableOnAnotherDevice") is not False:
            self.error(f"activation must reject another device: {package_id}")
        for field in ("requestCodePrefix", "activationCodePrefix"):
            value = activation.get(field, "")
            if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9]+-", value):
                self.error(f"invalid {field}: {package_id}")

    def validate(self) -> list[str]:
        self.validate_text_and_secrets()
        catalog = self.load_json("catalog.json")
        marketplace = self.load_json(".agents/plugins/marketplace.json")
        if not isinstance(catalog, dict) or not isinstance(marketplace, dict):
            return self.errors

        if catalog.get("schemaVersion") != 1:
            self.error("catalog schemaVersion must be 1")
        if catalog.get("publisher") != "NewbieCheng Team":
            self.error("catalog publisher must be NewbieCheng Team")

        projects = catalog.get("projects", [])
        project_ids: set[str] = set()
        if not isinstance(projects, list):
            self.error("catalog projects must be an array")
            projects = []
        for project in projects:
            if not isinstance(project, dict):
                self.error("project entry must be an object")
                continue
            if set(project) != {"id", "displayName", "description"}:
                self.error(f"project fields invalid: {project.get('id')}")
            project_id = project.get("id", "")
            if not isinstance(project_id, str) or not NAME_RE.fullmatch(project_id):
                self.error(f"invalid project id: {project_id!r}")
                continue
            if project_id in project_ids:
                self.error(f"duplicate project id: {project_id}")
            project_ids.add(project_id)

        marketplace_entries = marketplace.get("plugins", [])
        if marketplace.get("name") != "newbiecheng-team":
            self.error("marketplace name must be newbiecheng-team")
        if marketplace.get("interface", {}).get("displayName") != "NewbieCheng Team Skills":
            self.error("marketplace displayName must be NewbieCheng Team Skills")
        if not isinstance(marketplace_entries, list):
            self.error("marketplace plugins must be an array")
            marketplace_entries = []
        marketplace_by_name: dict[str, dict[str, Any]] = {}
        for entry in marketplace_entries:
            if not isinstance(entry, dict):
                self.error("marketplace plugin entry must be an object")
                continue
            name = entry.get("name", "")
            if name in marketplace_by_name:
                self.error(f"duplicate marketplace plugin: {name}")
            marketplace_by_name[name] = entry
            policy = entry.get("policy", {})
            if policy.get("installation") not in {
                "AVAILABLE",
                "INSTALLED_BY_DEFAULT",
                "NOT_AVAILABLE",
            }:
                self.error(f"invalid installation policy: {name}")
            if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
                self.error(f"invalid authentication policy: {name}")
            if not entry.get("category"):
                self.error(f"missing marketplace category: {name}")

        packages = catalog.get("packages", [])
        if not isinstance(packages, list):
            self.error("catalog packages must be an array")
            packages = []
        package_ids: set[str] = set()
        seen_skill_names: set[str] = set()
        for package in packages:
            if not isinstance(package, dict):
                self.error("package entry must be an object")
                continue
            required_fields = {
                "id",
                "displayName",
                "project",
                "version",
                "description",
                "pluginPath",
                "skillPaths",
                "platforms",
                "dependencies",
            }
            allowed_fields = required_fields | {"delivery"}
            if not required_fields <= set(package) or not set(package) <= allowed_fields:
                self.error(f"package fields invalid: {package.get('id')}")
            package_id = package.get("id", "")
            project_id = package.get("project", "")
            if not isinstance(package_id, str) or not NAME_RE.fullmatch(package_id):
                self.error(f"invalid package id: {package_id!r}")
                continue
            if package_id in package_ids:
                self.error(f"duplicate package id: {package_id}")
            package_ids.add(package_id)
            if project_id not in project_ids:
                self.error(f"unknown project for {package_id}: {project_id}")
            if not package_id.startswith(f"{project_id}-"):
                self.error(f"package must start with project prefix: {package_id}")
            version = package.get("version", "")
            if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
                self.error(f"invalid semantic version: {package_id}/{version}")

            plugin_relative = package.get("pluginPath", "")
            if plugin_relative != f"plugins/{package_id}":
                self.error(f"pluginPath mismatch: {package_id}/{plugin_relative}")
            plugin_path = self.root / plugin_relative
            manifest = self.load_json(f"{plugin_relative}/.codex-plugin/plugin.json")
            if isinstance(manifest, dict):
                if manifest.get("name") != package_id:
                    self.error(f"plugin manifest name mismatch: {package_id}")
                if manifest.get("version") != version:
                    self.error(f"plugin/catalog version mismatch: {package_id}")
                if manifest.get("skills") != "./skills/":
                    self.error(f"plugin skills path must be ./skills/: {package_id}")
                if manifest.get("author", {}).get("name") != "NewbieCheng Team":
                    self.error(f"plugin author mismatch: {package_id}")
                if not manifest.get("interface", {}).get("displayName"):
                    self.error(f"plugin displayName missing: {package_id}")

            skill_paths = package.get("skillPaths", [])
            if not isinstance(skill_paths, list) or not skill_paths:
                self.error(f"skillPaths must be a non-empty array: {package_id}")
                skill_paths = []
            for skill_relative in skill_paths:
                if not isinstance(skill_relative, str) or not skill_relative.startswith(
                    f"{plugin_relative}/skills/"
                ):
                    self.error(f"skill path outside plugin: {package_id}/{skill_relative}")
                    continue
                self.validate_skill(self.root / skill_relative, seen_skill_names)

            platforms_value = package.get("platforms", [])
            platforms = set(platforms_value) if isinstance(platforms_value, list) else set()
            if not platforms or not platforms <= PLATFORMS:
                self.error(f"invalid platforms: {package_id}/{platforms_value}")
            dependencies = package.get("dependencies", [])
            if not isinstance(dependencies, list):
                self.error(f"dependencies must be an array: {package_id}")
                dependencies = []
            for dependency in dependencies:
                self.validate_dependency(package_id, dependency, platforms)
            if "delivery" in package:
                self.validate_delivery(package_id, package["delivery"], platforms)

            entry = marketplace_by_name.get(package_id)
            if entry is None:
                self.error(f"package missing from marketplace: {package_id}")
            else:
                source = entry.get("source", {})
                if source != {"source": "local", "path": f"./plugins/{package_id}"}:
                    self.error(f"marketplace source mismatch: {package_id}")

        if set(marketplace_by_name) != package_ids:
            extras = set(marketplace_by_name) - package_ids
            if extras:
                self.error(f"marketplace entries missing from catalog: {sorted(extras)}")

        plugins_dir = self.root / "plugins"
        disk_plugins = {
            path.name for path in plugins_dir.iterdir() if path.is_dir()
        } if plugins_dir.is_dir() else set()
        if disk_plugins != package_ids:
            self.error(
                f"plugin directories and catalog differ: disk={sorted(disk_plugins)} catalog={sorted(package_ids)}"
            )
        return self.errors


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    validator = Validator(root)
    errors = validator.validate()
    if errors:
        print(f"Repository validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    print(
        "Repository validation passed: "
        f"{len(catalog['projects'])} project(s), {len(catalog['packages'])} package(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
