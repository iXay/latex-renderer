# LaTeX公式渲染器

一个专为从arXiv论文中提取的JSON文件设计的LaTeX渲染工具。使用完整的LaTeX引擎(usetex)将数学公式和文本渲染为高质量的PNG图片。

## 背景描述

本项目旨在从一批 LaTeX 文本中渲染出对应的图像，从而形成 (文本, 图像) 的数据对，用来作为 ground_truth 的训练数据.
- 图像的渲染过程应该尽量还原文本中描述的真实内容。
- 保持简单，尽量使用 general 的方法，少用 trivial 的 trick


## 功能特性

✅ **三重渲染模式**
- `display_formulas`: 独立数学公式渲染（如 $$...$$）
- `inline_texts`: 混合文本和行内公式渲染（如包含 $...$的段落）
- `tables`: LaTeX表格渲染（如 \begin{tabular}...\end{tabular}）

✅ **pdflatex直接编译**
- 使用pdflatex直接编译LaTeX文档，确保完整兼容性
- 支持学术包 (amsmath, amssymb, physics, braket等)
- 自动预处理复杂环境 (`aligned`, `pmatrix`等)
- 支持中文字符渲染
- 子进程架构避免内存积累问题

✅ **高质量输出**
- 300 DPI高分辨率PNG图片
- 自动白边裁剪和空白图片检测
- 白色背景，专业排版效果
- PDF转PNG确保最佳质量

✅ **批量处理**
- 支持单文件和目录批量处理
- 多进程并发处理
- 断点续传功能
- 分布式缓存系统

## 环境安装

### 1. 安装LaTeX环境

**推荐方案：安装完整的LaTeX发行版**

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install texlive-full

# macOS系统  
brew install --cask mactex

# Windows系统
# 下载并安装 MiKTeX 或 TeX Live
```

**系统要求**：
- LaTeX发行版 (TexLive/MiKTeX) - **必需**
- PDF转换工具 (Poppler/pdftoppm 或 ImageMagick) - **必需**
- Python 3.8+
- matplotlib >= 3.5.0
- numpy >= 1.20.0
- Pillow >= 8.0.0

### 2. 安装PDF转换工具

**推荐方案：安装 Poppler 工具包（包含 pdftoppm）**

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install poppler-utils

# macOS系统（使用Homebrew）
brew install poppler

# Windows系统
# 下载并安装 Poppler for Windows
# https://blog.alivate.com.au/poppler-windows/
```

**备选方案：安装 ImageMagick**

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install imagemagick

# macOS系统
brew install imagemagick

# Windows系统
# 下载并安装 ImageMagick for Windows
# https://imagemagick.org/script/download.php#windows
```

**验证安装**：
```bash
# 检查pdftoppm是否可用
pdftoppm -h

# 检查ImageMagick是否可用
convert -version
```

### 3. 安装Python依赖

```bash
# 激活虚拟环境（推荐）
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**注意**：本工具使用pdflatex直接编译，不依赖matplotlib的usetex功能，因此需要完整的LaTeX环境。

## 技术架构

本工具采用以下技术架构：

1. **主进程**：`latex_to_png_renderer.py` 和 `batch_renderer.py` 负责文件管理和任务调度
2. **子进程渲染**：`subprocess_renderer.py` 在独立进程中执行实际的LaTeX编译
3. **编译流程**：LaTeX源码 → pdflatex编译 → PDF文件 → pdftoppm/convert转换 → PNG图片
4. **缓存系统**：`distributed_cache.py` 提供分布式缓存和断点续传功能
5. **工具模块**：`latex_utils.py` 提供共用的LaTeX处理函数

**优势**：
- 避免matplotlib内存积累问题
- 完整LaTeX兼容性（支持所有LaTeX包）
- 高质量PDF输出转PNG
- 支持大规模批量处理

## 使用方法

### 1. 单文件处理

使用 `latex_to_png_renderer.py` 处理单个JSON文件：

```bash
python latex_to_png_renderer.py <json_file_path>
```

**示例**：
```bash
python latex_to_png_renderer.py arxiv_extracted_json/240100017_extracted.json
```

**输出**：
- 渲染的PNG图片保存在 `rendered_images/` 目录
- 文件命名格式：`{文件名}_doc{文档编号}_formula_{编号}.png` 或 `{文件名}_doc{文档编号}_text_{编号}.png`

### 2. 批量处理

使用 `batch_renderer.py` 批量处理多个JSON文件：

#### 基本用法

```bash
python batch_renderer.py <file_list_path>
```

其中 `file_list_path` 是一个包含JSON文件路径列表的文本文件，每行一个文件路径。

#### 完整参数

```bash
python batch_renderer.py <file_list_path> [选项]
```

**主要参数**：
- `file_list_path`: 包含JSON文件路径列表的描述文件
- `-o, --output`: 输出目录 (默认: rendered_images)
- `-n, --max-files`: 最大处理文件数量 (默认: 处理全部文件)
- `-j, --max-workers`: 最大并发工作进程数 (默认: 4)
- `--resume`: 断点续传模式，跳过已处理的文件
- `-r, --render-type`: 渲染类型 (formula/text/table/all，默认: all)

**示例**：
```bash
# 基本批量处理
python batch_renderer.py arxiv_file_list.txt

# 指定输出目录和并发数
python batch_renderer.py arxiv_file_list.txt -o my_output -j 8

# 断点续传模式
python batch_renderer.py arxiv_file_list.txt --resume

# 只渲染公式
python batch_renderer.py arxiv_file_list.txt -r formula

# 只渲染表格
python batch_renderer.py arxiv_file_list.txt -r table

# 渲染所有类型（公式、文本、表格）
python batch_renderer.py arxiv_file_list.txt -r all
```

