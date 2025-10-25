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

    def trim_image_whitespace(self, image_path: str) -> bool:
        """
        移除图片周围的白边
        
        Args:
            image_path: 图片路径
            
        Returns:
            True表示成功处理，False表示检测到空白图片
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
                return True
            else:
                # 检测到空白图片，删除文件
                if os.path.exists(image_path):
                    os.remove(image_path)
                print(f"✗ 检测到空白图片已删除: {image_path}")
                return False

        except Exception as e:
            print(f"  ⚠ 白边移除失败 {image_path}: {e}")
            return True  # 处理失败时保持原有行为

    # preprocess_latex函数已移动到 latex_utils.py 模块中

    # calculate_figure_width函数已移动到 latex_utils.py 模块中

    # create_latex_parbox函数已移动到 latex_utils.py 模块中

    # preprocess_text_commands函数已移动到 latex_utils.py 模块中

    # _categorize_latex_error函数已移动到 latex_utils.py 模块中

    def render_display_formula(self, formula_content: str, filename: str) -> Tuple[str, str]:
        """
        渲染独立的数学公式

        Args:
            formula_content: 公式内容
            filename: 输出文件名（不含扩展名）

        Returns:
            元组: (生成的PNG文件路径, 错误类型), 成功时错误类型为None
        """
        output_path = self.output_dir / f"{filename}.png"
        
        # 使用子进程渲染
        result = self._render_with_subprocess(formula_content, str(output_path), 'formula')
        if result:
            # 进行白边裁剪并检查是否为空白图片
            is_valid = self.trim_image_whitespace(str(output_path))
            if is_valid:
                self.stats['success'] += 1
                print(f"✓ 渲染公式成功: {output_path}")
                return result, None
            else:
                # 空白图片，视为渲染失败
                self.stats['errors'] += 1
                print(f"✗ 渲染公式失败 {filename} (空白图片)")
                return None, "BlankImageError"
        else:
            self.stats['errors'] += 1
            print(f"✗ 渲染公式失败 {filename}")
            return None, "FormulaRenderingError"

    def render_inline_text(self, text_content: str, filename: str) -> Tuple[str, str]:
        """
        渲染包含行内公式的文本

        Args:
            text_content: 文本内容
            filename: 输出文件名（不含扩展名）

        Returns:
            元组: (生成的PNG文件路径, 错误类型), 成功时错误类型为None
        """
        output_path = self.output_dir / f"{filename}.png"
        
        # 使用子进程渲染
        result = self._render_with_subprocess(text_content, str(output_path), 'text')
        if result:
            # 进行白边裁剪并检查是否为空白图片
            is_valid = self.trim_image_whitespace(str(output_path))
            if is_valid:
                self.stats['success'] += 1
                print(f"✓ 渲染文本成功: {output_path}")
                return result, None
            else:
                # 空白图片，视为渲染失败
                self.stats['errors'] += 1
                print(f"✗ 渲染文本失败 {filename} (空白图片)")
                return None, "BlankImageError"
        else:
            self.stats['errors'] += 1
            print(f"✗ 渲染文本失败 {filename}")
            return None, "TextRenderingError"

    def render_table(self, table_content: str, filename: str) -> Tuple[str, str]:
        """
        渲染LaTeX表格

        Args:
            table_content: 表格内容
            filename: 输出文件名（不含扩展名）

        Returns:
            元组: (生成的PNG文件路径, 错误类型), 成功时错误类型为None
        """
        output_path = self.output_dir / f"{filename}.png"
        
        # 使用子进程渲染
        result = self._render_with_subprocess(table_content, str(output_path), 'table')
        if result:
            # 进行白边裁剪并检查是否为空白图片
            is_valid = self.trim_image_whitespace(str(output_path))
            if is_valid:
                self.stats['success'] += 1
                print(f"✓ 渲染表格成功: {output_path}")
                return result, None
            else:
                # 空白图片，视为渲染失败
                self.stats['errors'] += 1
                print(f"✗ 渲染表格失败 {filename} (空白图片)")
                return None, "BlankImageError"
        else:
            self.stats['errors'] += 1
            print(f"✗ 渲染表格失败 {filename}")
            return None, "TableRenderingError"

    def process_json_file(self, json_file_path: str, render_type: str = "all") -> Dict[str, List[Dict[str, str]]]:
        """
        处理JSON文件，渲染所有公式、文本和表格

        Args:
            json_file_path: JSON文件路径
            render_type: 渲染类型，可选值: "formula"(只渲染公式), "text"(只渲染文本), "table"(只渲染表格), "all"(全部渲染)

        Returns:
            包含渲染结果的字典，每个结果包含content和对应的PNG文件路径
        """
        print(f"开始处理文件: {json_file_path} (渲染类型: {render_type})")

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results = {
            'display_formulas': [],
            'inline_texts': [],
            'tables': [],
            'errors': []
        }

        # 获取文件基名用于命名
        base_name = Path(json_file_path).stem

        # 处理所有文档
        if isinstance(data, list) and len(data) > 0:
            for doc_idx, document in enumerate(data):
                print(f"处理文档 {doc_idx + 1}/{len(data)}")

                # 处理display_formulas (只在render_type为"formula"或"all"时处理)
                if render_type in ["formula", "all"]:
                    display_formulas = document.get('display_formulas', [])
                    for i, formula in enumerate(display_formulas):
                        content = formula.get('content', '')
                        filename = f"{base_name}_doc{doc_idx+1:03d}_formula_{i+1:03d}"

                        result, error_type = self.render_display_formula(content, filename)
                        if result:
                            # 返回包含content和PNG文件路径的字典
                            results['display_formulas'].append({
                                "content": content,
                                "image": result,
                                "document_index": doc_idx + 1
                            })
                        else:
                            # render_display_formula内部已经增加了错误计数，这里不需要重复增加
                            # 根据错误类型设置不同的错误消息
                            if error_type == "BlankImageError":
                                error_message = f"文档{doc_idx+1} 公式 {i+1} 渲染失败 (空白图片)"
                            else:
                                error_message = f"文档{doc_idx+1} 公式 {i+1} 渲染失败"
                            
                            results['errors'].append({
                                "error_message": error_message,
                                "error_type": error_type or "FormulaRenderingError",
                                "content_preview": content,
                                "item_index": i+1,
                                "item_type": "display_formula",
                                "document_index": doc_idx + 1
                            })

                # 处理inline_texts (只在render_type为"text"或"all"时处理)
                if render_type in ["text", "all"]:
                    inline_texts = document.get('inline_texts', [])
                    for i, text_item in enumerate(inline_texts):
                        content = text_item.get('content', '')
                        filename = f"{base_name}_doc{doc_idx+1:03d}_text_{i+1:03d}"

                        try:
                            result, error_type = self.render_inline_text(content, filename)
                            if result:
                                # 返回包含content和PNG文件路径的字典
                                results['inline_texts'].append({
                                    "content": content,
                                    "image": result,
                                    "document_index": doc_idx + 1
                                })
                            else:
                                # render_inline_text内部已经增加了错误计数，这里不需要重复增加
                                # 根据错误类型设置不同的错误消息
                                if error_type == "BlankImageError":
                                    error_message = f"文档{doc_idx+1} 文本 {i+1} 渲染失败 (空白图片)"
                                else:
                                    error_message = f"文档{doc_idx+1} 文本 {i+1} 渲染失败"
                                
                                results['errors'].append({
                                    "error_message": error_message,
                                    "error_type": error_type or "TextRenderingError",
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

                # 处理tables (只在render_type为"table"或"all"时处理)
                if render_type in ["table", "all"]:
                    tables = document.get('tables', [])
                    for i, table in enumerate(tables):
                        content = table.get('content', '')
                        filename = f"{base_name}_doc{doc_idx+1:03d}_table_{i+1:03d}"

                        try:
                            result, error_type = self.render_table(content, filename)
                            if result:
                                # 返回包含content和PNG文件路径的字典
                                results['tables'].append({
                                    "content": content,
                                    "image": result,
                                    "document_index": doc_idx + 1
                                })
                            else:
                                # render_table内部已经增加了错误计数，这里不需要重复增加
                                # 根据错误类型设置不同的错误消息
                                if error_type == "BlankImageError":
                                    error_message = f"文档{doc_idx+1} 表格 {i+1} 渲染失败 (空白图片)"
                                else:
                                    error_message = f"文档{doc_idx+1} 表格 {i+1} 渲染失败"
                                
                                results['errors'].append({
                                    "error_message": error_message,
                                    "error_type": error_type or "TableRenderingError",
                                    "content_preview": content,
                                    "item_index": i+1,
                                    "item_type": "table",
                                    "document_index": doc_idx + 1
                                })
                        except Exception as e:
                            # 表格渲染错误
                            print(f"✗ 文档{doc_idx+1} 表格 {i+1} 渲染失败: {e}")
                            self.stats['errors'] += 1
                            latex_error_type = categorize_latex_error(str(e))
                            results['errors'].append({
                                "error_message": f"文档{doc_idx+1} 表格 {i+1} 渲染失败: {str(e)}",
                                "error_type": latex_error_type,
                                "python_error_type": type(e).__name__,
                                "content_preview": content,
                                "item_index": i+1,
                                "item_type": "table",
                                "document_index": doc_idx + 1
                            })

        return results

    # _is_pure_newcommand函数已移动到 latex_utils.py 模块中

    def trim_image_whitespace(self, image_path: str) -> bool:
        """
        移除图片周围的白边并检查是否为空白图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            bool: True如果图片有效（非空白），False如果图片为空白
        """
        try:
            # 导入trim_image_whitespace函数
            from latex_utils import trim_image_whitespace
            
            # 调用trim_image_whitespace函数
            trim_image_whitespace(image_path, self.dpi)
            
            # 检查图片是否为空白
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # 定义白色阈值
            white_threshold = 250
            
            # 检测非白色像素
            if len(img_array.shape) == 3:  # RGB
                non_white_mask = np.any(img_array < white_threshold, axis=2)
            else:  # Grayscale
                non_white_mask = img_array < white_threshold
            
            non_white_count = np.sum(non_white_mask)
            
            # 如果非白色像素太少，认为是空白图片
            if non_white_count < 100:  # 阈值可以根据需要调整
                # 删除空白图片
                os.remove(image_path)
                print(f"✗ 检测到空白图片已删除: {image_path}")
                return False
            else:
                return True
                
        except Exception as e:
            print(f"处理图片时出错: {e}")
            return False

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
    import argparse
    
    parser = argparse.ArgumentParser(description="LaTeX渲染器 - 使用子进程避免内存积累")
    parser.add_argument("json_file", help="JSON文件路径")
    parser.add_argument("-r", "--render-type", choices=["formula", "text", "table", "all"], default="all",
                       help="渲染类型: formula(只渲染公式), text(只渲染文本), table(只渲染表格), all(全部渲染) (默认: all)")
    parser.add_argument("-o", "--output", default="rendered_images", 
                       help="输出目录 (默认: rendered_images)")
    parser.add_argument("-d", "--dpi", type=int, default=300,
                       help="图片分辨率 (默认: 300)")
    
    args = parser.parse_args()
    
    print("LaTeX渲染器 - 使用子进程避免内存积累")
    print(f"渲染类型: {args.render_type}")

    # 检查文件是否存在
    if not os.path.exists(args.json_file):
        print(f"错误: 文件不存在: {args.json_file}")
        sys.exit(1)

    matplotlib.use('Agg')
    renderer = LaTeXRenderer(output_dir=args.output, dpi=args.dpi)
    
    print("✓ 使用子进程渲染模式（避免内存积累）")

    # 处理指定的文件
    results = renderer.process_json_file(args.json_file, render_type=args.render_type)

    print(f"\n=== 处理结果 ===")
    print(f"成功渲染公式: {len(results['display_formulas'])} 个")
    print(f"成功渲染文本: {len(results['inline_texts'])} 个")
    print(f"成功渲染表格: {len(results['tables'])} 个")
    if results['errors']:
        print(f"错误: {len(results['errors'])} 个")
        for error in results['errors'][:5]:  # 只显示前5个错误
            print(f"  - {error}")

    # 显示详细统计信息
    renderer.print_stats()


if __name__ == "__main__":
    main()
