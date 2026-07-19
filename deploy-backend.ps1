# 后端部署脚本
# 读取本地 .ssh-credentials.json，上传 server/ewa + server/scripts 到服务器并重启服务
# 不会触碰服务器上的 data/、.env、.venv

$ErrorActionPreference = 'Stop'

$credsPath = Join-Path $PSScriptRoot '.ssh-credentials.json'
if (-not (Test-Path $credsPath)) {
  throw "找不到 $credsPath，请先创建 .ssh-credentials.json"
}

$creds = Get-Content $credsPath -Raw | ConvertFrom-Json
$required = @('username', 'password', 'host')
foreach ($key in $required) {
  if (-not $creds.$key) { throw "缺少 $key 字段" }
}

$remote = "$($creds.username)@$($creds.host)"
$sshCommon = @('-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null')

# 1. 打包后端代码（ewa 包 + scripts 脚本）
Write-Host "Packing backend code..." -ForegroundColor Cyan
$serverDir = Join-Path $PSScriptRoot 'server'
$tar = "$env:TEMP\backend_code.tar.gz"
if (Test-Path $tar) { Remove-Item $tar }
& tar -czf $tar -C $serverDir ewa scripts
if ($LASTEXITCODE -ne 0) { throw "tar failed" }

# 2. 创建 SSH_ASKPASS 辅助脚本
$escapedPassword = $creds.password -replace '\^', '^^' -replace '&', '^&' -replace '\|', '^|' -replace '>', '^>' -replace '<', '^<' -replace '"', '^"'
$askpass = "$env:TEMP\ssh_askpass_deploy_backend.cmd"
Set-Content -Path $askpass -Value "@echo off`necho $escapedPassword" -Encoding ASCII

$env:SSH_ASKPASS = $askpass
$env:SSH_ASKPASS_REQUIRE = 'force'
$env:DISPLAY = 'dummy'

try {
  Write-Host "Uploading archive to server..." -ForegroundColor Cyan
  & scp @sshCommon $tar "$remote`:/tmp/backend_code.tar.gz"
  if ($LASTEXITCODE -ne 0) { throw "SCP upload failed" }

  Write-Host "Deploying on server..." -ForegroundColor Cyan
  $remoteScript = @'
set -e
cd /opt/miaomiao/server
# 先备份现有代码
rm -rf /tmp/ewa_backup
cp -r ewa /tmp/ewa_backup
# 解压覆盖（只动 ewa/ 和 scripts/，不碰 data/ .env .venv）
tar -xzf /tmp/backend_code.tar.gz
systemctl restart miaomiao.service
sleep 2
systemctl is-active miaomiao.service
curl -s http://127.0.0.1:8000/health
echo "Backend deployment finished"
'@
  # Windows 换行符会导致远端 bash 解析失败，先转成 LF
  $remoteScript = $remoteScript -replace "`r`n", "`n"
  & ssh @sshCommon $remote $remoteScript
  if ($LASTEXITCODE -ne 0) { throw "Remote deployment failed" }
}
finally {
  if (Test-Path $askpass) { Remove-Item $askpass -ErrorAction SilentlyContinue }
  if (Test-Path $tar) { Remove-Item $tar -ErrorAction SilentlyContinue }
}

Write-Host "Done!" -ForegroundColor Green
