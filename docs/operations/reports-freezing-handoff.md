# Reports, freezing, and handoff

`rlab` can render reports, freeze runs, export reproduction packages, and generate handoff documents.

## Run report

```bash
rlab report run runs/<run-id> --output reports/run.md
```

This exports a Markdown table of run comparison data.

Every completed run also receives a local `report.md` inside its run directory.

## Comparison report

```bash
rlab report compare runs/ --output reports/comparison.md
```

For more export formats, use `compare`:

```bash
rlab compare runs/ --format csv --output reports/comparison.csv
rlab compare runs/ --format json --output reports/comparison.json
rlab compare runs/ --format latex --output reports/comparison.tex
```

## Freeze a run

```bash
rlab freeze run runs/<run-id> --as paper_main
```

This copies the run into:

```text
paper/paper_main/
```

and writes a `frozen.txt` marker.

## Lock a run

```bash
rlab freeze lock runs/<run-id>
```

This writes `.locked` into the run directory. Locking is a convention; project tooling should treat locked runs as immutable.

## Export reproduction zip

```bash
rlab freeze export runs/<run-id> --format repro-zip
```

This creates:

```text
runs/<run-id>_repro.zip
```

## Generate a methods section

```bash
rlab freeze methods runs/<run-id>
```

This creates a draft methods paragraph from run metadata. It is not a final paper section, but it gives a structured starting point.

## Handoff document

```bash
rlab handoff <run-id> --to team-b
```

This writes:

```text
runs/<run-id>/handoff.md
```

The handoff includes:

- context;
- reproduction command;
- result summary;
- notes;
- known issues placeholder;
- suggested next experiments placeholder.

## Recommended paper workflow

1. Run experiments.
2. Compare candidates.
3. Record a decision.
4. Add notes to selected runs.
5. Reproduce selected runs.
6. Freeze selected runs.
7. Lock frozen runs.
8. Export reproduction zip.
9. Generate report tables.
10. Write final paper text manually using generated evidence.
