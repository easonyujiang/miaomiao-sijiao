# 部署验证：SSH 到服务器，打印主机信息 + 关键代码版本证据
$ErrorActionPreference = 'Stop'

$creds = Get-Content (Join-Path $PSScriptRoot '.ssh-credentials.json') -Raw | ConvertFrom-Json
$remote = "$($creds.username)@$($creds.host)"
$sshCommon = @('-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null')

$escapedPassword = $creds.password -replace '\^', '^^' -replace '&', '^&' -replace '\|', '^|' -replace '>', '^>' -replace '<', '^<' -replace '"', '^"'
$askpass = "$env:TEMP\ssh_askpass_verify.cmd"
Set-Content -Path $askpass -Value "@echo off`necho $escapedPassword" -Encoding ASCII
$env:SSH_ASKPASS = $askpass
$env:SSH_ASKPASS_REQUIRE = 'force'
$env:DISPLAY = 'dummy'

$remoteScript = @'
hostname
date
echo "--- service ---"
systemctl is-active miaomiao.service
echo "--- backend code: new UPSERT fix ---"
grep -c "ON CONFLICT" /opt/miaomiao/server/ewa/extension/store.py
grep -n "SUBTITLE_DIR" /opt/miaomiao/server/ewa/website/repository.py | head -2
echo "--- backend files mtime ---"
ls -la --time-style=full-iso /opt/miaomiao/server/ewa/extension/store.py /opt/miaomiao/server/ewa/website/service.py /opt/miaomiao/server/scripts/fetch_subtitle.py
echo "--- frontend dist mtime ---"
ls -la --time-style=full-iso /opt/miaomiao/server/frontend/dist/index.html
'@
$remoteScript = $remoteScript -replace "`r`n", "`n"

try {
  & ssh @sshCommon $remote $remoteScript
}
finally {
  if (Test-Path $askpass) { Remove-Item $askpass -ErrorAction SilentlyContinue }
}
