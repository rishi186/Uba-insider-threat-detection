# Contributing to UBA & Insider Threat Detection

## Project Conventions

### Logging
- **Never use `print()`** in production code. Use `logging`:
  ```python
  import logging
  logger = logging.getLogger("uba.<module_name>")
  logger.info("Loaded %d events.", count)
  ```

### Configuration
- All thresholds, multipliers, paths, and work-hour definitions **must** come from `config.yaml`.
- Read config via:
  ```python
  from utils.config import config
  val = config.risk_scoring.get('base_multiplier', 250)
  ```
- **Never hardcode** user IDs, day thresholds, or hour boundaries.

### Error Handling
- ML training pipelines must **fail fast** on error — never write placeholder/dummy model files.
- Use `raise` for critical failures; let the caller decide recovery.
- API endpoints should return structured error objects via FastAPI's HTTPException.

### Testing
- At minimum, every new feature needs a test in `tests/`.
- Run the full suite before committing:
  ```bash
  pytest tests/ -v --tb=short -W ignore::DeprecationWarning
  ```

---

## Adding Threat Scenarios

To change the insider threat user without modifying code:

1. Open `config.yaml`
2. Edit `data_generation.scenarios`:
   ```yaml
   scenarios:
     malicious_user: "U120"       # Any user ID
     malicious_start_day: "2024-01-15"
   ```
3. Also update `data_generation.insider_threat_user` (used by the generator):
   ```yaml
   insider_threat_user: "U120"
   insider_threat_start_day: 15
   ```
4. Re-run the pipeline — training, evaluation, and risk scoring will automatically pick up the new scenario.

---

## Adding New ML Models

1. Create the model class in `src/models/` (see `baseline.py` as a template).
2. Add an evaluation function in `src/models/evaluate_all_models.py`.
3. Register the model in the API's `/models/status` endpoint (`src/api/routers/models.py`).
4. Add tests in `tests/test_risk_engine.py`.

---

## Docker Deployment

```bash
# Build and start both backend and frontend
docker-compose up --build

# Backend only
docker-compose up --build backend
```

The backend exposes port `8000`, the frontend port `5173`.
