#!/usr/bin/env python3
"""
LaTeX to PNG Renderer
渲染JSON文件中的LaTeX公式和文本为PNG图片

支持：
- display_formulas: 独立的数学公式（$$...$$）
- inline_texts: 包含行内公式的文本段落
"""

import json
import re
import os
import sys
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import mathtext
import numpy as np
from PIL import Image, ImageOps

# 设置matplotlib使用完整LaTeX
matplotlib.rcParams['text.usetex'] = True  # 使用完整LaTeX渲染
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.size'] = 12

# 配置LaTeX包
matplotlib.rcParams['text.latex.preamble'] = r'''
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{physics}
\usepackage{braket}
\usepackage{bm}
\usepackage{mathtools}
\usepackage{xcolor}
\usepackage{natbib}
\usepackage{graphicx}
% Custom macro definitions for scientific papers
\newcommand{\vvir}{v_{\text{vir}}}
\newcommand{\vdm}{v_{\text{DM}}}
\newcommand{\mwd}{M_{\text{WD}}}
\newcommand{\mpbh}{M_{\text{PBH}}}
\newcommand{\Rwd}{R_{\text{WD}}}
\newcommand{\Rpbh}{R_{\text{PBH}}}
\newcommand{\fmergewb}{f_{\text{merge}}^{\text{WD-PBH}}}
\newcommand{\fmin}{f_{\text{min}}}
\newcommand{\fmax}{f_{\text{max}}}
\newcommand{\fpbh}{f_{\text{PBH}}}
\newcommand{\Mc}{\mathcal{M}_c}
\newcommand{\calO}{\mathcal{O}}
\newcommand{\vrel}{v_{\text{rel}}}
\newcommand{\diff}[2]{\frac{\mathrm{d}#1}{\mathrm{d}#2}}
\newcommand{\ee}{\mathrm{e}}
\newcommand{\us}{\mathrm{s}}
\newcommand{\um}{\mathrm{m}}
\newcommand{\uh}{\mathrm{h}}
\newcommand{\umin}{\mathrm{min}}
\newcommand{\umax}{\mathrm{max}}
\newcommand{\WD}{\text{WD}}
\newcommand{\PBH}{\text{PBH}}
\newcommand{\MS}{\text{MS}}
% Additional macros for text rendering
\newcommand{\ac}[1]{\text{#1}}
\newcommand{\acp}[1]{\text{#1s}}
\newcommand{\si}[1]{\,\text{#1}}
% Fix \df command
\newcommand{\df}{\,\mathrm{d}f}
% Add missing \ms command for composite indices
\newcommand{\ms}[1]{#1}
% Add missing \pbg command (parallel/propagator)
\newcommand{\pbg}{\text{p}}
% Add missing \ud and \uD commands (differential symbols)
\newcommand{\ud}{\mathrm{d}}
\newcommand{\uD}{\mathrm{D}}
% Add missing Greek letters
\newcommand{\vkappa}{\kappa}
% Add missing \bs command
\newcommand{\bs}{\boldsymbol}
% Add missing \ord command (order)
\newcommand{\ord}[2]{\mathcal{O}^{(#1)}(#2)}
% Add missing \mc command (mathcal)
\newcommand{\mc}{\mathcal}
'''


