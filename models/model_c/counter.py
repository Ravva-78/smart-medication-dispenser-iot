CLASSES = ["present", "missing"]


def count(results):
    """
    Count present/missing from Model C results.
    
    Args:
        results: list of (class_name, confidence) from predict_batch
    
    Returns:
        dict with total, present, missing
    """
    present = sum(1 for cls, _ in results if cls == "present")
    missing = sum(1 for cls, _ in results if cls == "missing")
    return {
        "total": len(results),
        "present": present,
        "missing": missing,
    }
