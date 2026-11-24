param([string]$WorkDir = (Join-Path $PSScriptRoot '..\..\.windows-build'),
      [string]$Revision = 'pinned')
$ErrorActionPreference = 'Stop'
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
if ([IO.Path]::GetPathRoot($WorkDir) -eq 'C:\') { throw 'Choose a data drive with -WorkDir D:\InkpadBuild' }
$cache = Join-Path $WorkDir 'cache'
$temp = Join-Path $WorkDir 'tmp'
New-Item -ItemType Directory -Force -Path $cache,$temp | Out-Null
$lock = [IO.File]::Open((Join-Path $WorkDir 'build.lock'),'OpenOrCreate','Write','None')
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
try {
    $env:TEMP = $temp
    $env:TMP = $temp
    $name = 'python-3.14.0-embed-amd64.zip'
    $sha = '8D4D3590C10449D78AA4375F534E6D5F3027D67FDC362DD1A882279DB6F90FDF'
    $archive = Join-Path $cache $name
    if (!(Test-Path -LiteralPath $archive) -or (Get-FileHash -LiteralPath $archive).Hash -ne $sha) {
        $partial = "$archive.part"
        Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/3.14.0/$name" -OutFile $partial
        if ((Get-FileHash -LiteralPath $partial).Hash -ne $sha) { throw "Invalid download: $name" }
        Move-Item -LiteralPath $partial -Destination $archive -Force
    }
    $hostDir = Join-Path $WorkDir "bootstrap-$($sha.Substring(0,12))"
    if (!(Test-Path -LiteralPath $hostDir)) {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $staging = Join-Path $WorkDir ([guid]::NewGuid().ToString('N'))
        [IO.Compression.ZipFile]::ExtractToDirectory($archive,$staging)
        [IO.Directory]::Move($staging,$hostDir)
    }
    $python = Join-Path $hostDir 'python.exe'
    & $python -I -B (Join-Path $PSScriptRoot 'prepare.py') $WorkDir
    if ($LASTEXITCODE -ne 0) { throw 'Toolchain preparation failed' }
    & $python -I -B (Join-Path $PSScriptRoot 'source.py') $WorkDir $Revision
    if ($LASTEXITCODE -ne 0) { throw 'Upstream source preparation failed' }
    & $python -I -B (Join-Path $PSScriptRoot 'package.py') $WorkDir
    if ($LASTEXITCODE -ne 0) { throw 'Windows build or verification failed' }
} finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    $lock.Dispose()
}
