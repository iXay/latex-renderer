#!/usr/bin/env python3
"""
LaTeX处理工具模块 - 共用的LaTeX处理函数
避免在多个文件中重复代码
"""

import re
import random
import numpy as np
from PIL import Image


# LaTeX包配置 - 在多个文件中共用
LATEX_PREAMBLE = r'''
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
\usepackage{siunitx}
\usepackage{array}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{CJKutf8}
\AtBeginDocument{\begin{CJK}{UTF8}{gbsn}}
\AtEndDocument{\end{CJK}}
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
% \si command is provided by siunitx package, so we don't redefine it
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
% Add missing commands from the failing formulas
\newcommand{\sI}{\mathcal{I}}  % Indicator function
\newcommand{\sH}{\mathcal{H}}  % Hilbert space
\newcommand{\fL}{\mathcal{L}} % Linear operator
\newcommand{\calT}{\mathcal{T}} % Set T
\newcommand{\bE}{\mathbb{E}} % Expectation
\newcommand{\bmu}{\boldsymbol{\mu}} % Bold mu
\newcommand{\rmi}{\mathrm{i}} % Imaginary unit
% Use \providecommand to avoid conflicts with physics package
\providecommand{\dd}{\mathrm{d}} % Differential d
% Additional common mathematical symbols
\newcommand{\sK}{\mathcal{K}} % Another Hilbert space
\newcommand{\fM}{\mathcal{M}} % Mapping/operator
\newcommand{\rmm}{\mathrm{m}} % Small m
\newcommand{\calP}{\mathcal{P}} % Probability/Projection
\newcommand{\bbR}{\mathbb{R}} % Real numbers
\newcommand{\bbN}{\mathbb{N}} % Natural numbers
\newcommand{\bbZ}{\mathbb{Z}} % Integers
\newcommand{\bbC}{\mathbb{C}} % Complex numbers
\newcommand{\bbQ}{\mathbb{Q}} % Rational numbers
\newcommand{\sB}{\mathcal{B}} % Borel sigma-algebra
\newcommand{\sF}{\mathcal{F}} % Filtration
\newcommand{\sG}{\mathcal{G}} % Another sigma-algebra
\newcommand{\sA}{\mathcal{A}} % Algebra
\newcommand{\sC}{\mathcal{C}} % Another algebra
\newcommand{\sD}{\mathcal{D}} % Distribution
\newcommand{\sE}{\mathcal{E}} % Expectation operator
\newcommand{\sL}{\mathcal{L}} % Linear operator
\newcommand{\sM}{\mathcal{M}} % Measure
\newcommand{\sN}{\mathcal{N}} % Normal distribution
\newcommand{\sO}{\mathcal{O}} % Big O notation
\newcommand{\sP}{\mathcal{P}} % Probability
\newcommand{\sQ}{\mathcal{Q}} % Another operator
\newcommand{\sR}{\mathcal{R}} % Range
\newcommand{\sS}{\mathcal{S}} % Schwartz space
\newcommand{\sT}{\mathcal{T}} % Topology
\newcommand{\sU}{\mathcal{U}} % Uniform distribution
\newcommand{\sV}{\mathcal{V}} % Variance
\newcommand{\sW}{\mathcal{W}} % Wiener process
\newcommand{\sX}{\mathcal{X}} % Sample space
\newcommand{\sY}{\mathcal{Y}} % Another sample space
\newcommand{\sZ}{\mathcal{Z}} % Another space
'''

# 专门用于表格渲染的preamble（不包含CJK环境以避免冲突）
LATEX_TABLE_PREAMBLE = r'''
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{physics}
\usepackage{braket}
\usepackage{bm}
\usepackage{mathtools}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{natbib}
\usepackage{graphicx}
\usepackage{siunitx}
\usepackage{array}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{geometry}
\usepackage{adjustbox}
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
% \si command is provided by siunitx package, so we don't redefine it
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
% Add missing commands from the failing formulas
\newcommand{\sI}{\mathcal{I}}  % Indicator function
\newcommand{\sH}{\mathcal{H}}  % Hilbert space
\newcommand{\fL}{\mathcal{L}} % Linear operator
\newcommand{\calT}{\mathcal{T}} % Set T
\newcommand{\bE}{\mathbb{E}} % Expectation
\newcommand{\bmu}{\boldsymbol{\mu}} % Bold mu
\newcommand{\rmi}{\mathrm{i}} % Imaginary unit
% Use \providecommand to avoid conflicts with physics package
\providecommand{\dd}{\mathrm{d}} % Differential d
% Additional common mathematical symbols
\newcommand{\sK}{\mathcal{K}} % Another Hilbert space
\newcommand{\fM}{\mathcal{M}} % Mapping/operator
\newcommand{\rmm}{\mathrm{m}} % Small m
\newcommand{\calP}{\mathcal{P}} % Probability/Projection
\newcommand{\bbR}{\mathbb{R}} % Real numbers
\newcommand{\bbN}{\mathbb{N}} % Natural numbers
\newcommand{\bbZ}{\mathbb{Z}} % Integers
\newcommand{\bbC}{\mathbb{C}} % Complex numbers
\newcommand{\bbQ}{\mathbb{Q}} % Rational numbers
\newcommand{\sB}{\mathcal{B}} % Borel sigma-algebra
\newcommand{\sF}{\mathcal{F}} % Filtration
\newcommand{\sG}{\mathcal{G}} % Another sigma-algebra
\newcommand{\sA}{\mathcal{A}} % Algebra
\newcommand{\sC}{\mathcal{C}} % Another algebra
\newcommand{\sD}{\mathcal{D}} % Distribution
\newcommand{\sE}{\mathcal{E}} % Expectation operator
\newcommand{\sL}{\mathcal{L}} % Linear operator
\newcommand{\sM}{\mathcal{M}} % Measure
\newcommand{\sN}{\mathcal{N}} % Normal distribution
\newcommand{\sO}{\mathcal{O}} % Big O notation
\newcommand{\sP}{\mathcal{P}} % Probability
\newcommand{\sQ}{\mathcal{Q}} % Another operator
\newcommand{\sR}{\mathcal{R}} % Range
\newcommand{\sS}{\mathcal{S}} % Schwartz space
\newcommand{\sT}{\mathcal{T}} % Topology
\newcommand{\sU}{\mathcal{U}} % Uniform distribution
\newcommand{\sV}{\mathcal{V}} % Variance
\newcommand{\sW}{\mathcal{W}} % Wiener process
\newcommand{\sX}{\mathcal{X}} % Sample space
\newcommand{\sY}{\mathcal{Y}} % Another sample space
\newcommand{\sZ}{\mathcal{Z}} % Another space
'''


