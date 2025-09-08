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

# 导入共用的LaTeX处理工具
from latex_utils import (
    LATEX_PREAMBLE,
    preprocess_latex,
    preprocess_text_commands,
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
