# Two-Way Slab Tributary Area

Local V1 web app for:
- DXF upload
- layer / unit review
- async tributary processing
- DXF + XLSX download

## Run Local
```bash
uv venv --clear --seed --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Open:
`http://127.0.0.1:8000`

## Current Flow
1. Upload DXF
2. Review inferred layers
3. Confirm inches or feet
4. Queue job
5. Download `tributary_output.dxf` and `column_load_takedown.xlsx`
