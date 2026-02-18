try:
    from server import app
    print("App loaded successfully:", app)
except Exception as e:
    print("Error loading app:", e)
    import traceback
    traceback.print_exc()