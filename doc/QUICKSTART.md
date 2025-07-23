# 快速上手指南

本指南将引导你完成 Opus Magnum Bot 的安装、配置和首次运行。

## 1. 环境要求

- **操作系统**: Windows 10/11
- **Python**: 3.8 或更高版本
- **游戏**: Steam 版本的《Opus Magnum》

## 2. 安装步骤

### a. 克隆项目仓库

打开命令行工具，克隆本项目到本地：

```bash
git clone https://github.com/bzhhan/autoopus.git
cd opus-magnum-bot
```

*(注意: 请将 `your-username/opus-magnum-bot.git` 替换为实际的项目地址)*

### b. 安装 Python 依赖

使用 `pip` 安装所有必需的库：

```bash
pip install -r requirements.txt
```

## 3. 首次配置

在运行脚本之前，需要对其进行配置以适应你的游戏环境。配置文件位于 `config/` 目录下。

1.  **复制配置文件**:
    *   将 `config/grid_config.json.example` 复制为 `config/grid_config.json`。
    *   将 `config/solver_config.json.example` 复制为 `config/solver_config.json`。
    *   将 `config/interrupt_config.json.example1` 复制为 `config/interrupt_config.json`。

2.  **配置 `grid_config.json`**:
    默认设置使用1440x900窗口，如果使用其他分辨率，请重新设置坐标。详细配置参考用户手册。
    *   **`window_title`**: 确保这与你的游戏窗口标题匹配。
    *   **`grid_origin`**: 棋盘标志点像素坐标 (x, y)。
    *   **`hex_size`**: 六边形的宽度。
    *   **`ui_points`**: 游戏中各个按钮（如“开始新游戏”）的坐标。

    **提示**: 可以使用屏幕截图工具来精确测量这些像素坐标。

## 4. 运行脚本

配置完成后，就可以启动脚本了。

1.  启动《Opus Magnum》并进入一个西格玛花园谜题。
2.  打开一个新的命令行窗口，导航到项目根目录。
3.  执行以下命令：

    *   **运行一次**:
        ```bash
        python main.py
        ```

    *   **无限次连续运行**:
        ```bash
        python main.py -c
        ```

    *   **指定次数连续运行 (例如 10 次)**:
        ```bash
        python main.py -c 10
        ```

脚本启动后，你会在游戏窗口上看到一个半透明的覆盖层，显示其当前状态。