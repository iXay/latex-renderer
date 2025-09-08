#!/usr/bin/env python3
"""
LaTeX to PNG Renderer
渲染JSON文件中的LaTeX公式和文本为PNG图片

支持：
- display_formulas: 独立的数学公式（$$...$$ 和 \\[...\\]）
- inline_texts: 包含行内公式的文本段落（$...$ 和 \\(...\\)）
"""

import json
import re
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import mathtext
import numpy as np
from PIL import Image, ImageOps

# 导入共用的LaTeX处理工具
from latex_utils import (
    LATEX_PREAMBLE,
    categorize_latex_error
)

# 设置matplotlib使用完整LaTeX
matplotlib.rcParams['text.usetex'] = True  # 使用完整LaTeX渲染
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.size'] = 12

# 配置LaTeX包
matplotlib.rcParams['text.latex.preamble'] = LATEX_PREAMBLE


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

    # preprocess_latex函数已移动到 latex_utils.py 模块中

    # calculate_figure_width函数已移动到 latex_utils.py 模块中

    # create_latex_parbox函数已移动到 latex_utils.py 模块中

    # preprocess_text_commands函数已移动到 latex_utils.py 模块中

    # _categorize_latex_error函数已移动到 latex_utils.py 模块中

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

    def process_json_file(self, json_file_path: str, render_type: str = "both") -> Dict[str, List[Dict[str, str]]]:
        """
        处理JSON文件，渲染所有公式和文本

        Args:
            json_file_path: JSON文件路径
            render_type: 渲染类型，可选值: "formula"(只渲染公式), "text"(只渲染文本), "both"(都渲染)

        Returns:
            包含渲染结果的字典，每个结果包含content和对应的PNG文件路径
        """
        print(f"开始处理文件: {json_file_path} (渲染类型: {render_type})")

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

                # 处理display_formulas (只在render_type为"formula"或"both"时处理)
                if render_type in ["formula", "both"]:
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

                # 处理inline_texts (只在render_type为"text"或"both"时处理)
                if render_type in ["text", "both"]:
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
                            latex_error_type = categorize_latex_error(str(e))
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

    # _is_pure_newcommand函数已移动到 latex_utils.py 模块中

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
