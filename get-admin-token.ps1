# 从服务器 .env 读取 ADMIN_TOKEN 并写入本地 .ssh-credentials.json（该文件已被 gitignore）
$ErrorActionPreference = 'Stop'

$credsPath = Join-Path $PSScriptRoot '.ssh-credentials.json'
$creds = Get-Content $credsPath -Raw | ConvertFrom-Json
$remote = "$($creds.username)@$($creds.host)"
$sshCommon = @('-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null')

$escapedPassword = $creds.password -replace '\^', '^^' -replace '&', '^&' -replace '\|', '^|' -replace '>', '^>' -replace '<', '^<' -replace '"', '^"'
$askpass = "$env:TEMP\ssh_askpass_token.cmd"
Set-Content -Path $askpass -Value "@echo off`necho $escapedPassword" -Encoding ASCII
$env:SSH_ASKPASS = $askpass
$env:SSH_ASKPASS_REQUIRE = 'force'
$env:DISPLAY = 'dummy'

try {
  $token = & ssh @sshCommon $remote 'grep ^ADMIN_TOKEN= /opt/miaomiao/server/.env | cut -d= -f2'
  $token = ($token | Out-String).Trim()
  if (-not $token) {
    Write-Host "服务器 .env 未设置 ADMIN_TOKEN（当前为每次启动随机生成）" -ForegroundColor Yellow
    exit 1
  }
  $creds | Add-Member -NotePropertyName admin_token -NotePropertyValue $token -Force
  $creds | ConvertTo-Json | Set-Content $credsPath -Encoding UTF8
  Write-Host "ADMIN_TOKEN 已写入 $credsPath 的 admin_token 字段" -ForegroundColor Green
  Write-Host "token: $token"
}
finally {
  if (Test-Path $askpass) { Remove-Item $askpass -ErrorAction SilentlyContinue }
}
