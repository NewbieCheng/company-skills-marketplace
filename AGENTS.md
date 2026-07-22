# Repository instructions

This repository distributes Codex skills through direct GitHub download and a repo marketplace. Preserve the no-Git beginner installation path.

## Package layout

- Keep plugins flat at `plugins/<project>-<capability>`.
- Register every project and package in `catalog.json`.
- Match the plugin directory, marketplace entry name, catalog package ID, and `plugin.json` name exactly.
- Prefix each plugin ID with its catalog project ID and a hyphen.
- Keep one independently installable primary Skill per plugin unless a bundle is explicitly required.
- Store expanded source files; do not add ZIP archives, generated build outputs, dependency folders, or caches.

## Skill and plugin authoring

- Initialize new plugins with the system `plugin-creator` scaffold and new Skills with `skill-creator`.
- Use lowercase kebab-case names under 64 characters.
- Limit `SKILL.md` frontmatter to `name` and `description`.
- Put detailed schemas and domain references in `references/`; do not add auxiliary README or installation guides inside a Skill.
- Keep `agents/openai.yaml` aligned with the Skill and make its default prompt explicitly mention `$skill-name`.
- Use strict semantic versions and keep catalog and plugin versions identical.
- Do not declare MCP, app, asset, or script paths unless the referenced files exist.

## Dependencies

- Declare each system dependency in `catalog.json` with purpose, required flag, system-modification flag, and per-platform detect/install/verify commands.
- Cover every platform listed by the package.
- Show all system-modifying commands to the user and obtain one confirmation before running them.
- Never claim unsupported platforms work.

## Quality and security

- Save text as UTF-8.
- Do not commit secrets, credentials, cookies, private keys, customer data, `node_modules`, build outputs, or logs.
- Do not leave TODO markers or placeholder content in installable packages.
- Preserve evidence and failure reasons in research Skills; do not invent sources or metrics.
- This repository permits direct pushes by trusted collaborators. Run validation before every push even though CI also runs afterward.

## Required verification

Run from the repository root:

```text
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

Also run the system `skill-creator/scripts/quick_validate.py` against every Skill and the system `plugin-creator/scripts/validate_plugin.py` against every plugin when those tools are available. For a release or changed install path, use the system `skill-installer` with `--method download` and a temporary destination.
