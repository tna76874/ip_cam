#!/bin/bash
SCRIPT=$(readlink -f "$0")
DIR=$(dirname "$SCRIPT")

cleanup() {
    for (( i=0; i<15; ++i)); do
        sudo killall lnxrouter > /dev/null 2>&1
        done
}


openap_cam() {
ssid=${1:-"wlan-hotspot"}
pw=${2:-$(pwgen 8 1)}
QRCODE="WIFI:S:$ssid;T:WPA;P:$pw;;"
qrencode -t ANSIUTF8 "$QRCODE"
echo -e "SSID:     $ssid \nPASSWORT: $pw\n"
inetdev=$(route | grep '^default' | grep -o '[^ ]*$' | head -n 1)

sudo rfkill unblock wifi
sudo rfkill unblock all

if [ -z "$inetdev" ]
then
      apdev=$(iw dev | awk '$1=="Interface"{print $2}' | grep -F 'w' | head -n 1)
      echo "Opening offline AP. [$apdev]"
      sudo "$DIR"/lnxrouter --no-virt --qr -n --ap $apdev $ssid -p $pw
else
      apdev=$(iw dev | awk '$1=="Interface"{print $2}' | grep -v "$inetdev" | grep -F 'w' | head -n 1)
      echo "Opening link to internet. [$apdev $inetdev]"
      sudo "$DIR"/lnxrouter --no-virt --qr --ap $apdev $ssid -p $pw
fi
}


# Standardwerte für die Parameter
SSID=""
PASSWORD=""

# Optionale Argumente verarbeiten
while getopts "s:p:" opt; do
  case $opt in
    s)
      SSID="$OPTARG"
      ;;
    p)
      PASSWORD="$OPTARG"
      ;;
    \?)
      echo "Ungültige Option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Überprüfen, ob beide Parameter gesetzt sind
if [ -z "$SSID" ] || [ -z "$PASSWORD" ]; then
  echo "Fehler: Sowohl SSID als auch PASSWORD müssen angegeben werden." >&2
  echo "Verwendung: $0 -s <SSID> -p <PASSWORD>"
  exit 1
fi

trap cleanup EXIT

openap_cam ${SSID} ${PASSWORD}

cleanup

trap "" EXIT