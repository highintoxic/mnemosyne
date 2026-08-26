from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from .config import VaultConfig
from .maintenance import doctor, rebuild_index, review
from .providers import TfidfProvider
from .retrieval import Retriever
from .sessions import SessionStore
from .store import MemoryStore

DEFAULT_VAULT = Path(os.environ.get("OBSIDIAN_MEMORY_VAULT", "C:/Memory"))


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--json", action="store_true", dest="as_json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obsidian-memory", description="Local-first Obsidian memory workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="initialize a vault"); _common(init); init.add_argument("--dry-run", action="store_true")
    save = sub.add_parser("save", help="save a typed memory"); _common(save); save.add_argument("--type", required=True); save.add_argument("--title", required=True); save.add_argument("--body", required=True); save.add_argument("--status", default="candidate"); save.add_argument("--confidence", type=float, default=.5); save.add_argument("--importance", type=float, default=.5); save.add_argument("--supersede", metavar="OLD_ID", default=None, help="mark this note superseded and link the new one")
    recall = sub.add_parser("recall", help="retrieve linked context"); _common(recall); recall.add_argument("query"); recall.add_argument("--type"); recall.add_argument("--limit", type=int, default=10); recall.add_argument("--semantic", action="store_true", help="blend TF-IDF semantic ranking")
    entity = sub.add_parser("entity", help="create a user, project, or agent"); _common(entity); entity.add_argument("kind", choices=("user", "person", "project", "agent")); entity.add_argument("--title", required=True); entity.add_argument("--description", default="")
    session = sub.add_parser("session", help="start, finalize, or load session context"); _common(session); session.add_argument("action", choices=("start", "finalize", "context", "update")); session.add_argument("--id"); session.add_argument("--project"); session.add_argument("--user"); session.add_argument("--agent"); session.add_argument("--limit", type=int, default=10); session.add_argument("--overview", default="{}"); session.add_argument("--auto", action="store_true", help="build the overview from journal events"); session.add_argument("--decisions", nargs="*", default=None); session.add_argument("--goals", nargs="*", default=None); session.add_argument("--text", default=None, help="activity entry to append (session update)")
    review = sub.add_parser("review", help="review candidates and conflicts"); _common(review); review.add_argument("--promote", metavar="ID"); review.add_argument("--reject", metavar="ID")
    question = sub.add_parser("question", help="record a quiz/learning question"); _common(question); question.add_argument("--question", required=True); question.add_argument("--answer", required=True); question.add_argument("--correct", type=lambda v: v.lower() in ("true", "1", "yes"), default=True); question.add_argument("--topic"); question.add_argument("--difficulty")
    decision = sub.add_parser("decision", help="record a decision with rationale"); _common(decision); decision.add_argument("--decision", required=True); decision.add_argument("--context", default=""); decision.add_argument("--options", nargs="*", default=None); decision.add_argument("--chosen"); decision.add_argument("--rationale", required=True)
    for name, help_text in (("index", "rebuild the disposable index"), ("doctor", "diagnose vault consistency")):
        child = sub.add_parser(name, help=help_text); _common(child)
    return parser


def _emit(value: object, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, indent=2, default=str))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                print(f"[{item.get('type', 'note')}] {item.get('title')} ({item.get('source_path', item.get('path', ''))}, confidence={item.get('confidence', 'n/a')})")
                if item.get("excerpt"): print(item["excerpt"])
            else: print(item)
    elif isinstance(value, dict):
        print(json.dumps(value, indent=2, default=str))
    else:
        print(value)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        vault = args.vault
        if args.command == "init":
            if args.dry_run:
                _emit({"vault": str(vault), "would_create": list(VaultConfig(vault).folders)}, args.as_json)
            else:
                config = VaultConfig.initialize(vault); _emit({"vault": str(config.vault), "schema_version": config.schema_version}, args.as_json)
        elif args.command == "save":
            store = MemoryStore(vault)
            if args.supersede:
                path = store.supersede(args.supersede, args.type, args.title, args.body, {"status": args.status, "confidence": args.confidence, "importance": args.importance})
            else:
                path = store.create_memory(args.type, args.title, args.body, {"status": args.status, "confidence": args.confidence, "importance": args.importance})
            _emit(str(path), args.as_json)
        elif args.command == "recall":
            filters = {"type": args.type} if args.type else None
            provider = TfidfProvider() if args.semantic else None
            _emit(Retriever(vault, provider=provider).search(args.query, filters, args.limit), args.as_json)
        elif args.command == "entity":
            path = MemoryStore(vault).create_entity(args.kind, args.title, {"description": args.description}); _emit(str(path), args.as_json)
        elif args.command == "session":
            store = SessionStore(vault)
            if args.action == "start": result = store.start(args.project, args.user, args.agent)
            elif args.action == "finalize":
                if not args.id: raise ValueError("--id is required for session finalize")
                if args.auto:
                    result = store.finalize_auto(args.id, decisions=args.decisions, goals=args.goals)
                else:
                    result = store.finalize(args.id, json.loads(args.overview))
            elif args.action == "update":
                if not args.id or not args.text: raise ValueError("--id and --text are required for session update")
                result = store.update_activity(args.id, args.text)
            else: result = store.load_context(args.project, args.limit)
            _emit(result, args.as_json)
        elif args.command == "question":
            _emit(str(MemoryStore(vault).create_question(args.question, args.answer, args.correct, args.topic, args.difficulty)), args.as_json)
        elif args.command == "decision":
            _emit(str(MemoryStore(vault).create_decision(args.decision, args.context, args.options, args.chosen, args.rationale)), args.as_json)
        elif args.command == "update":
            kwargs = {}
            if args.body is not None: kwargs["body"] = args.body
            if args.title is not None: kwargs["title"] = args.title
            if args.confidence is not None: kwargs["confidence"] = args.confidence
            if args.importance is not None: kwargs["importance"] = args.importance
            _emit(str(MemoryStore(vault).update_memory(args.id, **kwargs)), args.as_json)
        elif args.command == "review":
            if args.promote:
                _emit(str(MemoryStore(vault).set_status(args.promote, "active")), args.as_json)
            elif args.reject:
                _emit(str(MemoryStore(vault).set_status(args.reject, "rejected")), args.as_json)
            else:
                _emit(review(vault), args.as_json)
        elif args.command == "index": _emit(str(rebuild_index(vault)), args.as_json)
        elif args.command == "doctor": _emit(doctor(vault), args.as_json)
        return 0
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
