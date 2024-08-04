#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import nmap
import socket
import ipaddress
import psutil

class NetworkDevice:
    def __init__(self, **kwargs):
        self.hostname = kwargs.get('hostname')
        self.subnet = kwargs.get('subnet')
        
        self.status = None
        self._scan_for_ip()
        
    def _scan_for_ip(self):
        self.ip = DeviceScanner().find_host(self.hostname, scan = self.subnet)
        
    def get_ip(self):
        while DeviceScanner().check_if_is_online(self.ip)==False:
            self._scan_for_ip()
            
        return self.ip


class DeviceScanner:
    def __init__(self):
        self.scanner = nmap.PortScanner()

    def _get_local_interfaces(self):
        ip_addresses = []
        # Alle Netzwerk-Schnittstellen abrufen
        for interface, addrs in psutil.net_if_addrs().items():
            if interface.startswith('br-') or interface == 'lo' or 'docker' in interface:
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:  # Nur IPv4-Adressen
                    ip_addresses.append((interface, addr.address))
        return ip_addresses

    def _clean_hostname(self, hostname):
        return '.'.join(hostname.split(".")[:-1])
            
    def find_host(self, hostname, scan=None):
        """Finds the IP address of the device with the given hostname by scanning the local network."""
        if scan == None:
            interfaces = []
        else:
            interfaces = [('config', scan)]

        try:
            interfaces.extend([(k[0], '.'.join(k[1].split('.')[:-1]) + '.0/24') for k in self._get_local_interfaces()])
            for interface, subnet in interfaces:
                print(f"Scanning the local network for the host: {hostname} on subnet {subnet}...")
                self.scanner.scan(hosts=subnet, arguments='-sn')
                for ip in self.scanner.all_hosts():
                    print(f'Scanning {self._clean_hostname(self.scanner[ip].hostname())} / {ip}')
                    if self._clean_hostname(self.scanner[ip].hostname()) == hostname:
                        return ip
        except Exception as e:
            print(f"Error scanning for host {hostname}: {e}")
        return None
    
    def check_if_is_online(self, ip):
        """Scans the device at the given IP address using a quick scan."""
        try:
            host_info = self.scan_device(ip)
            if host_info == None: return False
            return host_info.get('status', {}).get('state')=='up'
            
        except Exception as e:
            return False

    def scan_device(self, ip):
        """Scans the device at the given IP address using a quick scan."""
        try:
            self.scanner.scan(ip, arguments='-sn')
            return self.scanner[ip]
        except Exception as e:
            print(f"Error scanning {ip}: {e}")
            return None

    def get_device_info(self, ip):
        """Returns the hostname and MAC address of the device at the given IP address."""
        scan_result = self.scan_device(ip)
        if scan_result:
            device_info = {
                'hostname': scan_result.hostname().rstrip('.'),
            }
            return device_info
        return None

# Beispiel der Verwendung
if __name__ == "__main__":
    pass

    self = NetworkDevice(hostname='DCS-932LB')

    # self = DeviceScanner()
    # ip_address = "192.168.1.214"
    # device_info = self.get_device_info(ip_address)
    
    # self.find_host('DCS-932LB')

