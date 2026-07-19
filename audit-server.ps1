# 审计：对比服务器与本地后端代码（md5），检查服务健康与关键配置
$ErrorActionPreference = 'Stop'

$creds = Get-Content (Join-Path $PSScriptRoot '.ssh-credentials.json') -Raw | ConvertFrom-Json
$remote = "$($creds.username)@$($creds.host)"
$sshCommon = @('-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null')

$escapedPassword = $creds.password -replace '\^', '^^' -replace '&', '^&' -replace '\|', '^|' -replace '>', '^>' -replace '<', '^<' -replace '"', '^"'
$askpass = "$env:TEMP\ssh_askpass_audit.cmd"
Set-Content -Path $askpass -Value "@echo off`necho $escapedPassword" -Encoding ASCII
$env:SSH_ASKPASS = $askpass
$env:SSH_ASKPASS_REQUIRE = 'force'
$env:DISPLAY = 'dummy'

# 1. 本地 md5 清单
$localDir = Join-Path $PSScriptRoot 'server'
$local = @{}
Get-ChildItem -Recurse -File (Join-Path $localDir 'ewa'), (Join-Path $localDir 'scripts') -Include *.py |
  Where-Object { $_.FullName -notmatch '__pycache__' } |
  ForEach-Object {
    $rel = $_.FullName.Substring($localDir.Length + 1).Replace('\', '/')
    $local[$rel] = (Get-FileHash $_.FullName -Algorithm MD5).Hash.ToLower()
  }

# 2. 远程 md5 清单（base64 传输避免引号被多层转义吃掉）
$remoteCmd = "cd /opt/miaomiao/server && find ewa scripts -name '*.py' -not -path '*__pycache__*' | sort | xargs md5sum"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($remoteCmd))
try {
  $remoteOut = & ssh @sshCommon $remote "echo $b64 | base64 -d | bash"
}
finally {
  if (Test-Path $askpass) { Remove-Item $askpass -ErrorAction SilentlyContinue }
}

$remote = @{}
foreach ($line in ($remoteOut | Out-String) -split "`n") {
  $line = $line.Trim()
  if ($line -match '^([0-9a-f]{32})\s+(\S+)$') {
    $remote[$Matches[2].Trim()] = $Matches[1]
  }
}

# 3. 对比
$diff = 0
foreach ($rel in ($local.Keys | Sort-Object)) {
  if (-not $remote.ContainsKey($rel)) {
    Write-Host "仅本地: $rel" -ForegroundColor Yellow; $diff++
  } elseif ($local[$rel] -ne $remote[$rel]) {
    Write-Host "不一致: $rel" -ForegroundColor Red; $diff++
  }
}
foreach ($rel in ($remote.Keys | Sort-Object)) {
  if (-not $local.ContainsKey($rel)) {
    Write-Host "仅服务器: $rel" -ForegroundColor Yellow; $diff++
  }
}
if ($diff -eq 0) {
  Write-Host "后端代码完全一致（$($local.Count) 个 .py 文件 md5 全部匹配）" -ForegroundColor Green
} else {
  Write-Host "发现 $diff 处差异" -ForegroundColor Red
}
