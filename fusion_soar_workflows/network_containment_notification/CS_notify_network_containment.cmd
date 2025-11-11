REM Executa o Chrome em local padrão, modo quiosque e desativando opções default
REM Alterar "file:" ou "--user-data-dir" conforme necessário no seu ambiente

"C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk "file:///C:/Windows/TEMP/CS_notify_network_containment.html" --user-data-dir="C:\temp\chrome-profile" --no-first-run --no-default-browser-check --disable-first-run-ui --disable-default-apps --disable-infobars
