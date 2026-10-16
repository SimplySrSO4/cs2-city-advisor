# pdf_render_winrt.ps1 —— 用 Windows 内置 PDF 渲染器（Windows.Data.Pdf）把 PDF 逐页渲染成 PNG。
#
# 为什么需要它：本项目的多份 PDF 用 JBIG2Decode / CCITTFaxDecode / JPXDecode 编码页面图像，
# Pillow 无法解码 JBIG2，且本机没有任何外部 PDF 工具（无 gs / poppler / mutool / magick）。
# Windows.Data.Pdf 是系统组件，能解码全部编码，是唯一可用的通用渲染路径。
#
# 关键实现：不用 StorageFile（沙箱下 UnauthorizedAccessException），改用
# File.OpenRead + AsRandomAccessStream 构造 IRandomAccessStream。
#
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File pdf_render_winrt.ps1 `
#       -Pdf <file.pdf> -OutDir <dir> [-First 1] [-Count 0] [-Scale 1.4] [-Prefix p]
# 输出：<OutDir>/<Prefix>0001.png ...
param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$First = 1,
    [int]$Count = 0,
    [double]$Scale = 1.4,
    [string]$Prefix = "p"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]
$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
    })[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}
function AwaitAction($WinRtAction) {
    $netTask = $asTaskAction.Invoke($null, @($WinRtAction))
    $netTask.Wait(-1) | Out-Null
}

[Windows.Data.Pdf.PdfDocument, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfPageRenderOptions, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataWriter, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$fs = [System.IO.File]::OpenRead($Pdf)
$ras = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($fs)
$doc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromStreamAsync($ras)) ([Windows.Data.Pdf.PdfDocument])
$total = [int]$doc.PageCount
Write-Host ("pages_total: " + $total)

$last = if ($Count -gt 0) { [Math]::Min($total, $First + $Count - 1) } else { $total }
$t0 = Get-Date
for ($i = $First; $i -le $last; $i++) {
    $out = Join-Path $OutDir ("{0}{1:D4}.png" -f $Prefix, $i)
    if (Test-Path $out) { continue }
    try {
        $page = $doc.GetPage($i - 1)
        $opt = New-Object Windows.Data.Pdf.PdfPageRenderOptions
        $opt.DestinationWidth = [uint32][Math]::Round($page.Size.Width * $Scale)
        $opt.DestinationHeight = [uint32][Math]::Round($page.Size.Height * $Scale)
        $ms = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        AwaitAction ($page.RenderToStreamAsync($ms, $opt))
        $size = [int]$ms.Size
        $ms.Seek(0)
        $reader = New-Object Windows.Storage.Streams.DataReader($ms)
        Await ($reader.LoadAsync([uint32]$size)) ([uint32]) | Out-Null
        $bytes = New-Object byte[] $size
        $reader.ReadBytes($bytes)
        [System.IO.File]::WriteAllBytes($out, $bytes)
        $reader.Dispose(); $ms.Dispose(); $page.Dispose()
        if (($i - $First) % 20 -eq 0) {
            Write-Host ("  rendered {0}/{1} ({2:N1}s)" -f ($i - $First + 1), ($last - $First + 1), ((Get-Date) - $t0).TotalSeconds)
        }
    }
    catch {
        Write-Host ("ERR page " + $i + " -> " + $_.Exception.Message)
    }
}
$ras.Dispose(); $fs.Dispose()
Write-Host ("done. {0} pages -> {1}" -f ($last - $First + 1), $OutDir)
