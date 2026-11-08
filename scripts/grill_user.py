#!/usr/bin/env python3
"""Grill the user relentlessly about a plan, decision, or idea.
Implements the 'Grilling' skill to stress-test their thinking.
"""

import argparse
import sys

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grill the user relentlessly about a plan, decision, or idea."
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default="",
        help="The topic, plan, decision, or idea to grill the user about.",
    )
    parser.add_argument(
        "--async",
        dest="async_mode",
        action="store_true",
        help="Print questions with recommended defaults formatted for a plan or PR.",
    )
    args = parser.parse_args()

    topic_title = args.topic if args.topic else "General Plan or Task"

    if args.async_mode:
        print(f"### Grilling Questions & Defaults: {topic_title}\n")
        print("#### Open Questions & Recommended Defaults")
        print("1. **Core Ambiguity / Design Choice**")
        print("   - Question: What is the primary architecture or target behavior?")
        print("   - Recommended Default: Follow standing conventions and existing project patterns.")
        print("   - Options: A) Standard conventions (recommended), B) Custom configuration, C) Minimal viable path.")
        print("   - Reason: Preserves consistency and minimizes regression risk.\n")
        print("2. **Scope Boundaries & Trade-offs**")
        print("   - Question: What failure modes and edge cases are in scope?")
        print("   - Recommended Default: Full test matrix with property-based and hostile input coverage.")
        print("   - Options: A) Full coverage matrix (recommended), B) Happy-path smoke only.")
        print("   - Reason: Ensures robust verification before declaring done.\n")
        print("#### Recorded Assumptions (Proceeding with recommended defaults)")
        print("- Proceeding with recommended defaults unless blocking feedback is received.")
        print("- Stating all assumptions in plan and pull request summary.")
        return 0

    print(f"Triggering 'Grilling' skill for topic: {args.topic}")
    print("\nInstructions for the AI Agent:")
    print("- Grill the user relentlessly about a plan, decision, or idea.")
    print("- Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.")
    print("- Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.")
    print("- Format a round like so:")
    print("  [Q] **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>")
    print("  [A] <your recommended answer>")
    print("  ---")
    print("  [Q] **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>")
    print("  [A] <your recommended answer>")
    print("- Word each question so 'yes' accepts your recommended answer.")
    print("- Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.")
    print("- Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.")
    print("- The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
