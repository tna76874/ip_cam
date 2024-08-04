sudo apt update
sudo apt upgrade -y

sudo apt install -y hostapd iw haveged iproute2 dnsmasq iptables pwgen libatlas-base-dev nmap

wget https://raw.githubusercontent.com/garywill/linux-router/master/lnxrouter

chmod +x lnxrouter
