# GitHub 仓库配置指南

## 重新部署（原仓库已删除）

本地代码保留，只需新建远程仓库并重新推送。

### 1. 在 GitHub 新建空仓库

1. 打开 [https://github.com/new](https://github.com/new)
2. 仓库名：`conference-tracker` 或 `conference-2026-h2-tracker`
3. 选 **Public**
4. **不要**勾选 README / .gitignore / License
5. 点击 **Create repository**

### 2. 更换远程地址并推送

将 `js-ccccc` 和仓库名换成你的账号与新建仓库名：

```powershell
cd "c:\Users\24993\Desktop\会议收集"

# 删除指向已删仓库的旧 remote
git remote remove origin

# 绑定新仓库（示例）
git remote add origin https://github.com/js-ccccc/conference-tracker.git

# 推送全部本地提交
git branch -M main
git push -u origin main
```

若 `git push` 失败，先登录 GitHub CLI 或使用 Personal Access Token。

### 3. 启用 Actions 并手动跑一次

1. 仓库 **Settings** → **Actions** → **General**
2. **Workflow permissions** → 选 **Read and write permissions** → Save
3. **Actions** → **Update Conference Report** → **Run workflow**

### 4. 验证

- `reports/2026-H2-conferences.md` 应有内容
- Actions 运行日志中应看到四类数据源采集（官网 / 科技新闻 / 学校 / 微信）

---

## 方式一：网页创建（首次部署）

### 1. 在 GitHub 创建仓库

1. 打开 [https://github.com/new](https://github.com/new)
2. 仓库名填写：`conference-2026-h2-tracker`（或自定义）
3. 选择 **Public**
4. **不要**勾选 "Add a README"（本地已有代码）
5. 点击 **Create repository**

### 2. 推送本地代码

将 `YOUR_USERNAME` 替换为你的 GitHub 用户名后执行：

```powershell
cd "c:\Users\24993\Desktop\会议收集"

git remote add origin https://github.com/YOUR_USERNAME/conference-2026-h2-tracker.git
git branch -M main
git push -u origin main
```

### 3. 启用 GitHub Actions

1. 进入仓库 → **Settings** → **Actions** → **General**
2. 在 "Workflow permissions" 中选择 **Read and write permissions**
3. 保存后，进入 **Actions** 标签页
4. 选择 **Update Conference Report** → **Run workflow** 手动触发一次

---

## 方式二：使用脚本（需已安装 GitHub CLI）

```powershell
# 安装 GitHub CLI（若未安装）
winget install GitHub.cli

# 登录
gh auth login

# 一键创建仓库并推送
cd "c:\Users\24993\Desktop\会议收集"
.\scripts\setup_github.ps1 -RepoName conference-2026-h2-tracker -Public
```

---

## 自动更新说明

| 配置项 | 值 |
|--------|-----|
| 定时任务 | 每周一 UTC 00:00（北京时间周一 08:00） |
| 工作流文件 | `.github/workflows/update-report.yml` |
| 输出报告 | `reports/2026-H2-conferences.md` |
| 手动触发 | Actions → Update Conference Report → Run workflow |

## 可选：GitHub Pages 展示报告

1. 仓库 **Settings** → **Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选 `main`，文件夹选 `/reports` 或根目录
4. 保存后可通过 `https://YOUR_USERNAME.github.io/conference-2026-h2-tracker/` 访问

> 若使用 `/reports` 目录，Markdown 不会自动渲染，建议配合 [github-markdown-css](https://github.com/sindresorhus/github-markdown-css) 或改用 Actions 生成 HTML。
