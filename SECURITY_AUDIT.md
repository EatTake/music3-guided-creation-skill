# Security audit report

- Audit target: `music3-guided-creation-skill`
- Audit date: 2026-09-20
- Scope: all repository files before publication
- Method: read all files; inspect metadata; scan command, network, file, credential, privilege and dependency patterns; review scripts; validate examples and direct-input compilation

## Executive summary

- P0 blocking risks: 0
- P1 risks: 0
- P2 assessment: safe to publish as a documentation, structured-output and local-validation Skill
- Runtime network access: none
- Automatic external command execution: none
- Automatic dependency installation: none
- Credential or private-path access: none
- Destructive file operation: none

## Reviewed contents

- `SKILL.md`, `README.md`, `NOTICE.md`, `.gitignore`
- all files under `references/`, `schemas/`, `scripts/` and `examples/`

## Decoupling review

The repository is standalone. It contains no FAEX1 name, host address, SSH alias, private path, queue client, service port, authentication code, token, secret, audio asset or deployment command. Backend work is an explicit adapter boundary in `SKILL.md` and `references/workflow.md`.

The Skill core outputs four portable JSON files. The local compiler separately produces exactly two model-facing fields: `caption` and `lyrics`. Authentication, endpoint selection, path policy, current backend Schema, task submission, monitoring, downloads and audio acceptance remain outside the core.

The output contract is stable:

- `guidance.json`: interaction state and authorization state
- `creative_spec.json`: structured music description
- `lyrics_document.json`: section tags, lyrics and section music intent
- `generation_request.json`: independent generation settings
- compiled result: `{ "caption": "...", "lyrics": "..." }`

## Command execution review

`scripts/validate_bundle.py` and `scripts/compile_music3_input.py` use only Python standard-library parsing and local file reads. They do not import shell, process, subprocess, runtime, package-management, HTTP or socket modules. No shell command is constructed or executed.

The validator reads the selected bundle and the repository interaction policy. The compiler reads the selected bundle and writes only the explicit `--out` path with exclusive-create mode. Neither deletes, moves, renames, overwrites, uploads or executes files.

## Network review

No network client or network call exists. The JSON Schema declaration URLs are metadata only and are never fetched. There are no remote imports, package registries or model-service calls.

## Sensitive data and path review

No credentials, tokens, passwords, private keys, environment values, user-home paths, SSH paths, FAEX1 paths, service endpoints, user stories, private songs or generated audio are included. `.gitignore` excludes common local environment files and Python cache files.

## Dependency review

No dependency manifest, install command, vendored package, build step or remote-code import exists. Both scripts run on the Python standard library.

## Metadata review

- Skill name: `music3-guided-creation`
- `agent_created: true` is present
- Description is concise and matches the implementation boundary
- No obfuscated executable, suspicious Base64 payload or metadata injection was found

## Functional checks

- Vocal bundle: valid
- Instrumental bundle: valid
- Vocal direct-input compilation: valid JSON with `caption` and `lyrics`
- Instrumental direct-input compilation: valid JSON with `caption` and `lyrics`
- Both examples: `generation_authorized: false`
- Both examples: no network and no unintended writes
- Auto duration: explicit `duration_seconds: null`
- Instrumental: `language: "und"`, empty vocal settings and empty instrumental lyric lines
- Guidance: intent 6/6 dimensions and music design 5/5 dimensions, both confirmed
- Invalid prefilled-as-asked state: rejected by validator
- Invalid pending recommendation state: rejected by validator
- Invalid auto request with numeric duration: rejected by validator
- Compiler rejects caption CR/LF injection, unsupported tags, empty sections, duplicate list items and invalid vocal/instrumental mixtures
- Compiler rejects direct inputs over 12000 caption or 20000 lyrics characters

## Conclusion

**P2 — safe to publish.** This repository is a portable creation workflow, structured-output contract and local validator/compiler. The compiler now validates the input boundary and final output limits before writing. Any external generation adapter must be separately audited because authentication, network access, backend submission, asset download and service-specific behavior are intentionally outside this repository.
