# INEFFICIENT: Slow Algorithm
# This code uses inefficient algorithms with poor time complexity

def find_duplicates_inefficient(items):
    """INEFFICIENT: O(n²) time complexity"""
    duplicates = []
    
    # INEFFICIENT: Nested loops - O(n²)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    
    return duplicates

def search_inefficient(data, target):
    """INEFFICIENT: Linear search on unsorted data"""
    # INEFFICIENT: O(n) for each search
    for item in data:
        if item == target:
            return True
    return False

def count_occurrences_inefficient(items):
    """INEFFICIENT: Multiple passes through data"""
    result = {}
    
    # INEFFICIENT: Multiple iterations
    for item in items:
        count = 0
        for other in items:
            if item == other:
                count += 1
        result[item] = count
    
    return result

