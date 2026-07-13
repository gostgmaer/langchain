# Workspace

## Quicksort — Visual Representation

```mermaid
flowchart TD
    A[Start: quicksort(arr, low, high)] --> B{low < high?}
    B -- No --> Z[Return: base case]
    B -- Yes --> C[pivot = arr[high]]
    C --> D[i = low - 1]
    D --> E{j = low .. high-1}
    E --> F{arr[j] <= pivot?}
    F -- Yes --> G[i += 1; swap arr[i], arr[j]]
    F -- No --> E
    G --> E
    E -- done --> H[swap arr[i+1], arr[high]]
    H --> I[p = i + 1]
    I --> J[quicksort(arr, low, p-1)]
    I --> K[quicksort(arr, p+1, high)]
    J --> B
    K --> B
```

### Python implementation with type hints, metrics, and bar-chart visualization

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SortStats:
    comparisons: int = 0
    swaps: int = 0
    passes: list[str] = field(default_factory=list)


def _bar_row(label: str, arr: list[int]) -> str:
    return f"{label}: " + " ".join("█" * v for v in arr)


def quicksort_visual(arr: list[int], stats: SortStats | None = None) -> list[int]:
    """Sort `arr` in place using quicksort (Lomuto partition), recording metrics."""
    stats = stats or SortStats()
    _quicksort(arr, 0, len(arr) - 1, stats)
    return arr


def _quicksort(arr: list[int], low: int, high: int, stats: SortStats) -> None:
    if low >= high:
        return

    pivot = arr[high]
    i = low - 1

    for j in range(low, high):
        stats.comparisons += 1
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
            if i != j:
                stats.swaps += 1

    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    if i + 1 != high:
        stats.swaps += 1
    pivot_index = i + 1

    stats.passes.append(_bar_row(f"pivot={pivot:>2}", arr))

    _quicksort(arr, low, pivot_index - 1, stats)
    _quicksort(arr, pivot_index + 1, high, stats)


if __name__ == "__main__":
    data = [5, 3, 8, 4, 2, 7, 1, 6]
    stats = SortStats()
    result = quicksort_visual(data.copy(), stats)

    for row in stats.passes:
        print(row)

    print(f"\nSorted: {result}")
    print(f"Comparisons: {stats.comparisons}, Swaps: {stats.swaps}")
```

Example output:

```
pivot= 6: █████ ███ ████ ██ █ ██████ ████████ ███████
pivot= 1: █ ███ ████ ██ █████ ██████ ████████ ███████
pivot= 5: █ ███ ████ ██ █████ ██████ ████████ ███████
pivot= 2: █ ██ ████ ███ █████ ██████ ████████ ███████
pivot= 3: █ ██ ███ ████ █████ ██████ ████████ ███████
pivot= 7: █ ██ ███ ████ █████ ██████ ███████ ████████

Sorted: [1, 2, 3, 4, 5, 6, 7, 8]
Comparisons: 18, Swaps: 8
```

**Why quicksort over bubble sort:** average-case `O(n log n)` vs `O(n²)`, in-place partitioning, and the recursive divide-and-conquer structure is a better showcase for tracking algorithmic metrics (comparisons/swaps) than a simple nested-loop pass.
