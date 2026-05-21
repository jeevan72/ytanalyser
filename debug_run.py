import sys
import traceback

try:
    print("Executing analyze_data.py...")
    import analyze_data
    print("Execution complete, no exceptions.")
except BaseException as e:
    print("BaseException occurred (including SystemExit):")
    traceback.print_exc()
    sys.exit(1)
