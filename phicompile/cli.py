"""Command-line interface for a user-controlled local vault."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .core import IntegrityError, compile_wiki, ingest, init, verify, ORIGINS
from .ollama import OllamaError, propose, select_pairs


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
    plan_parser = commands.add_parser("plan", help="Preview pairs without contacting a model")
    plan_parser.add_argument("--max-pairs", type=int, default=12)
    proposal_parser = commands.add_parser("propose", help="Opt-in local Ollama review; untrusted proposals only")
    proposal_parser.add_argument("--model", required=True,
                                 help="Installed Ollama model (e.g. granite4.2:8b)")
    proposal_parser.add_argument("--max-pairs", type=int, default=12)
    proposal_parser.add_argument("--timeout", type=int, default=180, help="Local request timeout, seconds")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init(args.vault)
            result = {"initialized": str(args.vault)}
        elif args.command == "ingest":
            result = ingest(args.vault, args.file, args.origin)
        elif args.command == "compile":
            result = compile_wiki(args.vault)
        elif args.command == "verify":
            result = verify(args.vault)
        elif args.command == "plan":
            result = select_pairs(args.vault, limit=args.max_pairs)
        else:
            result = propose(args.vault, args.model, limit=args.max_pairs,
                             timeout=args.timeout)
    except (IntegrityError, OllamaError, ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"PhiCompile error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0
