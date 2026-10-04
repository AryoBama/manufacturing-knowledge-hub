import sys
import argparse
from pathlib import Path

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.pipeline import ManufacturingKnowledgeHub
from src.generation.formatter import AnswerFormatter


def run_showcase(hub: ManufacturingKnowledgeHub):
    scenarios = [
        {
            "title": "SCENARIO 1: EQUIPMENT SPECIFICATION (DATASHEET RETRIEVAL)",
            "query": "What is GA-1201A and what is its rated flow?",
            "context": {}
        },
        {
            "title": "SCENARIO 2: SAFETY & INTERLOCK PROTECTION (CAUSE & EFFECT)",
            "query": "What conditions can trip GA-1201A and what are its start permissives?",
            "context": {}
        },
        {
            "title": "SCENARIO 3: TROUBLESHOOTING & FAILURE MEMORY (OPL + SAP PM)",
            "query": "What should I check when GA-1201A has high vibration?",
            "context": {}
        },
        {
            "title": "SCENARIO 4: MULTI-ASSET MAINTENANCE HISTORY (YD-2301)",
            "query": "What is the maintenance and breakdown history of YD-2301?",
            "context": {}
        },
        {
            "title": "SCENARIO 5: CONTEXTUAL DISAMBIGUATION & SAFETY REFUSAL",
            "query": "What should I check if there is abnormal noise and vibration?",
            "context": {}
        }
    ]

    print("\n" + "=" * 76)
    print(" CHANDRA ASRI PACIFIC - MANUFACTURING KNOWLEDGE HUB (CALIBER 2026)")
    print(" AUTOMATED COMPETITION SHOWCASE RUNNER")
    print("=" * 76 + "\n")

    for idx, sc in enumerate(scenarios, 1):
        print(f"\n>>> [{idx}/{len(scenarios)}] {sc['title']}")
        print(f"    Engineer Prompt: \"{sc['query']}\"\n")
        ans = hub.ask(sc["query"], session_context=sc["context"])
        print(AnswerFormatter.to_terminal_text(ans))
        print("\n")


def run_interactive(hub: ManufacturingKnowledgeHub):
    print("\n" + "=" * 70)
    print(" CHANDRA ASRI PACIFIC - MANUFACTURING KNOWLEDGE HUB (CALIBER 2026)")
    print(" Interactive Engineer Technical Assistant")
    print(" Type your technical question below (or 'exit' / 'quit' to end)")
    print("=" * 70 + "\n")

    last_tag = None
    while True:
        try:
            query = input("Engineer Query > ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("\nSession ended. Thank you.\n")
                break

            ctx = {"last_mentioned_tag": last_tag} if last_tag else {}
            ans = hub.ask(query, session_context=ctx)
            if ans.equipment_tag:
                last_tag = ans.equipment_tag

            print("\n" + AnswerFormatter.to_terminal_text(ans) + "\n")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.\n")
            break


def main():
    parser = argparse.ArgumentParser(description="Chandra Asri Manufacturing Knowledge Hub CLI")
    parser.add_argument("query", nargs="?", help="Direct question to ask the Knowledge Hub")
    parser.add_argument("--showcase", action="store_true", help="Run automated competition showcase scenarios")
    parser.add_argument("--markdown", action="store_true", help="Output in Markdown format")
    args = parser.parse_args()

    hub = ManufacturingKnowledgeHub()

    if args.showcase:
        run_showcase(hub)
    elif args.query:
        fmt = "markdown" if args.markdown else "terminal"
        print(hub.ask_formatted(args.query, format_type=fmt))
    else:
        run_interactive(hub)


if __name__ == "__main__":
    main()
