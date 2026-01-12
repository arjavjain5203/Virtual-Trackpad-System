
try:
    import mediapipe as mp
    print("MP Imported")
    try:
        print(f"MP Solutions: {mp.solutions}")
    except AttributeError:
        print("mp.solutions NOT found")
        
    try:
        import mediapipe.python.solutions as solutions
        print(f"Explicit Solutions Import: {solutions}")
    except ImportError as e:
        print(f"Explicit Import Failed: {e}")

except ImportError as e:
    print(f"MP Import Failed: {e}")
