import os
import sys

# Force output to a file instead of relying on bash redirects
log_file = open("python_pipeline.log", "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

import traceback
try:
    print("Starting pipeline...", flush=True)
    import run_pipeline
    run_pipeline.run_full_pipeline(use_synthetic=True)
    print("Pipeline finished successfully.", flush=True)
except Exception as e:
    print("CRASHED!", flush=True)
    traceback.print_exc()
finally:
    log_file.close()
