# 计算机顶会信息搜集 Agent 完整方案

## 一、需求文档（Markdown）

# 2026年下半年计算机顶会信息搜集系统

## 1. 项目概述

本项目旨在开发一个自动化 Agent，用于搜集2026年下半年（7月-12月）计算机领域顶级会议（CCF A类）的相关信息，包括会议召开时间、地点、国内中稿论文及作者信息，并特别标注清华大学、北京大学作者的论文。最终输出结构化的 Markdown 报告，并部署至 GitHub 实现自动化更新。

## 2. 功能需求

### 2.1 会议信息采集

- **采集范围**：2026年7月至12月期间召开的 CCF A 类计算机顶会
- **采集字段**：
  - 会议全称及缩写
  - CCF 评级
  - 所属领域
  - 召开时间（起止日期）
  - 召开地点（城市、国家）
  - 官方网站
  - 投稿截止时间
  - 录用通知时间

### 2.2 中稿论文信息采集

- **数据来源**：各会议官方录用名单、OpenReview、DBLP、高校官网新闻
- **采集字段**：
  - 论文标题
  - 全部作者列表
  - 作者所属机构
  - 论文摘要（如有）
  - 论文链接
  - 是否获奖（最佳论文、Highlight等）

### 2.3 清北作者标注

- 自动识别作者所属机构中包含"清华大学"、"Tsinghua University"、"北京大学"、"Peking University"的论文
- 使用特殊标记（如 🔵清华、🔴北大）进行高亮标注
- 单独统计清北各会议中稿数量并生成汇总表格



### 2.4 报告生成

- 自动生成结构化 Markdown 报告
- 按会议时间顺序排列
- 每个会议独立章节，包含基本信息 + 国内中稿列表 + 清北高亮
- 生成总览统计：会议总数、国内中稿总数、清北中稿统计



### 2.5 自动化更新

- 支持定时执行数据采集
- 增量更新：仅更新新增/变动的会议信息
- 自动提交至 GitHub 仓库



## 3. 2026下半年目标会议清单


| 会议缩写                 | 会议全称                                                            | 领域       | 召开时间          | 召开地点               | CCF评级 |
| -------------------- | --------------------------------------------------------------- | -------- | ------------- | ------------------ | ----- |
| ACL 2026             | Annual Meeting of the Association for Computational Linguistics | 自然语言处理   | 2026.07.02    | San Diego, USA     | A     |
| ICML 2026            | International Conference on Machine Learning                    | 机器学习     | 2026.07.06-11 | Seoul, South Korea | A     |
| SIGGRAPH 2026        | Special Interest Group on Computer Graphics                     | 计算机图形学   | 2026.07.19    | Los Angeles, USA   | A     |
| DAC 2026             | Design Automation Conference                                    | 体系结构/EDA | 2026.07.26    | Long Beach, USA    | A     |
| KDD 2026             | Knowledge Discovery and Data Mining                             | 数据挖掘     | 2026.08.09    | Jeju, Korea        | A     |
| USENIX Security 2026 | USENIX Security Symposium                                       | 网络安全     | 2026.08.12    | Baltimore, USA     | A     |
| IJCAI 2026           | International Joint Conference on AI                            | 人工智能综合   | 2026.08.15    | Bremen, Germany    | A     |
| VLDB 2026            | Very Large Data Bases                                           | 数据库      | 2026.08.31    | Boston, USA        | A     |
| ISSTA 2026           | International Symposium on Software Testing                     | 软件工程     | 2026.10.03-09 | Oakland, USA       | A     |
| ASE 2026             | Automated Software Engineering                                  | 软件工程     | 2026.10.12-16 | 待定                 | A     |
| EMNLP 2026           | Empirical Methods in NLP                                        | 自然语言处理   | 2026.10.24-29 | Budapest, Hungary  | A     |
| FOCS 2026            | Foundations of Computer Science                                 | 理论计算机    | 2026.11.08-11 | New York, USA      | A     |
| NeurIPS 2026         | Neural Information Processing Systems                           | 机器学习     | 2026.12.06-12 | Sydney, Australia  | A     |




## 4. 技术架构



### 4.1 核心模块

1. **配置管理模块**：维护会议列表、数据源配置、关键词匹配规则
2. **数据采集模块**：多源爬虫 + API 调用（OpenReview、DBLP、Semantic Scholar）
3. **数据处理模块**：机构名称归一化、作者去重、清北识别
4. **报告生成模块**：Markdown 模板渲染
5. **Git 同步模块**：自动提交推送至 GitHub



### 4.2 技术栈

- **开发环境**：Cursor IDE + Python
- **核心库**：requests, BeautifulSoup, PyYAML, Jinja2, GitPython
- **数据源**：会议官网、OpenReview API、DBLP API、Semantic Scholar API
- **部署**：GitHub Actions 定时运行



