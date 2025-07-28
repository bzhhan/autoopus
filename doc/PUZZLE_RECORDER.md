# 谜题录制与模拟器

`tools/puzzle_recorder.py` 是一个多功能工具，它既可以从正在运行的游戏中捕捉棋盘状态并将其保存为文件，也可以启动一个图形化界面来加载、分析和交互式地玩这些谜题。

## 1. 核心功能模式

该工具有两种主要的操作模式：`capture` 和 `simulate`。

### a. `capture` 模式：捕捉游戏状态

此模式用于从当前的游戏窗口捕捉棋盘布局，并将其保存为一个 `.json` 文件。这对于保存一个特定的、有趣的或难以解决的谜题以供日后分析非常有用。

**使用方法:**

```bash
python tools/puzzle_recorder.py capture [output_filename.json]
```

-   `output_filename.json` (可选): 指定保存文件的路径和名称。如果省略，文件将以默认名称（如 `puzzle_YYYYMMDD_HHMMSS.json`）保存在 `recordings/` 目录下。

### b. `simulate` 模式：启动模拟器GUI

此模式会启动一个图形用户界面（GUI），你可以在其中加载之前录制的谜题文件，进行交互式操作或使用内置的求解器进行分析。

**使用方法:**

```bash
python tools/puzzle_recorder.py simulate [input_filename.json]
```

-   `input_filename.json` (可选): 如果提供了此参数，GUI启动后会自动加载指定的谜题文件。如果省略，GUI将以一个空白的棋盘开始，你可以通过界面上的“Load Puzzle”按钮手动加载文件。

---

## 2. 模拟器GUI详解

当你运行 `simulate` 模式时，会看到一个包含棋盘和控制面板的窗口。

![GUI界面](/assets/doc/simugui.png)

### a. 加载与交互

-   **Load Puzzle**: 点击此按钮会打开一个文件对话框，让你选择一个由 `capture` 模式或其他工具生成的 `.json` 文件。加载成功后，谜题的初始状态会显示在棋盘上。
-   **手动操作**: 你可以像在游戏中一样，通过点击两个匹配的元素来消除它们。
    -   首先点击一个未锁定的元素，它会被高亮显示。
    -   再点击另一个匹配的、同样未锁定的元素，它们就会被消除。
    -   只有当元素在几何上和逻辑上（例如，金属的消除顺序）都解锁时，才能被选中。
-   **Undo Move**: 每当你手动消除一对元素后，此按钮会变为可用。点击它可以撤销上一步操作，将棋盘恢复到之前的状态。

### b. 求解与提示

-   **Solve Puzzle**: 点击此按钮，A*求解器会开始在后台运行，尝试从**当前**棋盘状态找到一个完整的解法。
    -   求解过程中，状态栏会显示求解器的进度。
    -   求解完成后，如果找到了解法，**Next Move Hint** 按钮将变为可用。
-   **Next Move Hint**: 当解法可用时，点击此按钮会在棋盘上高亮显示建议的下一步操作（即解法路径中的第一步）。这可以用来指导你完成谜题。
    -   如果你不遵循提示，而是执行了其他手动操作，提示将失效，你需要重新求解以获得新的提示。

## 3. 录制文件格式

录制的谜题以 `.json` 格式保存，其结构如下：

```json
{
    "puzzle_name": "custom_puzzle.json",
    "timestamp": "2025-07-28T10:00:00.123456",
    "initial_board_state": [
        { "element": "FIRE", "state": "normal" },
        { "element": "WATER", "state": "normal" },
        // ... more elements
    ],
    "solution_path": [
        // 在'capture'模式下，此字段通常为空
        // 在'puzzle_collector'生成的文件中，此字段会包含解法
    ]
}
```

-   `puzzle_name`: 谜题的名称或源文件名。
-   `timestamp`: 录制时的时间戳。
-   `initial_board_state`: 一个列表，包含了棋盘上每个六边形格子的初始元素和状态。
-   `solution_path`: 一个由求解器找到的解法路径。在 `capture` 模式下，此列表为空，因为此时只记录棋盘状态，尚未求解。

部分已记录的谜题见assets/collected_puzzles

