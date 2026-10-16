# AUTOCAD adapter

Purpose: DXF drafting and optionally DWG via licensed AutoCAD.

Reference: https://github.com/id0o0bi/autocad-mcp

**Preflight:** detect installed tool, version, available operations, execution host, units, auth, filesystem permission. Never presume a tool exists.

**Contract:** receive project_id/revision, stable element IDs, operation, parameters; return artifact pointers, new revision, log, errors and validation report.

**Safety:** sandbox arbitrary scripts, limit paths, keep transaction/undo backups, require approval before modifying originals.
