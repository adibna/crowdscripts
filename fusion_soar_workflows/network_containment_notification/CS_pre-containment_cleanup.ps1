# Definições dos arquivos necessários à execução do workflow
$logo = "C:\Windows\TEMP\CS_company_logo.png"
$html = "C:\Windows\TEMP\CS_notify_network_containment.html"
$script = "C:\Windows\TEMP\CS_notify_network_containment.cmd"

# Listagem dos arquivos
$files = $logo, $html, $script

# Validação e remoção caso sejam criados antes do workflow
$files | ForEach-Object {
    if ((Test-Path $PSItem) -and 
    ((Get-Item $PSItem).CreationTime -le ((Get-Date).AddMinutes(-5)))
    ) {
        Remove-Item $PSItem -Force -Verbose
    }
}