def preprocess_chinese_text(content: str) -> str:
    """预处理中文字符，确保LaTeX兼容性"""
    # 将裸露的中文字符包装在\text{}中
    # 匹配中文字符（包括中文标点符号）
    chinese_pattern = r'([一-龯]+[）】}）]*)'
    content = re.sub(chinese_pattern, r'\\text{\1}', content)
    
    # 处理中文标点符号
    content = content.replace('）', ')')
    content = content.replace('（', '(')
    content = content.replace('【', '[')
    content = content.replace('】', ']')
    content = content.replace('，', ',')
    content = content.replace('。', '.')
    content = content.replace('；', ';')
    content = content.replace('：', ':')
    
    # 处理已经在\text{}中的中文，避免重复包装
    content = re.sub(r'\\text\{\\text\{([^}]+)\}\}', r'\\text{\1}', content)
    
    return content


def preprocess_latex(latex_content: str, is_display: bool = True) -> str:
    """预处理LaTeX内容，优化为usetex兼容格式
    
    支持以下LaTeX语法：
    - Display formulas: $$...$$ 和 \\[...\\]
    - Inline formulas: $...$ 和 \\(...\\)
    """
    # 移除前后的数学环境符号
    content = latex_content.strip()
    
    # 处理display math环境符号
    if content.startswith('\\[') and content.endswith('\\]'):
        content = content[2:-2].strip()
        is_display = True
    elif content.startswith('$$') and content.endswith('$$'):
        content = content[2:-2].strip()
        is_display = True
    # 处理inline math环境符号  
    elif content.startswith('\\(') and content.endswith('\\)'):
        content = content[2:-2].strip()
        is_display = False
    elif content.startswith('$') and content.endswith('$'):
        content = content[1:-1].strip()
        is_display = False

    # 修复下标问题：将转义的下划线 \\_ 改为正常下标 _
    content = content.replace('\\_', '_')

    # 预处理中文字符
    content = preprocess_chinese_text(content)

    # 处理需要完整数学环境的内容
    if is_display:
        if '\\begin{aligned}' in content:
            content = f'$${content}$$'
        elif '\\begin{pmatrix}' in content or '\\begin{bmatrix}' in content:
            content = f'$${content}$$'
        else:
            content = f'${content}$'
    else:
        # 对于inline math，确保包装在单个$中
        if not (content.startswith('$') and content.endswith('$')):
            content = f'${content}$'

    # 处理转义字符
    content = content.replace('\\&', '\\text{\\&}')

    # 处理text环境中的特殊字符
    content = re.sub(r'\\text\{([^}]*)\}',
                     lambda m: f'\\text{{{m.group(1).replace("&", "\\&")}}}',
                     content)

    return content


def preprocess_text_commands(text: str) -> str:
    """极简文本预处理 - 让pdflatex处理所有LaTeX命令，只做最基本的清理"""
    processed_text = text.strip()
    
    # 只处理会导致LaTeX编译失败的基本问题，其他都让pdflatex处理
    
    # 1. 移除百分号注释（避免LaTeX解析问题）
    processed_text = re.sub(r'(?<!\\)%.*$', '', processed_text, flags=re.MULTILINE)
    
    # 2. 处理双反斜杠换行符（避免LaTeX换行问题）
    processed_text = processed_text.replace('\\\\', ' ')
    
    return processed_text.strip()


def preprocess_table_content(table_content: str) -> str:
    """预处理LaTeX表格内容 - 最小干预版本"""
    processed_table = table_content.strip()
    
    # 只处理siunitx的S列类型，替换为普通列（如果存在的话）
    processed_table = re.sub(r'S\[table-format=[^\]]+\]', 'c', processed_table)
    
    # 对于没有环境包装的纯表格内容，才需要添加tabular环境
    if not processed_table.startswith('\\begin{'):
        lines = processed_table.split('\n')
        if lines and '&' in lines[0]:
            # 根据第一行检测列数
            first_line = lines[0]
            col_count = first_line.count('&') + 1
            # 默认使用居中对齐
            col_format = 'c' * col_count
            processed_table = f'\\begin{{tabular}}{{{col_format}}}\n{processed_table}\\end{{tabular}}'
        else:
            processed_table = f'\\begin{{tabular}}{{c}}\n{processed_table}\\end{{tabular}}'
    
    return processed_table


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


def categorize_latex_error(error_message: str) -> str:
    """根据错误消息对LaTeX错误进行分类"""
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