### 3. Python脚本中使用

```python
from latex_to_png_renderer import LaTeXRenderer

# 创建渲染器
renderer = LaTeXRenderer(
    output_dir="my_images", 
    dpi=300
)

# 处理单个文件
results = renderer.process_json_file("path/to/file.json")

# 渲染单个公式
renderer.render_display_formula("E = mc^2", "einstein_formula")

# 渲染包含公式的文本  
text = "The famous equation is $E = mc^2$ where E is energy."
renderer.render_inline_text(text, "mixed_text")

# 渲染LaTeX表格
table = "\\begin{tabular}{|c|c|}\\hline A & B \\\\ \\hline 1 & 2 \\\\ \\hline\\end{tabular}"
renderer.render_table(table, "sample_table")
```

## 输入文件格式

支持如下JSON结构：

```json
[
  {
    "file_path": "...",
    "display_formulas": [
      {
        "content": "$$E = mc^2$$",
        "start": 1234,
        "end": 1245,
        "metadata": {...}
      }
    ],
    "inline_texts": [
      {
        "content": "Einstein's equation $E = mc^2$ is fundamental.",
        "start": 2345,
        "end": 2389,
        "metadata": {...}
      }
    ],
    "tables": [
      {
        "content": "\\begin{tabular}{|c|c|}\\hline A & B \\\\ \\hline 1 & 2 \\\\ \\hline\\end{tabular}",
        "start": 3456,
        "end": 3500,
        "metadata": {...}
      }
    ]
  }
]
```

## 输出结果

### 文件命名规则

- 公式：`{文件名}_doc{文档编号}_formula_{编号}.png`
- 文本：`{文件名}_doc{文档编号}_text_{编号}.png`
- 表格：`{文件名}_doc{文档编号}_table_{编号}.png`

例如：
- `240100001_extracted_doc001_formula_001.png`
- `240100001_extracted_doc001_text_001.png`
- `240100001_extracted_doc001_table_001.png`

### 处理统计

批量处理完成后会显示统计信息：
```
=== 批量处理完成 ===
总计渲染公式: 106 个
总计渲染文本: 1259 个
总计渲染表格: 23 个
总计错误: 45 个

渲染统计信息
==================================================
成功: 1209 (89.2%)
失败: 179 (10.8%)
```

## 支持的LaTeX功能

### 完全支持 (pdflatex直接编译)
- **基础符号**: `+`, `-`, `*`, `/`, `=`, `<`, `>`, `\leq`, `\geq`
- **希腊字母**: `\alpha`, `\beta`, `\gamma`, `\pi`, `\sigma`, `\omega`等
- **上下标**: `x^2`, `x_i`, `x^{2+3}`, `x_{i,j}`
- **分数根号**: `\frac{a}{b}`, `\sqrt{x}`, `\sqrt[n]{x}`
- **积分求和**: `\sum`, `\int`, `\prod`, `\oint`, `\iint`
- **复杂环境**: `\begin{aligned}`, `\begin{pmatrix}`, `\begin{bmatrix}`
- **物理符号**: `\hat{H}`, `\dagger`, `\langle`, `\rangle`, `\braket{}`
- **文本模式**: `\text{...}`, `\textbf{...}`, `\mathcal{A}`
- **学术包**: amsmath, amssymb, physics, braket 等
- **中文字符**: 自动处理中文文本
- **表格环境**: `\begin{tabular}`, `\begin{array}`, `\begin{table}`

### 智能处理
- 自动包装复杂环境 (`aligned` → `equation*`)
- 智能转义特殊字符 (`&`, `_`, `#`)
- 量子力学符号优化
- 矩阵环境标准化
- 子进程架构避免内存积累
- 自动白边裁剪和空白图片检测

## 性能优化建议

1. **大批量处理**：考虑分批处理，避免内存占用过大
2. **自定义DPI**：降低DPI可提高处理速度（默认300）
3. **输出目录**：使用SSD存储输出目录以提高I/O性能
4. **并发设置**：根据CPU核心数调整 `-j` 参数

## 常见问题

### Q: 如何安装LaTeX环境？
A: 推荐安装完整的LaTeX发行版。Ubuntu运行 `sudo apt install texlive-full`，macOS运行 `brew install --cask mactex`。

### Q: 如何安装PDF转换工具？
A: 推荐安装Poppler工具包：Ubuntu运行 `sudo apt install poppler-utils`，macOS运行 `brew install poppler`。备选方案是安装ImageMagick。

### Q: 某些公式仍然渲染失败怎么办？
A: 检查LaTeX语法是否正确，查看错误日志获取详细信息。本工具使用pdflatex直接编译，兼容性更好。

### Q: 渲染速度变慢了？
A: pdflatex编译确实比matplotlib快，但质量最高。可以降低DPI来提升速度，或调整并发数。

### Q: 如何处理大量文件？
A: 使用 `batch_renderer.py` 的 `--resume` 参数支持断点续传，避免重复处理。分布式缓存系统提供更好的性能。

## 示例结果

处理前的JSON内容：
```json
{
  "content": "$$E = mc^2$$"
}
```

处理后生成：`formula_001.png` - 包含渲染的数学公式的PNG图片。

---

**作者注**：此工具专为arXiv论文数据处理设计，针对学术文献中的数学公式和文本渲染进行了优化。