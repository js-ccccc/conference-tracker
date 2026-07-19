# 一键创建 GitHub 仓库并推送
# 用法: .\scripts\setup_github.ps1 [-RepoName conference-2026-h2-tracker] [-Public]

param(
    [string]$RepoName = "conference-2026-h2-tracker",
    [switch]$Public = $true
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 检查 gh CLI
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "未检测到 GitHub CLI，正在安装..." -ForegroundColor Yellow
    winget install GitHub.cli --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# 检查登录状态
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "请先登录 GitHub:" -ForegroundColor Yellow
    gh auth login
}

# 确保有初始提交
$commitCount = (git rev-list --count HEAD 2>$null)
if (-not $commitCount -or $commitCount -eq "0") {
    Write-Host "创建初始提交..." -ForegroundColor Cyan
    git add .
    git commit -m "Initial commit: conference tracker agent"
}

# 检查是否已有 remote
$remoteUrl = git remote get-url origin 2>$null
if ($remoteUrl) {
    Write-Host "已存在 remote: $remoteUrl" -ForegroundColor Yellow
    $push = git push -u origin main 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "推送完成！" -ForegroundColor Green
        exit 0
    }
    Write-Host "推送失败（远程仓库可能已删除），将移除旧 remote 并重新创建..." -ForegroundColor Yellow
    git remote remove origin
}

# 创建 GitHub 仓库
$visibility = if ($Public) { "--public" } else { "--private" }
Write-Host "创建仓库: $RepoName ($visibility)" -ForegroundColor Cyan
gh repo create $RepoName $visibility --source=. --remote=origin --push

if ($LASTEXITCODE -eq 0) {
    $repoUrl = gh repo view --json url -q .url
    Write-Host ""
    Write-Host "仓库已创建并推送成功！" -ForegroundColor Green
    Write-Host "地址: $repoUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "  1. 打开仓库 Settings -> Actions -> General"
    Write-Host "  2. Workflow permissions 设为 Read and write permissions"
    Write-Host "  3. Actions 页面手动运行 Update Conference Report"
} else {
    Write-Host "创建失败，请手动参考 docs/GITHUB_SETUP.md" -ForegroundColor Red
    exit 1
}
