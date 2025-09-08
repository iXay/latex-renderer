#!/usr/bin/env python3
"""
批量处理多个JSON文件的LaTeX渲染脚本 - 分布式缓存版本
"""

import os
import multiprocessing
import time
import logging
import traceback
import sys
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
from latex_to_png_renderer import LaTeXRenderer
from distributed_cache import DistributedCacheManager

def setup_logging(log_file: str = None, log_level: str = "INFO"):
    """设置日志配置，同时输出到控制台和文件"""
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"batch_renderer_{timestamp}.log"
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除已有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return log_file

def process_single_file_worker(args):
    """多进程工作函数，使用分布式缓存（无锁，高性能）"""
    json_file, output_dir, dpi, cache_dir, render_type = args
    
    # 获取进程ID用于调试
    process_id = os.getpid()
    
    # 设置进程级别的日志记录器
    logger = logging.getLogger(f"worker_{process_id}")
    
    try:
        # 设置matplotlib为非交互式后端（进程安全）
        import matplotlib
        import matplotlib.pyplot as plt
        matplotlib.use('Agg')
        
        # 确保每个进程有独立的随机种子（影响图片宽度计算）
        import random
        random.seed(os.getpid() + int(time.time()))
        
        # 创建独立的渲染器实例
        renderer = LaTeXRenderer(output_dir=output_dir, dpi=dpi)
        results = renderer.process_json_file(json_file, render_type=render_type)
        
        formulas_count = len(results['display_formulas'])
        texts_count = len(results['inline_texts'])
        errors_count = len(results['errors'])
        
        # 准备缓存数据
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "process_id": process_id,
            "output_files": {
                "formulas": results['display_formulas'],  # 现在每个元素是 {"content": "...", "image": "..."}
                "texts": results['inline_texts']          # 现在每个元素是 {"content": "...", "image": "..."}
            },
            "stats": {
                "formulas_count": formulas_count,
                "texts_count": texts_count,
                "errors_count": errors_count
            },
            "errors": results['errors'] if errors_count > 0 else []
        }
        
        # 使用分布式缓存（无锁，直接写入独立文件）
        cache_manager = DistributedCacheManager(cache_dir)
        cache_manager.save_file_cache(json_file, cache_entry)

        return json_file, True, {
            "formulas_count": formulas_count,
            "texts_count": texts_count,
            "errors_count": errors_count
        }
        
    except Exception as e:
        # 获取详细的异常信息
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        # 记录详细的异常信息到日志
        logger.error(f"进程 {process_id} 处理文件 {json_file} 时发生异常:")
        logger.error(f"  异常类型: {error_type}")
        logger.error(f"  异常信息: {error_message}")
        logger.error(f"  异常堆栈:\n{error_traceback}")
        
        # 错误情况的缓存条目
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "process_id": process_id,
            "error": error_message,
            "error_type": error_type,
            "error_traceback": error_traceback,
            "file_path": json_file,
            "status": "failed"
        }
        
        # 尝试更新缓存（即使发生错误）
        try:
            cache_manager = DistributedCacheManager(cache_dir)
            cache_manager.save_file_cache(json_file, cache_entry)
        except Exception as cache_error:
            logger.error(f"进程 {process_id} 无法更新错误缓存: {cache_error}")
        
        return json_file, False, {
            "formulas_count": 0,
            "texts_count": 0,
            "errors_count": 1,
            "error_type": error_type,
            "error_message": error_message
        }
    
    finally:
        # 强制清理matplotlib资源
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except Exception as cleanup_error:
            logger.warning(f"进程 {process_id} 清理matplotlib资源时发生异常: {cleanup_error}")




