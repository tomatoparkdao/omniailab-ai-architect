# IFC adapter

Purpose: IFC read/write, BIM spatial/semantic audit.

Reference: https://github.com/IfcOpenShell/IfcOpenShell

**Preflight:** detect installed tool, version, available operations, execution host, units, auth, filesystem permission. Never presume a tool exists.

**Contract:** receive project_id/revision, stable element IDs, operation, parameters; return artifact pointers, new revision, log, errors and validation report.

**Safety:** sandbox arbitrary scripts, limit paths, keep transaction/undo backups, require approval before modifying originals.
