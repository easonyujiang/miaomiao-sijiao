# 线上实测：生产环境妙喵聊天接口
$ErrorActionPreference = 'Stop'
$base = 'http://8.130.190.169:8000'

function Test-Chat($label, $body) {
  Write-Host "`n=== $label ===" -ForegroundColor Cyan
  $json = $body | ConvertTo-Json -Compress
  $tmpIn = "$env:TEMP\chat_payload.json"
  $tmpOut = "$env:TEMP\chat_response.json"
  [System.IO.File]::WriteAllText($tmpIn, $json, [System.Text.UTF8Encoding]::new($false))
  curl.exe -s -X POST "$base/api/site/ashley/chat" -H "Content-Type: application/json" --data-binary "@$tmpIn" --max-time 60 -o $tmpOut
  $resp = [System.IO.File]::ReadAllText($tmpOut, [System.Text.UTF8Encoding]::new($false))
  Remove-Item $tmpIn, $tmpOut -ErrorAction SilentlyContinue
  $obj = $resp | ConvertFrom-Json
  Write-Host "intent: $($obj.intent)"
  Write-Host "answer: $($obj.answer)"
  if ($obj.actions) {
    Write-Host "actions:"
    $obj.actions | ForEach-Object { Write-Host "  - [$($_.type)] $($_.label)" }
  }
}

# 1. 此前出错的问题：应走 video_query，摘要只基于字幕、带真实时间戳
Test-Chat '罗翔的正当防卫视频你有什么看法？' @{ message = '罗翔的正当防卫视频你有什么看法？' }

# 2. 带当前视频上下文：应直接总结当前视频
Test-Chat '这个视频讲了什么（带 video_id 上下文）' @{ message = '这个视频讲了什么'; video_id = 'BV1mJ4m147PG'; current_time_ms = 30000 }

# 3. 日记意图不应被意图分类破坏
Test-Chat '博主最近在做什么？' @{ message = '博主最近在做什么？' }

# 4. 社区讨论检索：应返回 open_topic 跳转按钮
Test-Chat '有没有关于正当防卫的讨论？' @{ message = '有没有关于正当防卫的讨论？' }