def batch_process_from_list(file_list_path: str, output_dir: str = "rendered_images", max_files: int = None, cache_dir: str = None, resume: bool = False, max_workers: int = 4, task_timeout: int = 3600 * 24, log_file: str = None, render_type: str = "both"):
    """从描述文件中读取JSON文件路径列表并批量处理 - 分布式缓存版本"""
    # 设置日志
    log_file_path = setup_logging(log_file)
    logger = logging.getLogger()
    
    logger.info("LaTeX渲染器 - 分布式缓存版本")
    logger.info("注意: 需要安装LaTeX环境")
    logger.info(f"并发工作进程数: {max_workers}")
    logger.info(f"渲染类型: {render_type}")
    logger.info(f"日志文件: {log_file_path}")
    
    # 设置默认缓存目录
    if cache_dir is None:
        cache_dir = f"{output_dir}_cache"
    
    # 创建分布式缓存管理器
    cache_manager = DistributedCacheManager(cache_dir)
    logger.info(f"使用分布式缓存目录: {cache_dir}")
    
    # 从描述文件读取JSON文件路径列表
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            json_files = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except FileNotFoundError:
        logger.error(f"错误: 描述文件不存在: {file_list_path}")
        return
    except Exception as e:
        logger.error(f"错误: 读取描述文件失败: {e}")
        return
    
    if not json_files:
        logger.error(f"描述文件 {file_list_path} 中没有找到任何JSON文件路径")
        return
    
    # 首先验证文件是否存在
    valid_files = []
    for json_file in json_files:
        if os.path.exists(json_file):
            valid_files.append(json_file)
        else:
            logger.warning(f"警告: 文件不存在，跳过: {json_file}")
    
    if not valid_files:
        logger.error("错误: 没有找到任何有效的JSON文件")
        return
    
    # 应用数量限制（先选取前 max_files 个文件）
    if max_files is not None and max_files > 0:
        valid_files = valid_files[:max_files]
        logger.info(f"限制处理文件数量为: {max_files}")
    
    # 然后在选定的文件中应用断点续传逻辑
    files_to_process = []
    skipped_cached = 0
    for json_file in valid_files:
        # 只有在启用断点续传模式时才检查是否已处理过
        if resume and cache_manager.is_file_cached(json_file):
            skipped_cached += 1
            continue
        files_to_process.append(json_file)
    
    if resume and skipped_cached > 0:
        logger.info(f"跳过已处理的文件: {skipped_cached} 个")
    
    if not files_to_process:
        if skipped_cached > 0:
            logger.info("所有指定范围内的文件都已处理完成!")
            return
        else:
            logger.error("错误: 没有找到任何需要处理的文件")
            return
    
    logger.info(f"总共 {len(valid_files)} 个文件在处理范围内，需要处理 {len(files_to_process)} 个文件")
    
    total_formulas = 0
    total_texts = 0
    total_errors = 0
    completed_count = 0
    
    # 准备任务参数列表（每个任务包含分布式缓存目录参数和渲染类型）
    task_args = [
        (json_file, output_dir, 300, cache_dir, render_type) 
        for json_file in files_to_process
    ]
    
    # 使用 ProcessPoolExecutor 进行动态并发处理
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 动态任务提交：维护一个任务队列和运行中的任务
        task_queue = list(task_args)  # 待处理任务队列
        running_tasks = {}  # 正在运行的任务 {future: (json_file, args)}
        submitted_count = 0
        completed_count = 0
        
        logger.info(f"开始动态提交任务，总任务数: {len(task_args)}, 最大并发数: {max_workers}")
        
        # 初始提交任务（提交数量不超过max_workers）
        while task_queue and len(running_tasks) < max_workers:
            args = task_queue.pop(0)
            json_file = args[0]
            future = executor.submit(process_single_file_worker, args)
            running_tasks[future] = (json_file, args)
            submitted_count += 1
        
        logger.info(f"初始提交了 {submitted_count} 个任务")
        
        # 处理完成的任务并动态提交新任务
        while running_tasks:
            # 等待至少一个任务完成
            for future in as_completed(running_tasks.keys(), timeout=task_timeout):
                json_file, args = running_tasks.pop(future)
                
                # 检查future状态，如果异常就直接跳过，避免进程池中断
                if future.exception() is not None:
                    # 进程异常退出，记录错误但继续处理其他任务
                    exception = future.exception()
                    logger.error(f"进程异常退出，处理文件 {json_file} 时发生异常: {exception}")
                    logger.error(f"  异常类型: {type(exception).__name__}")
                    logger.error(f"  异常堆栈: {traceback.format_exc()}")
                    total_errors += 1
                    completed_count += 1
                else:
                    try:
                        file_path, success, stats = future.result(timeout=task_timeout)
                        
                        # 累计统计信息
                        total_formulas += stats["formulas_count"]
                        total_texts += stats["texts_count"]
                        total_errors += stats["errors_count"]
                        completed_count += 1
                        
                        # 显示进度信息
                        progress_percent = (completed_count / len(files_to_process)) * 100
                        logger.info(f"[{completed_count}/{len(files_to_process)}] ({progress_percent:.1f}%) 完成: {os.path.basename(json_file)}")
                        if success:
                            status_msg = f"公式: {stats['formulas_count']} 个, 文本: {stats['texts_count']} 个"
                            if stats["errors_count"] > 0:
                                status_msg += f", 错误: {stats['errors_count']} 个"
                            logger.info(f"  {status_msg}")
                        else:
                            # 显示详细的错误信息
                            error_type = stats.get("error_type", "Unknown")
                            error_message = stats.get("error_message", "进程异常")
                            logger.error(f"  处理失败: {error_type} - {error_message}")
                        
                        # 显示当前运行状态
                        if len(running_tasks) > 0:
                            logger.debug(f"  当前运行任务数: {len(running_tasks)}, 待提交任务数: {len(task_queue)}")
                            
                    except TimeoutError:
                        logger.error(f"处理文件 {json_file} 超时 (超过 {task_timeout} 秒)")
                        total_errors += 1
                        completed_count += 1
                    except Exception as e:
                        logger.error(f"处理文件 {json_file} 时发生异常: {e}")
                        logger.error(f"  异常类型: {type(e).__name__}")
                        logger.error(f"  异常堆栈: {traceback.format_exc()}")
                        total_errors += 1
                        completed_count += 1
                
                # 动态提交新任务：当有任务完成时，立即提交下一个任务
                if task_queue:
                    new_args = task_queue.pop(0)
                    new_json_file = new_args[0]
                    new_future = executor.submit(process_single_file_worker, new_args)
                    running_tasks[new_future] = (new_json_file, new_args)
                    submitted_count += 1
                    
                    # 显示动态提交信息
                    if submitted_count % 100 == 0:  # 每100个任务显示一次进度
                        remaining = len(task_queue)
                        running_count = len(running_tasks)
                        logger.info(f"  动态提交进度: 已提交 {submitted_count}/{len(task_args)}, 运行中 {running_count}, 剩余 {remaining} 个任务")
                
                break  # 处理完一个任务后跳出内层循环，继续外层循环
    
    logger.info("ProcessPoolExecutor 已退出，所有任务完成")
    
    # 生成最终汇总信息
    final_summary = cache_manager.save_summary()
    
    logger.info("="*50)
    logger.info("批量处理完成!")
    logger.info(f"总计渲染公式: {total_formulas} 个")
    logger.info(f"总计渲染文本: {total_texts} 个")
    if total_errors > 0:
        logger.warning(f"总计错误: {total_errors} 个")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"分布式缓存目录: {cache_dir}")
    logger.info(f"并发工作进程数: {max_workers}")
    logger.info(f"处理文件数: {len(files_to_process)}")
    logger.info(f"缓存文件总数: {final_summary['total_cached_files']}")
    
    # 计算成功率
    success_rate = (100 - (total_errors / (total_formulas + total_texts) * 100)) if total_formulas + total_texts > 0 else 0
    logger.info(f"成功率: {success_rate:.1f}%")
    
    # 显示缓存系统性能提升信息
    logger.info(f"缓存汇总已保存到: {cache_manager.summary_file}")
    logger.info(f"详细日志已保存到: {log_file_path}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量渲染LaTeX公式和文本为PNG图片 (分布式缓存版本)")
    parser.add_argument("file_list", help="包含JSON文件路径列表的描述文件")
    parser.add_argument("-o", "--output", default="rendered_images", 
                       help="输出目录 (默认: rendered_images)")
    parser.add_argument("-n", "--max-files", type=int, default=None,
                       help="最大处理文件数量 (默认: 处理全部文件)")
    parser.add_argument("-c", "--cache-dir", default=None,
                       help="分布式缓存目录路径 (默认: {output_dir}_cache)")
    parser.add_argument("--resume", action="store_true",
                       help="断点续传模式，跳过已处理的文件")
    parser.add_argument("-j", "--max-workers", type=int, default=4,
                       help="最大并发工作进程数 (默认: 4)")
    parser.add_argument("-t", "--task-timeout", type=int, default=3600*24,
                       help="单个任务超时时间（秒） (默认: 3600*24)")
    parser.add_argument("-l", "--log-file", default=None,
                       help="日志文件路径 (默认: 自动生成带时间戳的文件名)")
    parser.add_argument("-r", "--render-type", choices=["formula", "text", "both"], default="both",
                       help="渲染类型: formula(只渲染公式), text(只渲染文本), both(都渲染) (默认: both)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_list):
        print(f"错误: 描述文件不存在: {args.file_list}")
        return
    
    if args.resume:
        print("启用断点续传模式")
    
    # 验证并发数范围
    if args.max_workers < 1:
        print("错误: 并发工作进程数必须大于0")
        return
    if args.max_workers > multiprocessing.cpu_count():
        print(f"警告: 并发工作进程数 ({args.max_workers}) 超过CPU核心数 ({multiprocessing.cpu_count()})")
    if args.max_workers > 16:
        print("警告: 并发工作进程数过大，建议不超过16")
    
    batch_process_from_list(
        file_list_path=args.file_list,
        output_dir=args.output,
        max_files=args.max_files,
        cache_dir=args.cache_dir,
        resume=args.resume,
        max_workers=args.max_workers,
        task_timeout=args.task_timeout,
        log_file=args.log_file,
        render_type=args.render_type
    )
    
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)
    main()
