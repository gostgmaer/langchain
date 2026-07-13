"""
Bubble Sort Visualizer
Run this file directly to see bubble sort happening step-by-step as an
animated bar chart in a matplotlib window.

    python bubble_sort_visualizer.py
"""

import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Colors picked for clear semantic contrast against a light background.
COLOR_DEFAULT = "#4C72B0"   # unsorted / idle bar
COLOR_COMPARE = "#DD8452"   # bars currently being compared
COLOR_SWAP = "#C44E52"      # bars currently being swapped
COLOR_SORTED = "#55A868"    # bar locked into its final position


def bubble_sort_steps(values):
    """
    Run bubble sort on a copy of `values`, yielding a snapshot after every
    comparison so the animation can render each individual step.

    Each yielded snapshot is a tuple:
        (array_state, compare_indices, swapped, sorted_boundary)
    """
    arr = values[:]
    n = len(arr)

    for pass_num in range(n):
        swapped_any = False
        for i in range(0, n - pass_num - 1):
            # Highlight the pair being compared this step.
            yield (arr[:], (i, i + 1), False, n - pass_num)

            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                swapped_any = True
                # Highlight the pair right after swapping.
                yield (arr[:], (i, i + 1), True, n - pass_num)

        if not swapped_any:
            break

    # Final fully-sorted state.
    yield (arr[:], (), False, 0)


def animate_bubble_sort(values, interval_ms=300):
    """Build and show the matplotlib animation for bubble-sorting `values`."""
    steps = list(bubble_sort_steps(values))

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.canvas.manager.set_window_title("Bubble Sort Visualizer")

    bar_container = ax.bar(range(len(values)), values, color=COLOR_DEFAULT, edgecolor="white")
    ax.set_xlim(-1, len(values))
    ax.set_ylim(0, max(values) * 1.15)
    ax.set_xticks(range(len(values)))
    ax.set_ylabel("Value")
    ax.set_title("Bubble Sort")

    step_label = ax.text(0.5, 1.05, "", transform=ax.transAxes,
                          ha="center", va="bottom", fontsize=11)

    def update(frame_idx):
        arr, compare_idx, swapped, sorted_boundary = steps[frame_idx]

        for bar, height, idx in zip(bar_container, arr, range(len(arr))):
            bar.set_height(height)
            if idx >= sorted_boundary:
                bar.set_color(COLOR_SORTED)
            elif idx in compare_idx:
                bar.set_color(COLOR_SWAP if swapped else COLOR_COMPARE)
            else:
                bar.set_color(COLOR_DEFAULT)

        if compare_idx:
            action = "Swapping" if swapped else "Comparing"
            step_label.set_text(f"{action} positions {compare_idx[0]} and {compare_idx[1]}  "
                                 f"(step {frame_idx + 1}/{len(steps)})")
        else:
            step_label.set_text(f"Sorted!  (step {frame_idx + 1}/{len(steps)})")

        return list(bar_container) + [step_label]

    anim = animation.FuncAnimation(
        fig, update, frames=len(steps), interval=interval_ms, repeat=False, blit=False
    )
    plt.tight_layout()
    plt.show()
    return anim


if __name__ == "__main__":
    random.seed()
    data = random.sample(range(1, 1000), 100)
    print("Unsorted:", data)
    print("Sorted:  ", sorted(data))
    print("Opening chart window... close it to exit.")

    animate_bubble_sort(data, interval_ms=1)
