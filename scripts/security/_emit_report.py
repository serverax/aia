"""JSON report assembler for pre_deploy_check.sh.

Called from the bash gate with a single positional arg pointing at a
config JSON describing the run. Reads the findings tempfile, builds the
report doc, writes it to the configured path.

Kept separate from the bash script because heredoc + Python on Windows
Git Bash is fragile. This file is testable in isolation.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path


def build_report(
    *,
    findings_path: str,
    report_path: str,
    critical: int,
    warning: int,
    info: int,
    mode: str,
    verdict: str,
    exit_code: int,
) -> dict:
    findings = []
    if findings_path:
        with open(findings_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    findings.append(json.loads(line))
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                              .isoformat(timespec="seconds"),
        "mode": mode,
        "verdict": verdict,
        "exit_code": exit_code,
        "summary": {"critical": critical, "warning": warning, "info": info},
        "checks": findings,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 8:
        print(
            "usage: _emit_report.py FINDINGS REPORT CRIT WARN INFO MODE VERDICT EXIT",
            file=sys.stderr,
        )
        return 2
    findings_path, report_path, crit, warn, info, mode, verdict, exit_code = args
    doc = build_report(
        findings_path=findings_path,
        report_path=report_path,
        critical=int(crit),
        warning=int(warn),
        info=int(info),
        mode=mode,
        verdict=verdict,
        exit_code=int(exit_code),
    )
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        json.dumps(doc, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
