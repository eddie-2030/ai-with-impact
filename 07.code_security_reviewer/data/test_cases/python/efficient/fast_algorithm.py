# EFFICIENT: Fast Algorithm
# This code uses efficient algorithms with optimal time complexity

def find_duplicates_efficient(items):
    """EFFICIENT: O(n) time complexity using set"""
    seen = set()
    duplicates = []
    
    # EFFICIENT: Single pass - O(n)
    for item in items:
        if item in seen:
            duplicates.append(item)
        else:
            seen.add(item)
    
    return duplicates

def search_efficient(data, target):
    """EFFICIENT: Use set for O(1) lookup"""
    # EFFICIENT: Convert to set once, then O(1) lookups
    data_set = set(data)
    return target in data_set

def count_occurrences_efficient(items):
    """EFFICIENT: Single pass with dictionary"""
    result = {}
    
    # EFFICIENT: Single iteration - O(n)
    for item in items:
        result[item] = result.get(item, 0) + 1
    
    return result