## 5. 输出格式规范



### 5.1 单会议输出模板

```markdown
## 会议名称（缩写）

**基本信息**
- 时间：YYYY.MM.DD - YYYY.MM.DD
- 地点：City, Country
- 官网：链接
- 领域：XXX

**国内中稿概览**
- 总中稿数：XX 篇
- 清华大学：XX 篇 🔵
- 北京大学：XX 篇 🔴

**清北高亮论文列表**

1. **论文标题**
   - 作者：XXX 🔵, XXX, XXX 🔴
   - 机构：清华大学 XXX 实验室，北京大学 XXX 学院
   - 链接：paper_url

...
```



## 6. 非功能需求

- **可扩展性**：支持新增会议、新增数据源、新增高校标注
- **可维护性**：模块化设计，配置与代码分离
- **容错性**：单数据源失败不影响整体运行，支持降级策略
- **合规性**：遵守各网站 robots.txt，控制请求频率

---



## 二、Cursor Agent 实现方案



### 开发步骤

**第一步：项目初始化**

1. 在 Cursor 中创建项目目录 `conference-tracker`
2. 初始化 Python 项目与虚拟环境
3. 创建目录结构：
  ```
   conference-tracker/
   ├── config/           # 配置文件
   ├── src/              # 源代码
   │   ├── collector/    # 数据采集器
   │   ├── processor/    # 数据处理
   │   ├── generator/    # 报告生成
   │   └── sync/         # Git同步
   ├── data/             # 原始数据缓存
   ├── output/           # 生成的Markdown
   └── requirements.txt
  ```

**第二步：配置会议清单**

- 在 `config/conferences.yaml` 中录入上述13个会议的基础信息
- 配置各会议的数据采集源（官网URL、OpenReview ID等）
- 配置清北机构关键词匹配规则

**第三步：核心模块开发**

1. **采集器模块**
  - 通用爬虫基类：处理请求头、频率控制、异常重试
  - OpenReview 采集器：通过 API 获取录用论文列表
  - DBLP 采集器：按会议和机构检索论文
  - 高校新闻采集器：抓取清华、北大计算机学院官网的中稿喜报
2. **处理器模块**
  - 机构名称归一化（别名映射：THU、清华、Tsinghua → 清华大学）
  - 作者机构关联匹配
  - 清北标记逻辑
  - 去重与合并
3. **生成器模块**
  - Jinja2 Markdown 模板
  - 按会议分组渲染
  - 统计数据计算
4. **Git 同步模块**
  - 使用 GitPython 自动 commit + push
  - 生成提交信息（包含更新日期和会议）

**第四步：主入口与调度**

- 编写 `main.py` 串联全流程
- 支持命令行参数：指定会议、全量/增量、是否推送
- 配置 GitHub Actions workflow 实现每周自动运行



### Cursor 使用技巧

1. **@文件引用**：开发时引用 `config/conferences.yaml` 让 Cursor 了解会议清单
2. **分模块开发**：逐个模块实现，每完成一个让 Cursor 进行代码审查
3. **测试驱动**：先用 ICML 2026（已有结果）做测试集，验证采集和标注准确性
4. **重构优化**：跑通后让 Cursor 帮忙优化代码结构和异常处理

---



## 三、GitHub 部署方案



### 仓库结构

```
your-github-repo/
├── .github/
│   └── workflows/
│       └── update-report.yml    # 自动更新工作流
├── reports/
│   └── 2026-H2-conferences.md   # 生成的报告
├── src/                         # 源代码（同上）
├── config/                      # 配置
├── requirements.txt
└── README.md
```



### GitHub Actions 配置

创建 `.github/workflows/update-report.yml`：

```yaml
name: Update Conference Report

on:
  schedule:
    - cron: '0 0 * * 1'  # 每周一凌晨执行
  workflow_dispatch:      # 支持手动触发

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run collector
        run: python main.py --full --push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit and push changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add reports/
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto update: $(date +%Y-%m-%d)" && git push)
```



### 部署步骤

1. **创建 GitHub 仓库**：新建公开仓库 `conference-2026-h2-tracker`
2. **推送初始代码**：将本地项目推送到仓库
3. **启用 Actions**：确认 GitHub Actions 已启用
4. **首次手动运行**：触发一次 workflow 验证全流程
5. **设置 Pages（可选）**：将 Markdown 渲染为网页展示



### 进阶优化建议

- **缓存机制**：使用 GitHub Actions cache 缓存已采集数据，减少重复请求
- **Issue 跟踪**：发现新中稿信息时自动创建 Issue
- **RSS 订阅**：生成 RSS feed 供订阅
- **多格式输出**：除 Markdown 外，支持 JSON、CSV 导出

