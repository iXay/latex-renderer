#!/usr/bin/env python3
"""
子进程渲染器 - 用于在独立进程中渲染单个LaTeX公式或文本
避免内存积累问题
"""

import sys
import json
import os
import random
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # 必须在导入pyplot之前设置
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# 设置matplotlib使用完整LaTeX
matplotlib.rcParams['text.usetex'] = True
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


def preprocess_latex(latex_content: str, is_display: bool = True) -> str:
    """预处理LaTeX内容，优化为usetex兼容格式"""
    import re
    
    # 移除前后的$$符号
    content = latex_content.strip()
    if content.startswith('$$') and content.endswith('$$'):
        content = content[2:-2].strip()
    elif content.startswith('$') and content.endswith('$'):
        content = content[1:-1].strip()

    # 修复下标问题：将转义的下划线 \\_ 改为正常下标 _
    content = content.replace('\\_', '_')

    # 处理需要完整数学环境的内容
    if is_display:
        if '\\begin{aligned}' in content:
            content = f'$${content}$$'
        elif '\\begin{pmatrix}' in content or '\\begin{bmatrix}' in content:
            content = f'$${content}$$'
        else:
            content = f'${content}$'

    # 处理转义字符
    content = content.replace('\\&', '\\text{\\&}')

    # 处理text环境中的特殊字符
    content = re.sub(r'\\text\{([^}]*)\}',
                     lambda m: f'\\text{{{m.group(1).replace("&", "\\&")}}}',
                     content)

    return content


def preprocess_text_commands(text: str) -> str:
    """在换行之前预处理LaTeX命令，避免命令被换行截断"""
    import re
    
    processed_text = text

    # 处理百分号注释
    processed_text = re.sub(r'(?<!\\)%.*$', '', processed_text, flags=re.MULTILINE)

    # 处理引用命令
    processed_text = re.sub(r'\\citep\{([^}]+)\}', r'[\1]', processed_text)
    processed_text = re.sub(r'\\cite\{([^}]+)\}', r'(\1)', processed_text)
    processed_text = re.sub(r'\\citet\{([^}]+)\}', r'\1', processed_text)

    # 处理subsection和section命令
    processed_text = re.sub(r'\\subsection\{([^}]+)\}', r'\1', processed_text)
    processed_text = re.sub(r'\\section\{([^}]+)\}', r'\1', processed_text)

    # 移除newcommand定义
    processed_text = re.sub(r'\\newcommand\{[^}]+\}(?:\[[0-9]+\])?\{[^}]*\}', '', processed_text)

    # 处理其他常见的LaTeX命令
    processed_text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', processed_text)
    processed_text = re.sub(r'\\textit\{([^}]+)\}', r'\1', processed_text)
    processed_text = re.sub(r'\\emph\{([^}]+)\}', r'\1', processed_text)

    # 处理caption命令
    processed_text = re.sub(r'\\caption\{([^}]+)\}', r'Caption: \1', processed_text)
    processed_text = re.sub(r'\\caption\{(.*)$', r'Caption: \1', processed_text)

    # 修复多余的大括号
    processed_text = re.sub(r'\s*\}\s*$', '', processed_text)
    processed_text = re.sub(r'\$([^$]+)\$\s*\}', r'$\1$', processed_text)

    # 处理双反斜杠换行符
    processed_text = processed_text.replace('\\\\', ' ')

    return processed_text.strip()


def create_latex_parbox(text: str, target_width_inches: float) -> str:
    """使用LaTeX parbox控制文本宽度，让LaTeX处理换行"""
    horizontal_padding = 0.5
    content_width_pt = (target_width_inches - 2 * horizontal_padding) * 72.27
    latex_text = f"\\parbox{{{content_width_pt:.2f}pt}}{{{text}}}"
    return latex_text


def calculate_figure_width(text_content: str, is_display: bool = False) -> float:
    """根据文本内容计算合适的图片宽度"""
    a4_width_inches = 8.27
    
    if is_display:
        min_width = 0.4 * a4_width_inches
        max_width = 1.0 * a4_width_inches
        return random.uniform(min_width, max_width)
    
    min_width = 0.4 * a4_width_inches
    max_width = 1.0 * a4_width_inches
    return random.uniform(min_width, max_width)


