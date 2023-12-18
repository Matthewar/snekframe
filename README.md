# Photo Display for Raspberry Pi

## Setup OS

### 1. Setup Raspberry Pi
If you use Raspberry Pi image can setup WiFi and root user, otherwise that needs to be done separately.

Needs Raspberry Pi OS including desktop environment.

### 2. Setup Root User
Normal root user setup (dotfiles, etc.).

Require password for sudo

Setup firewall
- sudo apt install ufw
- sudo ufw allow SSH
- sudo ufw enable

## Setup Program

### Install Dependencies
```bash
sudo apt install python3-tk
sudo apt install jq
```

### Misc:

- [Screen](https://thepihut.com/products/10-1inch-capacitive-touch-display)
- [Wiki](https://www.waveshare.com/wiki/10.1DP-CAPLCD)
