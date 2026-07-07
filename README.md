# 2026年下半年计算机顶会信息搜集 Agent

自动搜集 2026 年 7–12 月 CCF A 类顶会的召开信息、国内中稿论文及清北作者标注，生成结构化 Markdown 报告。

## 功能

- **会议信息采集**：时间、地点、官网、领域、CCF 评级等
- **中稿论文采集**：OpenReview、DBLP、清华/北大官网新闻
- **清北标注**：自动识别清华 🔵、北大 🔴 作者并高亮
- **报告生成**：按会议时间排序的 Markdown 报告
- **自动化更新**：GitHub Actions 每周定时运行

## 项目结构

```
├── config/                 # 配置文件
│   ├── conferences.yaml    # 13 个目标会议
│   ├── institutions.yaml   # 清北关键词与国内机构
│   └── settings.yaml       # 运行参数
├── src/
│   ├── collector/          # 数据采集器
│   ├── processor/          # 数据处理
│   ├── generator/          # 报告生成
│   └── sync/               # Git 同步
├── templates/              # Jinja2 模板
├── data/                   # 采集缓存
├── reports/                # 生成的报告
├── main.py                 # 主入口
└── requirements.txt
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 增量更新全部会议
python main.py

# 全量采集
python main.py --full

# 仅采集 ICML 2026
python main.py --conference icml-2026 --full

# 采集并推送至 GitHub
python main.py --full --push
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--full` | 全量采集（默认增量） |
| `--conference ID` | 指定会议 ID |
| `--push` | 自动 git commit + push |
| `--force` | 强制重新采集 |
| `--no-report` | 跳过报告生成 |

## 配置说明

在 `config/conferences.yaml` 中维护会议列表与各数据源 ID。当官方公布录用名单后，更新对应会议的 `openreview.venue_id` 或 `dblp.key` 即可。

在 `config/institutions.yaml` 中可扩展清北关键词与国内机构列表。

## GitHub Actions 部署

1. 将项目推送到 GitHub 仓库
2. 确认 Actions 已启用
3. 工作流每周一自动运行，也可在 Actions 页面手动触发

## 目标会议（2026 H2）

ACL、ICML、SIGGRAPH、DAC、KDD、USENIX Security、IJCAI、VLDB、ISSTA、ASE、EMNLP、FOCS、NeurIPS

## 注意事项

- 遵守各网站 robots.txt，默认请求间隔 1 秒
- 单数据源失败不影响整体运行
- 2026 年会议录用名单陆续公布前，报告可能为空，属正常现象
