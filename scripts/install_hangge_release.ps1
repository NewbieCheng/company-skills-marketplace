param(
    [string]$AssetUrl = "https://github.com/NewbieCheng/company-skills-marketplace/releases/download/social-media-hangge-moments-v1.0.0/hangge-moments-universal-v1.0.0.zip",
    [string]$ExpectedSha256 = "BB3E1D97CE315C65520406C795E829CBF6C15176630DAFE3FF7888E41C4D297A"
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
    throw "This installer is for Windows. Use scripts/install_hangge_release.sh on macOS."
}

$temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$temporaryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $temporaryBase ("hangge-skill-install-" + [guid]::NewGuid().ToString("N")))
)
$archivePath = Join-Path $temporaryRoot "hangge-moments.zip"
$expandedPath = Join-Path $temporaryRoot "expanded"

New-Item -ItemType Directory -Path $temporaryRoot, $expandedPath | Out-Null

try {
    Write-Host "正在从 GitHub Release 下载航哥朋友圈授权版..."
    Invoke-WebRequest `
        -Uri $AssetUrl `
        -OutFile $archivePath `
        -Headers @{"User-Agent" = "NewbieCheng-Skill-Installer"}

    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash
    if ($actualSha256 -ne $ExpectedSha256.ToUpperInvariant()) {
        throw "BUNDLE_TAMPERED: SHA-256 校验失败。期望 $ExpectedSha256，实际 $actualSha256"
    }

    Expand-Archive -LiteralPath $archivePath -DestinationPath $expandedPath
    $packageInstaller = Get-ChildItem `
        -LiteralPath $expandedPath `
        -Recurse `
        -File `
        -Filter "install-windows.ps1" |
        Select-Object -First 1
    if ($null -eq $packageInstaller) {
        throw "RUNTIME_INCOMPATIBLE: 安装包中缺少 install-windows.ps1"
    }

    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $packageInstaller.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "WRITE_FAILED: 本地运行器安装失败，退出码 $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "安装完成。请重启 Codex 或 Cursor，然后输入：激活航哥朋友圈" -ForegroundColor Green
    Write-Host "系统会返回 HGD1- 设备请求码；把它发给销售方换取本机专属 HGL1- 激活码。"
}
finally {
    $resolvedRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
    if (
        $resolvedRoot.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $resolvedRoot).StartsWith("hangge-skill-install-")
    ) {
        Remove-Item -LiteralPath $resolvedRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
