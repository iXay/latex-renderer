# 动态任务提交机制改进

## 问题描述

原始代码在处理大量任务（如2万+个并发任务）时存在以下问题：

1. **一次性提交所有任务**：所有任务在开始时就被提交到 `ProcessPoolExecutor`，但只有 `max_workers` 个进程在运行
2. **资源竞争**：大量任务在队列中等待，可能导致某些任务长期拿不到资源而超时
3. **内存占用**：所有任务的 Future 对象同时存在，占用大量内存

## 解决方案

### 1. 动态任务提交机制

**改进前**：
```python
# 一次性提交所有任务
future_to_file = {
    executor.submit(process_single_file_worker, args): args[0]
    for args in task_args
}
```

**改进后**：
```python
# 动态任务提交：维护任务队列和运行中的任务
task_queue = list(task_args)  # 待处理任务队列
running_tasks = {}  # 正在运行的任务

# 初始提交任务（不超过max_workers）
while task_queue and len(running_tasks) < max_workers:
    args = task_queue.pop(0)
    future = executor.submit(process_single_file_worker, args)
    running_tasks[future] = (json_file, args)

# 动态提交新任务：当有任务完成时，立即提交下一个任务
if task_queue:
    new_args = task_queue.pop(0)
    new_future = executor.submit(process_single_file_worker, new_args)
    running_tasks[new_future] = (new_json_file, new_args)
```

### 2. 主要改进点

#### 2.1 任务队列管理
- **任务队列**：维护一个待处理任务队列，而不是一次性提交所有任务
- **运行中任务跟踪**：只跟踪实际在运行的任务，减少内存占用
- **动态提交**：每当有任务完成时，立即从队列中取出下一个任务提交

#### 2.2 资源优化
- **内存效率**：同时存在的 Future 对象数量等于 `max_workers`，而不是总任务数
- **CPU利用率**：始终保持 `max_workers` 个任务在运行，最大化CPU利用率
- **避免饥饿**：任务按顺序提交，避免某些任务长期等待

#### 2.3 进度监控增强
- **实时进度**：显示完成百分比和当前运行状态
- **动态提交进度**：每100个任务显示一次提交进度
- **运行状态**：显示当前运行任务数和待提交任务数

#### 2.4 可配置超时
- **任务超时参数**：新增 `--task-timeout` 参数，可配置单个任务超时时间
- **默认超时**：保持1200秒（20分钟）的默认超时时间

### 3. 性能优势

#### 3.1 内存使用
- **改进前**：O(n) 内存使用，n为总任务数
- **改进后**：O(max_workers) 内存使用，与任务总数无关

#### 3.2 任务调度
- **改进前**：所有任务同时排队，可能导致饥饿
- **改进后**：FIFO队列，保证任务按顺序执行

#### 3.3 资源利用率
- **改进前**：可能存在资源浪费，某些任务等待时间过长
- **改进后**：始终保持最大并发数，资源利用率最优

### 4. 使用示例

```bash
# 使用默认设置
python batch_renderer.py arxiv_file_list.txt

# 自定义并发数和超时时间
python batch_renderer.py arxiv_file_list.txt -j 8 -t 1800

# 断点续传模式
python batch_renderer.py arxiv_file_list.txt --resume -j 6
```

### 5. 新增参数

- `-t, --task-timeout`：单个任务超时时间（秒），默认1200秒

### 6. 输出改进

```
开始动态提交任务，总任务数: 20000, 最大并发数: 8
初始提交了 8 个任务

[1/20000] (0.0%) 完成: 240100001_extracted.json
  公式: 15 个, 文本: 23 个
  当前运行任务数: 8, 待提交任务数: 19991

[2/20000] (0.0%) 完成: 240100002_extracted.json
  公式: 8 个, 文本: 12 个
  当前运行任务数: 8, 待提交任务数: 19990

...

  动态提交进度: 已提交 100/20000, 运行中 8, 剩余 19900
```

## 总结

动态任务提交机制解决了大规模并发处理中的资源竞争和超时问题，通过维护任务队列和动态提交，确保了：

1. **高效资源利用**：始终保持最大并发数
2. **内存优化**：内存使用与任务总数无关
3. **公平调度**：任务按FIFO顺序执行
4. **实时监控**：提供详细的进度和状态信息
5. **灵活配置**：支持自定义并发数和超时时间

这种改进特别适合处理大量任务（如2万+个文件）的场景，能够显著提高处理效率和稳定性。
