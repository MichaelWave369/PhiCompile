"""Command-line interface for a user-controlled local vault."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .core import IntegrityError, compile_wiki, ingest, init, verify, ORIGINS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phicompile")
    parser.add_argument("--vault", type=Path, default=Path(".phicompile"),
                        help="Local vault path (default: .phicompile)")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create the local vault")
    ingest_parser = commands.add_parser("ingest", help="Snapshot and compile a text source")
    ingest_parser.add_argument("file", type=Path)
    ingest_parser.add_argument("--origin", choices=ORIGINS, default="UNKNOWN")
    commands.add_parser("compile", help="Rebuild derived wiki and report")
    commands.add_parser("verify", help="Verify ledger chain and source snapshots")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init(args.vault)
            result = {"initialized": str(args.vault)}
        elif args.command == "ingest":
            result = ingest(args.vault, args.file, args.origin)
        elif args.command == "compile":
            result = compile_wiki(args.vault)
        else:
            result = verify(args.vault)
    except (IntegrityError, ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"PhiCompile error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
