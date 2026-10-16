# ocr_winrt.ps1 —— 用 Windows 内置 OCR（Windows.Media.Ocr）识别图片中的中文
# 纯系统组件，无需管理员权限、无需安装任何软件、不需要联网。
#
# 关键实现说明：
#   本脚本**不使用** StorageFile.GetFileFromPathAsync —— 在受限/沙箱进程里它会抛
#   UnauthorizedAccessException（WinRT 文件访问受应用能力约束）。改为把图片字节读入
#   InMemoryRandomAccessStream，再用 BitmapDecoder 解码，完全不触碰 WinRT 文件系统。
#
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File ocr_winrt.ps1 `
#       -ImageDir <图片目录> -OutDir <输出目录> [-Lang zh-Hans-CN] [-Pattern *.png] [-MaxImages N]
#
# 输出：<OutDir>/<同名>.txt        每张图的识别文本（UTF-8 无 BOM）
#       <OutDir>/_ocr_summary.txt  每张图的字符数与行数（用于可读性判定）
# 退出码：0 正常；3 = 系统没有任何 OCR 语言包（此时应如实报告"无法查看"，不要猜测内容）
param(
    [Parameter(Mandatory = $true)][string]$ImageDir,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [string]$Lang = "",
    [string]$Pattern = "*",
    [int]$MaxImages = 0,
    [double]$MaxWidth = 0
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
Add-Type -AssemblyName System.Drawing | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataWriter, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$engine = $null
$available = @([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag })
Write-Host ("available OCR languages: " + ($available -join ", "))

if ($Lang -ne "") {
    try {
        $language = New-Object Windows.Globalization.Language($Lang)
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
    }
    catch { $engine = $null }
}
if ($null -eq $engine) {
    foreach ($tag in @("zh-Hans-CN", "zh-Hans", "zh-CN")) {
        if ($available -contains $tag) {
            try {
                $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language($tag)))
                if ($engine) { break }
            }
            catch { }
        }
    }
}
if ($null -eq $engine) {
    try { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() } catch { $engine = $null }
}
if ($null -eq $engine) {
    Write-Error "NO_OCR_ENGINE: 系统未安装任何 OCR 语言包（或 Windows.Media.Ocr 不可用）"
    exit 3
}
Write-Host ("using OCR language: " + $engine.RecognizerLanguage.LanguageTag)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$files = @(Get-ChildItem -Path $ImageDir -File | Where-Object { $_.Extension -match '^\.(png|jpg|jpeg|bmp|tif|tiff)$' } | Sort-Object Name)
if ($MaxImages -gt 0) { $files = @($files | Select-Object -First $MaxImages) }

$summary = New-Object System.Collections.Generic.List[string]
$summary.Add("engine_language: " + $engine.RecognizerLanguage.LanguageTag)
$summary.Add("images_found: " + $files.Count)
$utf8 = New-Object System.Text.UTF8Encoding($false)

foreach ($f in $files) {
    $outPath = Join-Path $OutDir ($f.BaseName + ".txt")
    try {
        $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
        $ras = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        $writer = New-Object Windows.Storage.Streams.DataWriter($ras)
        $writer.WriteBytes($bytes)
        Await ($writer.StoreAsync()) ([uint32]) | Out-Null
        Await ($writer.FlushAsync()) ([bool]) | Out-Null
        $writer.DetachStream() | Out-Null
        $ras.Seek(0)
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($ras)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $sb = New-Object System.Text.StringBuilder
        foreach ($line in $result.Lines) { [void]$sb.AppendLine($line.Text) }
        $text = $sb.ToString()
        [System.IO.File]::WriteAllText($outPath, $text, $utf8)
        $summary.Add(("{0}`t{1}`t{2}" -f $f.Name, $text.Length, $result.Lines.Count))
        $bitmap.Dispose()
        $ras.Dispose()
    }
    catch {
        $msg = $_.Exception.Message
        $inner = $_.Exception.InnerException
        while ($null -ne $inner) { $msg += " << " + $inner.GetType().Name + ": " + $inner.Message; $inner = $inner.InnerException }
        $summary.Add(("{0}`tERROR`t{1}" -f $f.Name, $msg))
        Write-Host ("ERR " + $f.Name + " -> " + $msg)
    }
}
[System.IO.File]::WriteAllLines((Join-Path $OutDir "_ocr_summary.txt"), $summary, $utf8)
Write-Host "done. summary -> $OutDir\_ocr_summary.txt"
