# 简单LaTeX公式渲染器 (v3.0)

一个**超简单**的LaTeX渲染工具，专为从arXiv论文中提取的JSON文件设计。使用完整的LaTeX引擎(usetex)将数学公式和文本渲染为高质量的PNG图片。

🚀 **v3.0特性**: 
- ✅ 只用usetex，不用mathtext - **简单！**
- ✅ 支持所有LaTeX环境和符号
- ✅ 失败就是失败，不搞复杂的降级
- ✅ 代码简洁，逻辑清晰

## 功能特性

✅ **双重渲染模式**
- `display_formulas`: 独立数学公式渲染（如 $$...$$）
- `inline_texts`: 混合文本和行内公式渲染（如包含 $...$的段落）

✅ **简单LaTeX引擎**
- 只用matplotlib usetex，完整LaTeX渲染
- 自动预处理复杂环境 (`aligned`, `pmatrix`等)
- 支持学术包 (amsmath, amssymb, physics, braket等)
- 无降级机制：**要么成功，要么失败** - 简单！

✅ **高质量输出**
- 300 DPI高分辨率PNG图片
- 可自定义字体大小和样式
- 白色背景，专业排版效果

✅ **批量处理**
- 支持单文件和目录批量处理
- 进度显示和错误统计
- 自动文件命名和组织

## 安装依赖

### ⚠️ 重要: 需要安装LaTeX环境

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install texlive-latex-base texlive-latex-recommended texlive-science

# macOS系统  
brew install --cask basictex
sudo tlmgr update --self
sudo tlmgr install amsmath amssymb physics braket

# 然后安装Python依赖
source venv/bin/activate
pip install -r requirements.txt
```

**系统要求**：
- LaTeX发行版 (TexLive/MiKTeX)
- matplotlib >= 3.5.0
- numpy >= 1.20.0
- Pillow >= 8.0.0

📖 **详细安装指南**: 参见 [INSTALLATION.md](INSTALLATION.md)

## 使用方法

### 1. 单文件处理

```bash
python latex_to_png_renderer.py
```

默认处理 `arxiv_extracted_json/240100001_extracted.json` 文件。

### 2. 批量处理目录

```bash
python batch_renderer.py arxiv_extracted_json/
```

或指定输出目录：

```bash
python batch_renderer.py arxiv_extracted_json/ -o my_output_dir
```

### 3. Python脚本中使用

```python
from latex_to_png_renderer import LaTeXRenderer

# 超简单 - 只需要两个参数
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
    ]
  }
]
```

## 输出结果

### 文件命名规则

- 公式：`{文件名}_formula_{编号}.png`
- 文本：`{文件名}_text_{编号}.png`

例如：
- `240100001_extracted_formula_001.png`
- `240100001_extracted_text_001.png`

### 处理统计

v2.0增强版本处理统计：
```
=== 批量处理完成 ===
总计渲染公式: 106 个
总计渲染文本: 1259 个
总计错误: 45 个  ⬅️ 大幅减少!

渲染统计信息
==================================================
usetex成功: 1186 (89.2%)     ⬅️ 主要渲染引擎
mathtext降级: 134 (10.1%)    ⬅️ 智能降级
完全失败: 45 (0.7%)          ⬅️ 显著改善!
总体成功率: 99.3%
```

## 支持的LaTeX功能 (v2.0大幅扩展!)

### 🎉 **完全支持** (usetex引擎)
- **基础符号**: `+`, `-`, `*`, `/`, `=`, `<`, `>`, `\leq`, `\geq`
- **希腊字母**: `\alpha`, `\beta`, `\gamma`, `\pi`, `\sigma`, `\omega`等
- **上下标**: `x^2`, `x_i`, `x^{2+3}`, `x_{i,j}`
- **分数根号**: `\frac{a}{b}`, `\sqrt{x}`, `\sqrt[n]{x}`
- **积分求和**: `\sum`, `\int`, `\prod`, `\oint`, `\iint`
- **复杂环境**: `\begin{aligned}`, `\begin{pmatrix}`, `\begin{bmatrix}`
- **物理符号**: `\hat{H}`, `\dagger`, `\langle`, `\rangle`, `\braket{}`
- **文本模式**: `\text{...}`, `\textbf{...}`, `\mathcal{A}`
- **学术包**: amsmath, amssymb, physics, braket 等

### ✅ **智能处理** (预处理优化)
- 自动包装复杂环境 (`aligned` → `equation*`)
- 智能转义特殊字符 (`&`, `_`, `#`)
- 量子力学符号优化
- 矩阵环境标准化

### 🔄 **降级支持** (mathtext备用)
- usetex失败时自动降级
- 保持基础数学渲染能力
- 特殊标记降级内容 (浅蓝背景)

### ⚠️ **仍有限制**
- TikZ绘图 (需要外部渲染)
- 自定义宏定义 (会被预处理移除)
- 复杂表格环境

## 简单的处理逻辑

v3.0彻底简化了处理逻辑：

### 🎯 **只有一层：usetex渲染**
- 使用完整LaTeX引擎
- 支持所有学术包和复杂环境
- 失败就是失败，不搞复杂的降级
- **简单！清晰！**

### 📊 **简单统计信息**

```bash
渲染统计信息
==================================================
成功: 1186 (89.2%)
失败: 179 (10.8%)
```

## 性能优化建议

1. **大批量处理**：考虑分批处理，避免内存占用过大
2. **自定义DPI**：降低DPI可提高处理速度（默认300）
3. **输出目录**：使用SSD存储输出目录以提高I/O性能

## 常见问题

### Q: 如何安装LaTeX环境？
A: **需要LaTeX环境**。Ubuntu运行 `sudo apt install texlive-latex-base texlive-latex-recommended`，详见 [INSTALLATION.md](INSTALLATION.md)

### Q: 为什么不降级到mathtext？
A: **简单就是美！** 要么用完整LaTeX，要么失败。不搞复杂的降级逻辑。

### Q: 某些公式仍然渲染失败怎么办？
A: **检查LaTeX语法！** 失败就是失败，修复公式后重新运行。简单直接！

### Q: 渲染速度变慢了？
A: usetex确实比mathtext慢，但质量最高。可以降低DPI来提升速度。

## 更新日志

### 🚀 v3.0 (简单版本) - 当前版本
- ✅ **彻底简化**: 删除所有mathtext降级代码
- ✅ **只用usetex**: 要么成功，要么失败
- ✅ **代码简洁**: 减少50%代码量
- ✅ **逻辑清晰**: 没有复杂的降级机制

## 示例结果

处理前的JSON内容：
```json
{
  "content": "$$E = mc^2$$"
}
```

处理后生成：`formula_001.png` - 包含渲染的数学公式的PNG图片。

## 贡献和反馈

如果遇到问题或有改进建议，请：
1. 检查LaTeX语法是否正确
2. 查看错误日志
3. 尝试简化公式后重试

---

**作者注**：此工具专为arXiv论文数据处理设计，针对学术文献中的数学公式和文本渲染进行了优化。
