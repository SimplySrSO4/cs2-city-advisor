# run_extract_all.ps1 —— 一键跑完两本扫描书的图片导出 + OCR + 合并
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File run_extract_all.ps1 [-Book all|brt|plan] [-Workers 2]
param(
    [string]$Book = "all",
    [int]$Workers = 2,
    [string]$Scale = "0.55"
)
$ErrorActionPreference = "Continue"
# 工作区根由脚本自身位置推出：scripts/tools/ → scripts/ → skill 目录 → 工作区
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $here "..\..\..\..")).Path
$py = "C:\Users\Devcl\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$driver = Join-Path $here "ocr_books.py"

$books = @()
if ($Book -eq "all" -or $Book -eq "brt") { $books += @{ key = "brt"; work = "skill-extract\brt" } }
if ($Book -eq "all" -or $Book -eq "plan") { $books += @{ key = "plan"; work = "skill-extract\plan" } }

foreach ($b in $books) {
    $work = Join-Path $root $b.work
    Write-Host "=================== $($b.key) ==================="
    Write-Host "--- stage export"
    & $py $driver --book $b.key --work $work --scale $Scale --stage export
    Write-Host "--- stage ocr (workers=$Workers)"
    & $py $driver --book $b.key --work $work --stage ocr --workers $Workers
    Write-Host "--- stage assemble"
    & $py $driver --book $b.key --work $work --stage assemble
}
Write-Host "ALL DONE"
