#!/bin/bash
SCRIPT=$(readlink -f "$0")
DIR=$(dirname "$SCRIPT")

cleanup() {
    for (( i=0; i<15; ++i)); do
        sudo killall lnxrouter > /dev/null 2>&1
        sudo killall python3 > /dev/null 2>&1
    done
}

function open_ap_cam() {
ssid=${1:-"wlan-hotspot"}
pw=${2:-$(pwgen 8 1)}
QRCODE="WIFI:S:$ssid;T:WPA;P:$pw;;"
qrencode -t ANSIUTF8 "$QRCODE"
echo -e "SSID:     $ssid \nPASSWORT: $pw\n"
inetdev=$(route | grep '^default' | grep -o '[^ ]*$' | head -n 1)

sudo rfkill unblock wifi
sudo rfkill unblock all


apdev=$(iw dev | awk '$1=="Interface"{print $2}' | grep -F 'w' | head -n 1)
echo "Opening offline AP. [$apdev]"
sudo "$DIR"/lnxrouter --no-virt -g 5 --qr -n --ap $apdev $ssid  -p $pw > /dev/null 2>&1

if [ -z "$inetdev" ]
then
      apdev=$(iw dev | awk '$1=="Interface"{print $2}' | grep -F 'w' | head -n 1)
      echo "Opening offline AP. [$apdev]"
else
      apdev=$(iw dev | awk '$1=="Interface"{print $2}' | grep -v "$inetdev" | grep -F 'w' | head -n 1)
      echo "Opening link to internet. [$apdev $inetdev]"
fi
sudo "$DIR"/lnxrouter --no-virt -g 5 --qr -n --ap $apdev $ssid -p $pw > /dev/null 2>&1

}

sudo echo "Opening access point and starting tracking"

cd "$DIR"

trap cleanup EXIT

# open access point
(open_ap_cam 'SLH-ALERT' '0943vun490mbt6wdf' > /dev/null 2>&1) &

sleep 5

# ("$DIR"/motionalert.py > /dev/null 2>&1) &

"$DIR"/motionalert.py

echo -e "\n\n"

# wait until tunnel gets closed
read -r -p "Type ENTER to exit" response

# run cleanup
cleanup
sleep 2

# delete trap
trap "" EXIT