class LaTeXRenderer:
    """增强的LaTeX到PNG渲染器 - 使用完整usetex引擎"""

    def __init__(self, output_dir: str = "rendered_images", dpi: int = 300):
        """
        初始化渲染器

        Args:
            output_dir: 输出目录
            dpi: 图片分辨率
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.dpi = dpi

        # A4纸宽度（英寸）：210mm = 8.27英寸
        self.a4_width_inches = 8.27
        self.horizontal_padding = 0.5  # 水平padding（英寸）

        # 统计信息
        self.stats = {
            'success': 0,
            'errors': 0
        }
        
        # 子进程渲染器脚本路径
        self.subprocess_script = Path(__file__).parent / "subprocess_renderer.py"

    def _render_with_subprocess(self, content: str, output_path: str, render_type: str) -> str:
        """
        使用子进程渲染LaTeX内容
        
        Args:
            content: LaTeX内容
            output_path: 输出文件路径
            render_type: 渲染类型 ('formula' 或 'text')
            
        Returns:
            生成的PNG文件路径，失败时返回None
        """
        try:
            # 将内容编码为JSON字符串
            content_json = json.dumps(content)
            
            # 构建子进程命令
            cmd = [
                sys.executable,
                str(self.subprocess_script),
                render_type,
                content_json,
                output_path,
                str(self.dpi)
            ]
            
            # 运行子进程
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode != 0:
                print(f"✗ 子进程渲染失败 {output_path}: {result.stderr}")
                return None
            
            # 解析结果
            try:
                result_data = json.loads(result.stdout.strip())
                if result_data['success']:
                    return result_data['output_path']
                else:
                    print(f"✗ 子进程渲染失败 {output_path}: {result_data['error']}")
                    return None
            except json.JSONDecodeError:
                print(f"✗ 子进程输出解析失败 {output_path}: {result.stdout}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"✗ 子进程渲染超时 {output_path}")
            return None
        except Exception as e:
            print(f"✗ 子进程渲染异常 {output_path}: {e}")
            return None

    def trim_image_whitespace(self, image_path: str) -> str:
        """
        移除图片周围的白边

        Args:
            image_path: 图片路径

        Returns:
            处理后的图片路径
        """
        try:
            # 打开图片
            img = Image.open(image_path)

            # 转换为RGB模式（如果需要）
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 转换为numpy数组进行处理
            img_array = np.array(img)
            height, width = img_array.shape[:2]

            # 定义白色阈值（考虑到可能的抗锯齿）
            white_threshold = 250  # 接近白色的像素都被认为是背景

            # 检测非白色像素
            # 对于RGB图片，检查所有通道都接近白色的像素
            non_white_mask = np.any(img_array < white_threshold, axis=2)

            # 找到包含非白色像素的行和列
            non_white_rows = np.where(np.any(non_white_mask, axis=1))[0]
            non_white_cols = np.where(np.any(non_white_mask, axis=0))[0]

            if len(non_white_rows) > 0 and len(non_white_cols) > 0:
                # 计算裁剪边界
                top = non_white_rows[0]
                bottom = non_white_rows[-1] + 1
                left = non_white_cols[0]
                right = non_white_cols[-1] + 1

                # 添加小量的padding（可选）
                padding = 5  # 像素
                top = max(0, top - padding)
                left = max(0, left - padding)
                bottom = min(height, bottom + padding)
                right = min(width, right + padding)

                # 裁剪图片
                cropped_img = img.crop((left, top, right, bottom))

                # 保存回原文件
                cropped_img.save(image_path, 'PNG', dpi=(self.dpi, self.dpi))
                print(
                    f"  ✓ 已移除白边: {image_path} (从 {width}x{height} 裁剪到 {right-left}x{bottom-top})")
            else:
                print(f"  ⚠ 未检测到内容，跳过裁剪: {image_path}")

            return image_path

        except Exception as e:
            print(f"  ⚠ 白边移除失败 {image_path}: {e}")
            return image_path

    def preprocess_latex(self, latex_content: str, is_display: bool = True) -> str:
        """
        预处理LaTeX内容，优化为usetex兼容格式
        """
        # 移除前后的$$符号
        content = latex_content.strip()
        if content.startswith('$$') and content.endswith('$$'):
            content = content[2:-2].strip()
        elif content.startswith('$') and content.endswith('$'):
            content = content[1:-1].strip()

        # 修复下标问题：将转义的下划线 \\_ 改为正常下标 _
        # 这是为了修复JSON中 MOM\\_{nM} 导致的下标渲染问题
        content = content.replace('\\_', '_')

        # 修复特殊情况：将 word$_$word 格式转换为 word_{word}
        # 这修复了 MOM$\_$7M 这类格式在parbox中的渲染问题
        # import re
        # content = re.sub(r'(\w+)\$_\$(\w+)', r'\1_{\2}', content)

        # 处理需要完整数学环境的内容
        if is_display:
            # 如果是display模式，需要包装在数学环境中
            if '\\begin{aligned}' in content:
                # 对于aligned环境，直接使用$$包围，避免嵌套环境问题
                content = f'$${content}$$'
            elif '\\begin{pmatrix}' in content or '\\begin{bmatrix}' in content:
                content = f'$${content}$$'
            else:
                # 普通公式也需要数学环境
                content = f'${content}$'

        # 处理转义字符
        content = content.replace('\\&', '\\text{\\&}')

        # 处理text环境中的特殊字符
        content = re.sub(r'\\text\{([^}]*)\}',
                         lambda m: f'\\text{{{m.group(1).replace("&", "\\&")}}}',
                         content)

        return content

    def calculate_figure_width(self, text_content: str, is_display: bool = False) -> float:
        """
        根据文本内容计算合适的图片宽度

        Args:
            text_content: 文本内容
            is_display: 是否为display公式

        Returns:
            图片宽度（英寸）
        """
        # 对于display公式，使用固定的较大宽度
        if is_display:
            min_width = 0.4 * self.a4_width_inches
            max_width = 1.0 * self.a4_width_inches
            return random.uniform(min_width, max_width)

        # 对于文本，在A4纸宽度范围内随机选择
        min_width = 0.4 * self.a4_width_inches
        max_width = 1.0 * self.a4_width_inches
        return random.uniform(min_width, max_width)

    def create_latex_parbox(self, text: str, target_width_inches: float) -> str:
        """
        使用LaTeX parbox控制文本宽度，让LaTeX处理换行

        Args:
            text: 原始文本
            target_width_inches: 目标宽度（英寸）

        Returns:
            包装在parbox中的LaTeX文本
        """
        # 计算内容宽度（英寸转换为点，1英寸 = 72.27pt）
        content_width_pt = (target_width_inches - 2 *
                            self.horizontal_padding) * 72.27

        # 使用LaTeX parbox让LaTeX处理换行
        latex_text = f"\\parbox{{{content_width_pt:.2f}pt}}{{{text}}}"

        return latex_text

    def preprocess_text_commands(self, text: str) -> str:
        """
        在换行之前预处理LaTeX命令，避免命令被换行截断

        Args:
            text: 原始文本

        Returns:
            预处理后的文本
        """
        processed_text = text

        # 处理百分号注释 - 在parbox环境中，%注释会破坏结构
        # 移除%及其后面的内容，但保留已经转义的\%
        processed_text = re.sub(
            r'(?<!\\)%.*$', '', processed_text, flags=re.MULTILINE)

        # 处理引用命令 - 将它们转换为简单的文本格式
        # \citep{ref1,ref2} -> [ref1, ref2]
        processed_text = re.sub(r'\\citep\{([^}]+)\}', r'[\1]', processed_text)
        # \cite{ref1,ref2} -> (ref1, ref2)
        processed_text = re.sub(r'\\cite\{([^}]+)\}', r'(\1)', processed_text)
        # \citet{ref1} -> ref1
        processed_text = re.sub(r'\\citet\{([^}]+)\}', r'\1', processed_text)

        # 处理subsection和section命令，将其转换为简单的标题文本
        processed_text = re.sub(
            r'\\subsection\{([^}]+)\}', r'\1', processed_text)
        processed_text = re.sub(r'\\section\{([^}]+)\}', r'\1', processed_text)

        # 移除newcommand定义
        processed_text = re.sub(
            r'\\newcommand\{[^}]+\}(?:\[[0-9]+\])?\{[^}]*\}', '', processed_text)

        # 处理其他常见的LaTeX命令
        processed_text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', processed_text)
        processed_text = re.sub(r'\\textit\{([^}]+)\}', r'\1', processed_text)
        processed_text = re.sub(r'\\emph\{([^}]+)\}', r'\1', processed_text)

        # 处理caption命令 - 同时处理有闭合和无闭合大括号的情况
        # 先处理有闭合大括号的情况
        processed_text = re.sub(
            r'\\caption\{([^}]+)\}', r'Caption: \1', processed_text)
        # 然后处理无闭合大括号的情况（通常是文本截断导致的）
        processed_text = re.sub(
            r'\\caption\{(.*)$', r'Caption: \1', processed_text)

        # 修复多余的大括号（通常出现在文本片段末尾）
        # 移除文本末尾孤立的 }
        processed_text = re.sub(r'\s*\}\s*$', '', processed_text)
        # 修复 $...$ } 格式为 $...$
        processed_text = re.sub(r'\$([^$]+)\$\s*\}', r'$\1$', processed_text)

        # 处理双反斜杠换行符
        processed_text = processed_text.replace('\\\\', ' ')

        return processed_text.strip()

    def _categorize_latex_error(self, error_message: str) -> str:
        """
        根据错误消息对LaTeX错误进行分类
        """
        error_str = str(error_message).lower()

        if 'undefined control sequence' in error_str:
            return "UndefinedCommand"
        elif 'missing' in error_str and ('$' in error_str or 'math' in error_str):
            return "MathModeError"
        elif 'extra' in error_str and ('alignment' in error_str or '&' in error_str):
            return "AlignmentError"
        elif 'missing' in error_str and ('{' in error_str or '}' in error_str):
            return "BraceError"
        elif 'package' in error_str and 'not found' in error_str:
            return "PackageError"
        elif 'timeout' in error_str or 'time' in error_str:
            return "TimeoutError"
        elif 'unicode' in error_str or 'encoding' in error_str:
            return "EncodingError"
        elif 'memory' in error_str or 'capacity' in error_str:
            return "MemoryError"
        else:
            return "LaTeXSyntaxError"

    def render_display_formula(self, formula_content: str, filename: str) -> str:
        """
        渲染独立的数学公式

        Args:
            formula_content: 公式内容
            filename: 输出文件名（不含扩展名）

        Returns:
            生成的PNG文件路径
        """
        output_path = self.output_dir / f"{filename}.png"
        
        # 使用子进程渲染
        result = self._render_with_subprocess(formula_content, str(output_path), 'formula')
        if result:
            # 进行白边裁剪
            self.trim_image_whitespace(str(output_path))
            self.stats['success'] += 1
            print(f"✓ 渲染公式成功: {output_path}")
            return result
        else:
            self.stats['errors'] += 1
            print(f"✗ 渲染公式失败 {filename}")
            return None

    def render_inline_text(self, text_content: str, filename: str) -> str:
        """
        渲染包含行内公式的文本

        Args:
            text_content: 文本内容
            filename: 输出文件名（不含扩展名）

        Returns:
            生成的PNG文件路径
        """
        output_path = self.output_dir / f"{filename}.png"
        
        # 使用子进程渲染
        result = self._render_with_subprocess(text_content, str(output_path), 'text')
        if result:
            # 进行白边裁剪
            self.trim_image_whitespace(str(output_path))
            self.stats['success'] += 1
            print(f"✓ 渲染文本成功: {output_path}")
            return result
        else:
            self.stats['errors'] += 1
            print(f"✗ 渲染文本失败 {filename}")
            return None

    def process_json_file(self, json_file_path: str) -> Dict[str, List[Dict[str, str]]]:
        """
        处理JSON文件，渲染所有公式和文本

        Args:
            json_file_path: JSON文件路径

        Returns:
            包含渲染结果的字典，每个结果包含content和对应的PNG文件路径
        """
        print(f"开始处理文件: {json_file_path}")

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results = {
            'display_formulas': [],
            'inline_texts': [],
            'errors': []
        }

        # 获取文件基名用于命名
        base_name = Path(json_file_path).stem

        # 处理所有文档
        if isinstance(data, list) and len(data) > 0:
            for doc_idx, document in enumerate(data):
                print(f"处理文档 {doc_idx + 1}/{len(data)}")

                # 处理display_formulas
                display_formulas = document.get('display_formulas', [])
                for i, formula in enumerate(display_formulas):
                    content = formula.get('content', '')
                    filename = f"{base_name}_doc{doc_idx+1:03d}_formula_{i+1:03d}"

                    result = self.render_display_formula(content, filename)
                    if result:
                        # 返回包含content和PNG文件路径的字典
                        results['display_formulas'].append({
                            "content": content,
                            "image": result,
                            "document_index": doc_idx + 1
                        })
                    else:
                        # render_display_formula内部已经增加了错误计数，这里不需要重复增加
                        results['errors'].append({
                            "error_message": f"文档{doc_idx+1} 公式 {i+1} 渲染失败",
                            "error_type": "FormulaRenderingError",
                            "content_preview": content,
                            "item_index": i+1,
                            "item_type": "display_formula",
                            "document_index": doc_idx + 1
                        })

                # 处理inline_texts
                inline_texts = document.get('inline_texts', [])
                for i, text_item in enumerate(inline_texts):
                    content = text_item.get('content', '')
                    filename = f"{base_name}_doc{doc_idx+1:03d}_text_{i+1:03d}"

                    try:
                        result = self.render_inline_text(content, filename)
                        if result:
                            # 返回包含content和PNG文件路径的字典
                            results['inline_texts'].append({
                                "content": content,
                                "image": result,
                                "document_index": doc_idx + 1
                            })
                        else:
                            # render_inline_text内部已经增加了错误计数，这里不需要重复增加
                            results['errors'].append({
                                "error_message": f"文档{doc_idx+1} 文本 {i+1} 渲染失败",
                                "error_type": "TextRenderingError",
                                "content_preview": content,
                                "item_index": i+1,
                                "item_type": "inline_text",
                                "document_index": doc_idx + 1
                            })
                    except ValueError as ve:
                        # 特殊情况：纯newcommand或空文本，记录为跳过而非错误
                        print(f"⚠ 跳过文档{doc_idx+1} 文本 {i+1}: {ve}")
                        self.stats['errors'] += 1  # 跳过的内容也计入失败统计
                        results['errors'].append({
                            "error_message": f"文档{doc_idx+1} 文本 {i+1} 跳过: {str(ve)}",
                            "error_type": "ContentSkipped",
                            "content_preview": content,
                            "item_index": i+1,
                            "item_type": "inline_text",
                            "document_index": doc_idx + 1,
                            "skip_reason": "pure_newcommand_or_empty"
                        })
                    except Exception as e:
                        # 其他真正的错误
                        print(f"✗ 文档{doc_idx+1} 文本 {i+1} 渲染失败: {e}")
                        self.stats['errors'] += 1  # 其他错误也计入失败统计
                        latex_error_type = self._categorize_latex_error(str(e))
                        results['errors'].append({
                            "error_message": f"文档{doc_idx+1} 文本 {i+1} 渲染失败: {str(e)}",
                            "error_type": latex_error_type,
                            "python_error_type": type(e).__name__,
                            "content_preview": content,
                            "item_index": i+1,
                            "item_type": "inline_text",
                            "document_index": doc_idx + 1
                        })

        return results

    def _is_pure_newcommand(self, text: str) -> bool:
        """
        检查文本是否只包含newcommand定义（无法直接渲染的内容）
        """
        # 移除空白字符后检查
        clean_text = text.strip()

        # 检查是否以\newcommand开始
        if not clean_text.startswith('\\newcommand'):
            return False

        # 移除所有newcommand定义，看看是否还有其他内容
        # 这个正则表达式需要匹配嵌套的大括号
        remaining_text = clean_text
        while True:
            # 找到\newcommand{...}[...]{...}模式
            newcommand_match = re.search(
                r'\\newcommand\{[^}]+\}(?:\[[0-9]+\])?\{', remaining_text)
            if not newcommand_match:
                break

            # 找到匹配的结束大括号
            start_pos = newcommand_match.end() - 1  # 指向开始的{
            brace_count = 1
            pos = start_pos + 1

            while pos < len(remaining_text) and brace_count > 0:
                if remaining_text[pos] == '{':
                    brace_count += 1
                elif remaining_text[pos] == '}':
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                # 找到了完整的newcommand定义，移除它
                remaining_text = remaining_text[:newcommand_match.start(
                )] + remaining_text[pos:]
            else:
                # 没有找到匹配的结束括号，可能格式有问题
                break

        # 如果移除所有newcommand后没有剩余内容，则认为是纯newcommand
        return not remaining_text.strip()

    def print_stats(self):
        """打印渲染统计信息"""
        total = self.stats['success'] + self.stats['errors']
        if total == 0:
            return

        print(f"\n{'='*50}")
        print("渲染统计信息")
        print(f"{'='*50}")
        print(
            f"成功: {self.stats['success']} ({self.stats['success']/total*100:.1f}%)")
        print(
            f"失败: {self.stats['errors']} ({self.stats['errors']/total*100:.1f}%)")


def main():
    """主函数 - 使用子进程的usetex渲染器"""
    print("LaTeX渲染器 - 使用子进程避免内存积累")
    print("注意: 需要安装LaTeX (texlive-latex-base + texlive-latex-recommended)")

    # 检查命令行参数
    if len(sys.argv) != 2:
        print("用法: python latex_to_png_renderer.py <json_file_path>")
        print("示例: python latex_to_png_renderer.py arxiv_extracted_json/240100017_extracted.json")
        sys.exit(1)

    json_file = sys.argv[1]

    # 检查文件是否存在
    if not os.path.exists(json_file):
        print(f"错误: 文件不存在: {json_file}")
        sys.exit(1)

    matplotlib.use('Agg')
    renderer = LaTeXRenderer(output_dir="rendered_images", dpi=300)
    
    print("✓ 使用子进程渲染模式（避免内存积累）")

    # 处理指定的文件
    results = renderer.process_json_file(json_file)

    print(f"\n=== 处理结果 ===")
    print(f"成功渲染公式: {len(results['display_formulas'])} 个")
    print(f"成功渲染文本: {len(results['inline_texts'])} 个")
    if results['errors']:
        print(f"错误: {len(results['errors'])} 个")
        for error in results['errors'][:5]:  # 只显示前5个错误
            print(f"  - {error}")

    # 显示详细统计信息
    renderer.print_stats()


if __name__ == "__main__":
    main()
