#!/usr/bin/env python3
"""
子进程渲染器 - 用于在独立进程中渲染单个LaTeX公式或文本
避免内存积累问题

支持LaTeX语法：
- Display formulas: $$...$$ 和 \\[...\\]
- Inline formulas: $...$ 和 \\(...\\)
"""

import sys
import json
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # 必须在导入pyplot之前设置
import matplotlib.pyplot as plt
import re

# 导入共用的LaTeX处理工具
from latex_utils import (
    LATEX_PREAMBLE,
    LATEX_TABLE_PREAMBLE,
    preprocess_latex,
    preprocess_text_commands,
    preprocess_table_content,
    create_latex_parbox,
    calculate_figure_width,
    is_pure_newcommand,
    trim_image_whitespace
)

# 设置matplotlib使用完整LaTeX
matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.size'] = 12

# 配置LaTeX包
matplotlib.rcParams['text.latex.preamble'] = LATEX_PREAMBLE


# 重复的函数已移动到 latex_utils.py 模块中


def render_display_formula(formula_content: str, output_path: str, dpi: int = 300) -> dict:
    """渲染独立的数学公式 - 使用pdflatex直接编译"""
    import subprocess
    import tempfile
    import shutil
    from pathlib import Path
    
    try:
        # 预处理LaTeX内容
        processed_content = preprocess_latex(formula_content, is_display=True)
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tex_file = tmpdir_path / "formula.tex"
            pdf_file = tmpdir_path / "formula.pdf"
            
            # 针对formula类型优化：使用display math环境，居中显示
            latex_doc = f"""\\documentclass{{article}}
{LATEX_PREAMBLE}
\\usepackage{{geometry}}
\\usepackage{{amsmath}}
\\geometry{{margin=0.5in}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{center}}
{processed_content}
\\end{{center}}
\\end{{document}}
"""
            
            # 写入.tex文件
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_doc)
            
            # 使用pdflatex编译
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir_path), str(tex_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0 or not pdf_file.exists():
                error_msg = f"pdflatex compilation failed: return_code={result.returncode}"
                if result.stderr:
                    error_msg += f", stderr={result.stderr}"
                if result.stdout:
                    error_msg += f", stdout={result.stdout}"
                return {
                    'success': False,
                    'output_path': None,
                    'error': error_msg
                }
            
            # 使用pdftoppm (优先) 或 ImageMagick convert 将PDF转换为PNG
            try:
                # 优先使用pdftoppm (更可靠，支持单页输出)
                subprocess.run(
                    ['pdftoppm', '-png', '-r', str(dpi), '-singlefile', str(pdf_file), str(tmpdir_path / 'formula')],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                png_file = tmpdir_path / 'formula.png'
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果pdftoppm失败，尝试使用ImageMagick的convert
                subprocess.run(
                    ['convert', '-density', str(dpi), str(pdf_file), str(tmpdir_path / 'formula.png')],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                png_file = tmpdir_path / 'formula.png'
            
            if not png_file.exists():
                return {
                    'success': False,
                    'output_path': None,
                    'error': 'PDF to PNG conversion failed'
                }
            
            # 复制PNG文件到目标位置
            shutil.copy(png_file, output_path)
        
        # 进行白边裁剪
        trim_image_whitespace(output_path, dpi)
        
        return {
            'success': True,
            'output_path': output_path,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'output_path': None,
            'error': str(e)
        }


def render_inline_text(text_content: str, output_path: str, dpi: int = 300) -> dict:
    """渲染包含行内公式的文本 - 使用pdflatex直接编译"""
    import subprocess
    import tempfile
    import shutil
    from pathlib import Path
    
    try:
        # 检查是否是纯newcommand定义
        if is_pure_newcommand(text_content):
            raise ValueError(f"纯newcommand定义无法渲染: {text_content.strip()}")
        
        # 预处理LaTeX命令
        preprocessed_text = preprocess_text_commands(text_content)
        
        # 如果文本为空，直接失败
        if not preprocessed_text.strip():
            raise ValueError(f"处理后的文本为空，无法渲染: {text_content.strip()}")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tex_file = tmpdir_path / "text.tex"
            pdf_file = tmpdir_path / "text.pdf"
            
            # 针对text类型优化：设置A4纸页宽，支持自动换行
            latex_doc = f"""\\documentclass{{article}}
{LATEX_TABLE_PREAMBLE}
\\usepackage{{geometry}}
\\usepackage{{amsmath}}
\\geometry{{margin=0.5in}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{center}}
\\parbox{{\\textwidth}}{{
{preprocessed_text}
}}
\\end{{center}}
\\end{{document}}
"""
            
            # 写入.tex文件
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_doc)
            
            # 使用pdflatex编译
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir_path), str(tex_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0 or not pdf_file.exists():
                error_msg = f"pdflatex compilation failed: return_code={result.returncode}"
                if result.stderr:
                    error_msg += f", stderr={result.stderr}"
                if result.stdout:
                    error_msg += f", stdout={result.stdout}"
                return {
                    'success': False,
                    'output_path': None,
                    'error': error_msg
                }
            
            # 使用pdftoppm (优先) 或 ImageMagick convert 将PDF转换为PNG
            try:
                # 优先使用pdftoppm (更可靠，支持单页输出)
                subprocess.run(
                    ['pdftoppm', '-png', '-r', str(dpi), '-singlefile', str(pdf_file), str(tmpdir_path / 'text')],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                png_file = tmpdir_path / 'text.png'
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果pdftoppm失败，尝试使用ImageMagick的convert
                subprocess.run(
                    ['convert', '-density', str(dpi), str(pdf_file), str(tmpdir_path / 'text.png')],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                png_file = tmpdir_path / 'text.png'
            
            if not png_file.exists():
                return {
                    'success': False,
                    'output_path': None,
                    'error': 'PDF to PNG conversion failed'
                }
            
            # 复制PNG文件到目标位置
            shutil.copy(png_file, output_path)
        
        # 进行白边裁剪
        trim_image_whitespace(output_path, dpi)
        
        return {
            'success': True,
            'output_path': output_path,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'output_path': None,
            'error': str(e)
        }


def render_table(table_content: str, output_path: str, dpi: int = 300) -> dict:
    """渲染LaTeX表格 - 使用pdflatex直接编译保持原始样式，支持宽表格"""
    import subprocess
    import tempfile
    import shutil
    from pathlib import Path
    
    try:
        # 直接使用原始表格内容，不进行预处理
        processed_table = table_content.strip()
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tex_file = tmpdir_path / "table.tex"
            pdf_file = tmpdir_path / "table.pdf"
            
            # 统一使用数学模式 + adjustbox 包装所有表格（支持宽表格）
            latex_doc = f"""\\documentclass{{article}}
{LATEX_TABLE_PREAMBLE}
\\usepackage{{geometry}}
\\usepackage{{amsmath}}
\\usepackage{{adjustbox}}
\\geometry{{margin=0.5in}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{center}}
\\begin{{adjustbox}}{{width=\\textwidth,center}}
\\begin{{math}}
{processed_table}
\\end{{math}}
\\end{{adjustbox}}
\\end{{center}}
\\end{{document}}
"""
            
            # 写入.tex文件
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_doc)
            
            # 使用pdflatex编译
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir_path), str(tex_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0 or not pdf_file.exists():
                error_msg = f"pdflatex compilation failed: return_code={result.returncode}"
                if result.stderr:
                    error_msg += f", stderr={result.stderr}"
                if result.stdout:
                    error_msg += f", stdout={result.stdout}"
                return {
                    'success': False,
                    'output_path': None,
                    'error': error_msg
                }
            
            # 使用pdftoppm (优先) 或 ImageMagick convert 将PDF转换为PNG
            try:
                # 优先使用pdftoppm (更可靠，支持单页输出)
                subprocess.run(
                    ['pdftoppm', '-png', '-r', str(dpi), '-singlefile', str(pdf_file), str(tmpdir_path / 'table')],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                png_file = tmpdir_path / 'table.png'
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果pdftoppm失败，尝试使用ImageMagick的convert
                subprocess.run(
                    ['convert', '-density', str(dpi), str(pdf_file), str(tmpdir_path / 'table.png')],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                png_file = tmpdir_path / 'table.png'
            
            if not png_file.exists():
                return {
                    'success': False,
                    'output_path': None,
                    'error': 'PDF to PNG conversion failed'
                }
            
            # 复制PNG文件到目标位置
            shutil.copy(png_file, output_path)
        
        # 进行白边裁剪
        trim_image_whitespace(output_path, dpi)
        
        return {
            'success': True,
            'output_path': output_path,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'output_path': None,
            'error': str(e)
        }


def parse_table_to_matplotlib(table_content: str) -> dict:
    """将LaTeX表格内容解析为matplotlib表格格式"""
    lines = table_content.split('\n')
    table_data = []
    headers = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('\\begin{') or line.startswith('\\end{'):
            continue
        
        # 处理表格行
        if '\\\\' in line:
            # 移除\\和hline
            line = line.replace('\\\\', '')
            line = line.replace('\\hline', '')
            
            # 分割列
            if '&' in line:
                cells = line.split('&')
                # 清理每个单元格
                cleaned_cells = []
                for cell in cells:
                    cell = cell.strip()
                    # 移除LaTeX命令但保留数学符号
                    cell = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', cell)
                    cell = re.sub(r'\\[a-zA-Z]+', '', cell)
                    cell = cell.replace('{', '').replace('}', '')
                    # 处理下标
                    cell = cell.replace('\\_', '_')
                    cleaned_cells.append(cell)
                
                if cleaned_cells:
                    if headers is None:
                        headers = cleaned_cells
                    else:
                        table_data.append(cleaned_cells)
    
    if headers and table_data:
        return {
            'headers': headers,
            'data': table_data
        }
    else:
        return None


def parse_table_to_text(table_content: str) -> str:
    """将LaTeX表格内容解析为纯文本表格"""
    lines = table_content.split('\n')
    table_lines = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('\\begin{') or line.startswith('\\end{'):
            continue
        
        # 处理表格行
        if '\\\\' in line:
            # 移除\\和hline
            line = line.replace('\\\\', '')
            line = line.replace('\\hline', '')
            line = line.replace('\\hline', '')
            
            # 分割列
            if '&' in line:
                cells = line.split('&')
                # 清理每个单元格
                cleaned_cells = []
                for cell in cells:
                    cell = cell.strip()
                    # 移除LaTeX命令
                    cell = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', cell)
                    cell = re.sub(r'\\[a-zA-Z]+', '', cell)
                    cell = cell.replace('{', '').replace('}', '')
                    cleaned_cells.append(cell)
                
                if cleaned_cells:
                    table_lines.append(' | '.join(cleaned_cells))
    
    if table_lines:
        return '\n'.join(table_lines)
    else:
        return "Table content could not be parsed"


def main():
    """主函数 - 从命令行参数获取渲染任务"""
    if len(sys.argv) < 4:
        print("用法: python subprocess_renderer.py <type> <content> <output_path> [dpi]")
        print("type: 'formula', 'text' 或 'table'")
        print("content: LaTeX内容（JSON编码）")
        print("output_path: 输出文件路径")
        print("dpi: 可选，默认300")
        sys.exit(1)
    
    render_type = sys.argv[1]
    content_json = sys.argv[2]
    output_path = sys.argv[3]
    dpi = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    
    try:
        # 解码JSON内容，如果失败则直接使用原始字符串
        try:
            content = json.loads(content_json)
        except json.JSONDecodeError:
            # 如果不是有效的JSON，直接使用原始字符串
            content = content_json
        
        # 如果content是字典且包含content键，提取实际的字符串内容
        if isinstance(content, dict) and 'content' in content:
            content = content['content']
        
        # 根据类型调用相应的渲染函数
        if render_type == 'formula':
            result = render_display_formula(content, output_path, dpi)
        elif render_type == 'text':
            result = render_inline_text(content, output_path, dpi)
        elif render_type == 'table':
            result = render_table(content, output_path, dpi)
        else:
            result = {
                'success': False,
                'output_path': None,
                'error': f"未知的渲染类型: {render_type}"
            }
        
        # 输出结果到stdout（JSON格式）
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            'success': False,
            'output_path': None,
            'error': str(e)
        }
        print(json.dumps(error_result))


if __name__ == "__main__":
    main()
