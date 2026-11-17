# Drug Master Data Change Dictation System

## What & Who

A desktop resident tool for hospital pharmacy staff. Instead of typing a master-data change form for 6-10 minutes after every verbal drug catalog verification, the pharmacist holds a button and speaks the conclusion. The tool transcribes it locally (offline, speaker-labeled, millisecond-timed), compresses it into a change draft with drug code, field name, current and proposed values each linked to the original utterance, and writes it back to the master-data platform only after the pharmacist confirms and a second reviewer (different person) approves. Recordings never leave the machine and are not saved by default.

## Core Capabilities

- Speak, get a draft: phrases appear line by line by voice segment (~0.6-1s per sentence, not per character).
- Drug code and field name are hard-matched against the hospital catalog; ambiguous generic names are rejected with candidates listed, never guessed.
- Negative corrections ("not 0.25, it is 0.5") are resolved for direction by the model, while numbers are parsed by rules; original text is always shown.
- Every element carries its source utterance, speaker and absolute millisecond range.
- Two-person review is enforced in code: the same person cannot confirm and review.
- Append-only audit trail records who changed what, when, and on which evidence.

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
cp .env.example .env          # fill in real endpoints and credentials
python -m dmchange            # launch the desktop window (system-tray resident)
```

Press "Hold to speak", then confirm and review in the window. CLI is for operations only (`doctor`, `sync-dictionary`, `selftest`, `export`). Full details: see README.md (Chinese).

## Repository Layout

- `src/dmchange/` - domain, audio, asr, extract, dictionary, ledger, outbound, ui
- `samples/` - catalog snapshot, scenarios, benchmarks
- `scripts/` - sample fetching, screenshot capture, replay, e2e rehearsal, release check
- `docs/` - CLI, architecture, examples, offline deployment, field spec, screenshots
- `tests/` - unit and protocol-compatibility tests

Full documentation: see README.md (Chinese).

---

## Follow Us

Scan the QR code to follow our official account for updates and community access:

![Follow Us](qrcode.jpg)