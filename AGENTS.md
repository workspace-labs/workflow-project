# AGENTS.md: working on workflow-project

For coding agents changing this repository. What the skill does is in `README.md`; what it must never do
is in `docs/scope.md`.

## Test

```bash
cd workflow-project        # your clone
python3 -m unittest discover -s tests
```

A change to `layout.py` or `routing.py` is not done until the geometry checks in `tests/test_layout.py`
pass for every example. Look at the drawn pages too: render them with `pdftoppm -r 70 -png`.

The tests judge the tool with their own independent checks, never with its code: `tests/geometry_oracle.py`
(lines, boxes, arrow meetings) and `tests/pdf_words.py` (word positions read back with `pdftotext`, from
poppler). Keep them independent: a test that calls the tool's own collision or fit helpers is blind to the
bug it should catch.

## Draw the examples

```bash
for ex in leave-request building-permit workflow-project; do
  python3 skills/workflow-project/scripts/draw_workflow.py skills/workflow-project/examples/$ex.json -o "/tmp/$ex.pdf"
done
```

## Rules for this repository

- Keep `skills/workflow-project/` clean: no `__pycache__`, no drawn PDFs, no test files. It is installed
  and uploaded as it is. The tool sets `sys.dont_write_bytecode`; run tests with `python3 -B` if unsure.
- The look lives in `workflow_tool/theme.py` and is the owner's decision. Never change fonts or colours
  without his yes.
- Geometry code never imports drawing code (see `docs/architecture/boundaries.md`).
- Every change bumps `VERSION` in `workflow_tool/__init__.py` and adds a dated `CHANGELOG.md` entry.
- After a change, rebuild `dist/workflow-project.zip` (command in `README.md`) and tell the owner it needs
  uploading again to the Claude app.
- Never commit or push without the owner's word.