def is_pure_newcommand(text: str) -> bool:
    """检查文本是否只包含newcommand定义"""
    import re
    
    clean_text = text.strip()
    
    if not clean_text.startswith('\\newcommand'):
        return False
    
    remaining_text = clean_text
    while True:
        newcommand_match = re.search(r'\\newcommand\{[^}]+\}(?:\[[0-9]+\])?\{', remaining_text)
        if not newcommand_match:
            break
        
        start_pos = newcommand_match.end() - 1
        brace_count = 1
        pos = start_pos + 1
        
        while pos < len(remaining_text) and brace_count > 0:
            if remaining_text[pos] == '{':
                brace_count += 1
            elif remaining_text[pos] == '}':
                brace_count -= 1
            pos += 1
        
        if brace_count == 0:
            remaining_text = remaining_text[:newcommand_match.start()] + remaining_text[pos:]
        else:
            break
    
    return not remaining_text.strip()


def trim_image_whitespace(image_path: str, dpi: int = 300) -> str:
    """
    移除图片周围的白边
    
    Args:
        image_path: 图片路径
        dpi: 图片DPI
        
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
            cropped_img.save(image_path, 'PNG', dpi=(dpi, dpi))
        
        return image_path
        
    except Exception as e:
        # 如果裁剪失败，返回原路径
        return image_path


def render_display_formula(formula_content: str, output_path: str, dpi: int = 300) -> dict:
    """渲染独立的数学公式"""
    try:
        # 预处理LaTeX内容
        processed_content = preprocess_latex(formula_content, is_display=True)
        
        # 计算图片宽度
        figure_width = calculate_figure_width(formula_content, is_display=True)
        figure_height = max(figure_width * 0.3, 2.0)
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(figure_width, figure_height))
        ax.axis('off')
        
        # 使用usetex渲染数学公式，居中显示
        ax.text(0.5, 0.5, processed_content,
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transAxes,
                fontsize=16)
        
        # 保存图片
        horizontal_padding = 0.5
        plt.tight_layout()
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=horizontal_padding/2)
        plt.close(fig)
        
        # 进行白边裁剪
        trim_image_whitespace(output_path, dpi)
        
        return {
            'success': True,
            'output_path': output_path,
            'error': None
        }
        
    except Exception as e:
        if 'fig' in locals():
            plt.close(fig)
        return {
            'success': False,
            'output_path': None,
            'error': str(e)
        }


def render_inline_text(text_content: str, output_path: str, dpi: int = 300) -> dict:
    """渲染包含行内公式的文本"""
    try:
        # 检查是否是纯newcommand定义
        if is_pure_newcommand(text_content):
            raise ValueError(f"纯newcommand定义无法渲染: {text_content.strip()}")
        
        # 计算图片宽度
        figure_width = calculate_figure_width(text_content, is_display=False)
        
        # 预处理LaTeX命令
        preprocessed_text = preprocess_text_commands(text_content)
        
        # 使用LaTeX parbox让LaTeX处理换行
        latex_parbox_text = create_latex_parbox(preprocessed_text, figure_width)
        
        # 估算高度
        figure_height = max(figure_width * 0.4, 1.5)
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(figure_width, figure_height))
        ax.axis('off')
        
        # 如果文本为空，直接失败
        if not latex_parbox_text.strip():
            plt.close(fig)
            raise ValueError(f"处理后的文本为空，无法渲染: {text_content.strip()}")
        
        # 使用usetex渲染LaTeX parbox，居中显示
        ax.text(0.5, 0.5, latex_parbox_text,
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transAxes,
                fontsize=14)
        
        # 保存图片
        horizontal_padding = 0.5
        plt.tight_layout()
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=horizontal_padding/4)
        plt.close(fig)
        
        # 进行白边裁剪
        trim_image_whitespace(output_path, dpi)
        
        return {
            'success': True,
            'output_path': output_path,
            'error': None
        }
        
    except Exception as e:
        if 'fig' in locals():
            plt.close(fig)
        return {
            'success': False,
            'output_path': None,
            'error': str(e)
        }


def main():
    """主函数 - 从命令行参数获取渲染任务"""
    if len(sys.argv) < 4:
        print("用法: python subprocess_renderer.py <type> <content> <output_path> [dpi]")
        print("type: 'formula' 或 'text'")
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
        
        # 根据类型调用相应的渲染函数
        if render_type == 'formula':
            result = render_display_formula(content, output_path, dpi)
        elif render_type == 'text':
            result = render_inline_text(content, output_path, dpi)
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
