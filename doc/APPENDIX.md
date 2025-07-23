# 附录


## 1. 启发式函数调参

A* 求解器的核心在于其启发式函数 (`h_cost`)，它评估了当前棋盘状态的“优劣”。通过调整其权重，可以显著改变求解器的行为和效率。

### a. 权重参数说明

这些参数位于 `config/solver_config.json` 中：

-   `remaining_elements_factor`: 剩余元素数量的权重。这是最基础的评估，值越高，求解器越倾向于快速消除任何元素。
-   `locked_marbles_penalty`: 被锁定（无法消除）的元素的惩罚权重。值越高，求解器会越优先尝试解锁这些元素。
-   `salt_marbles_reward`: “盐”元素的奖励权重。因为盐是万能配对元素，保留它可以增加后续的灵活性。这是一个负向惩罚（即奖励），值越高，求解器越倾向于保留盐。
-   `metal_marbles_penalty`: 金属元素的惩罚权重。因为金属元素配对规则复杂（必须按顺序消除），所以给予高惩罚可以优先消除金属。

### b. 如何使用动态调参工具

`tools/dynamic_tuner.py` 是一个用于自动测试和评估上述参数的工具。

**示例**: 测试 `metal_marbles_penalty` 参数，范围从 1.0 到 2.0，分 50 步，每个值测试 5 个谜题：
    ```bash
    python tools/dynamic_tuner.py tune --param metal_marbles_penalty --start 1.0 --end 2.0 --steps 50 --puzzles 5
    ```
    -   `--param`: 要调整的参数名（必须与配置文件中的键名一致）。
    -   `--start`, `--end`: 测试范围的起始值和结束值。
    -   `--steps`: 在该范围内取多少个测试点。
    -   `--puzzles`: 每个参数值要跑多少个谜题来取样。

    工具会自动运行游戏，记录每次成功求解的时间，并将数据保存在 `assets/analysis/[param_name]/time.csv`。

3.  **运行绘图模式**: 测试完成后，使用 `plot` 子命令来可视化结果。

    **示例**: 绘制 `metal_marbles_penalty` 的性能图：
    ```bash
    python tools/dynamic_tuner.py plot --param metal_marbles_penalty
    ```
    -   `--window`: (可选) 移动平均线的窗口大小，用于平滑曲线。

    该命令会读取对应的 `time.csv` 文件，并生成一张散点图和移动平均曲线图，保存为 `assets/analysis/[param_name]/[param_name]_performance_plot.png`。通过观察曲线的波谷，你可以找到该参数的最优值。

### c. 调参实例分析

下图是使用动态调参工具对 `metal_marbles_penalty` 参数进行测试后生成的一个性能分析图。

![金属惩罚参数性能图](../assets/analysis/metal_marbles_penalty/metal_marbles_penalty_performance_plot.png)

可根据此图调节参数

## 2. 中断条件估计 (Interrupt Condition Estimation)

为了最大化单位时间内的解题效率，我们需要一个合理的超时机制：在某个谜题上花费过多时间是不划算的，主动放弃并开始下一个可能更优。`tools/performance_analyzer.py` 工具就是为此设计的。

### a. 收集性能数据

首先，使用 `run` 模式来收集基准性能数据。该工具会多次运行解谜循环，并记录下每次成功解谜的“求解器时间”和“其他时间”（如截图、点击等）。

```bash
python tools/performance_analyzer.py run --runs 100
```
数据会保存在 `assets/analysis/total/performance.csv`。运行的次数越多，后续的估算越准确。

### b. 分析性能分布

收集数据后，可以使用 `plot` 模式来可视化性能数据。

```bash
python tools/performance_analyzer.py plot
```
这会生成一张包含两个直方图的图像，保存在 `assets/analysis/total/performance_histogram.png`。

![性能数据直方图](../assets/analysis/total/performance_histogram.png)

*   **左图 (Solver Time Distribution)**: 显示了求解器成功找到解法所需时间的分布。
*   **右图 (Other Time Distribution)**: 显示了除求解器计算之外的其他固定开销（如截图、分析、点击、等待加载等）的时间分布。

### c. 估算最优超时

。使用 `estimate` 模式，工具会根据历史数据，计算出能最大化“每小时解题数”的最佳超时时间。

```bash
python tools/performance_analyzer.py estimate --plot
```

该命令会输出详细的分析过程和结果，并生成一张吞吐率分析图，保存在 `assets/analysis/total/optimal_timeout_plot.png`。

![最优超时估算图](../assets/analysis/total/optimal_timeout_plot.png)

根据上图分析，横轴代表我们设定的“超时时间”，纵轴代表对应的“吞吐率”（每秒解题数）。曲线的峰值就是我们的最优点。从图中可以看出，将超时时间设置在 **11.5秒** 左右时，我们可以达到最高的解题效率，大约每小时能解决101个谜题。将这个值设置为 `interrupt_config.json` 中的超时条件，即可实现最大化的自动化效率。

由于硬件存在差异，可以自行运行来估计最佳中断条件。
