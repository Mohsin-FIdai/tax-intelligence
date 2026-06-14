import traceback
try:
    import run_pipeline
    run_pipeline.run_full_pipeline(use_synthetic=True)
except Exception as e:
    with open('error.txt', 'w') as f:
        traceback.print_exc(file=f)
