param(
  [string]$HostName = "192.168.1.65",
  [string]$UserName = "admin",
  [string]$RemoteDir = "~/Clock"
)

scp -r `
  assets `
  uploads `
  app.js `
  cities.json `
  clock_state.json `
  index.html `
  manage.html `
  manage.js `
  native_display.py `
  README-pi.md `
  requirements.txt `
  server.py `
  start-clock-browser.sh `
  clock-web.service `
  "${UserName}@${HostName}:${RemoteDir}"
