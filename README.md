# Snekframe
Python powered digital photo frame software (for Raspberry Pi).

## Setup OS

### 1. Setup Raspberry Pi
If you use Raspberry Pi image can setup WiFi and root user, otherwise that needs to be done separately.

Needs Raspberry Pi OS including desktop environment.


#### Disable Bluetooth
Not required currently so can close this by modifying `/boot/config.txt`:
```
# Disable bluetooth
dtoverlay=disable-bt
```

Need to disable the service that initialises the model so it doesn't connect to UART
(see [raspberry pi documentation](https://www.raspberrypi.com/documentation/computers/configuration.html#uarts-and-device-tree)).
```
# This configures bluetooth modems connected by UART
sudo systemctl disable hciuart
```
Can also disable bluetooth service because it's unnecessary
```
sudo systemctl disable bluetooth
```

#### Disable LX Panel and Desktop
This isn't visible to users because the program takes the entire screen.
It also can have pop-ups which could appear over the program.

We also switch off the desktop because its hidden under the application.
Even if the desktop crashes an empty desktop doesn't provide any useful functionality.

If the power supply isn't sufficient (under-voltage warning) the notification that would usually appear on the taskbar will appear on the title bar of the application.

To disable these, edit `/etc/xdg/lxsession/LXDE-pi/autostart`
```
#@lxpanel --profile LXDE-pi
#@pcmanfm --desktop --profile LXDE-pi
```

### 2. Setup Root User
Normal root user setup (dotfiles, etc.).

Setup firewall and `sshd_config` as desired. Suggested:
```bash
sudo apt install ufw
sudo ufw allow SSH
sudo ufw enable
```

Can also login to WiFi at this stage if already have network credentials (but can also do this later).
Use `sudo raspi-config`.

Raspberry Pi by default makes the first user login automatically and doesn't require password for sudo.
To fix this, delete default sudoers no password file:
```bash
sudo rm /etc/sudoers.d/010_pi-nopasswd
```

Can also comment out `@includedir /etc/sudoers.d` in `/etc/sudoers` if desired (can use `visudo` to edit).
This shouldn't be done if using the sudoers permission file in the next step.

### 3. Setup Automated Upgrades
Using `unattended-upgrades` can automatically upgrade the device with security upgrades.

```bash
sudo apt install unattended-upgrades apt-listchanges
```

To email info about package upgrades, need `mailx`.
```bash
sudo apt install mailutils # Required for updates to be emailed
```

Once installed, update `/etc/apt/apt.conf.d/50unattended-upgrades`:
- `Unattended-Upgrade::Mail "root";`
  - Need to have installed `mailx`
  - `root` can be replaced with an external email with the necessary configuration.
- `Unattended-Upgrade::Automatic-Reboot "true";`
  - Will reboot if required after upgrade
- `Unattended-Upgrade::Automatic-Reboot-Time "03:00";`
  - Time reboot will occur (if required) after packages are installed

Update `/etc/apt/apt.conf.d/20auto-upgrades`:
- `APT::Periodic::Unattended-Upgrade "1";`
  - Upgrade is performed daily

To adjust timing of updates:
```bash
sudo systemctl edit apt-daily.timer
```

Personally I leave this unchanged, updates shouldn't affect performance.

To adjust timing of upgrades:
```bash
sudo systemctl edit apt-daily-upgrade.timer
```

Add the following section:
```systemd.timer
[Timer]
OnCalendar=
OnCalendar=*-*-* 2:00
RandomizedDelaySec=30m
```

- First `OnCalender` resets the expression
- Second `OnCalendar` sets upgrade to 2am (an hour before reboot time)
- `RandomizedDelaySec` allows some randomness when upgrade starts, should still be enough time to finish before reboot check

Can review this has been successfully applied with `sudo systemctl list-timers apt-daily-upgrade`.

### 4. Setup Program User
User with autologin, this stores relevant files and is used to run the program.
- `video` group allows the user to access the `vcgencmd` utility
- `i2c` group allows the user to access the i2c bus for the `ddcutil` utility

```bash
sudo useradd --comment "Photo display program" --create-home snekframe --groups video,i2c
sudo passwd snekframe
# Boot into autologin user (we specify the user to login to below)
sudo raspi-config nonint do_boot_behaviour B4
# Disable screen sleeping
sudo raspi-config nonint do_blanking 1
```

Install the sudoers file to allow the `snekframe` user to perform operations like shutdown and reboot.
```bash
sudo cp install/sudoer.snekframe /etc/sudoers.d/snekframe
sudo chown root:root /etc/sudoers.d/snekframe
```

Can block others from SSHing into the program user, it only needs to be used in person.
To do this modify `/etc/ssh/sshd_config`
```sshd_config
DenyUsers snekframe
```

Modify the `/etc/lightdm/lightdm.conf`:
- `autologin-user=snekframe`
  - Change auto login user to `snekframe`
  - (Taken from `raspi-config` script)
- `xserver-command=X -nocursor`
  - Disable cursor

## Setup Program

### Install Dependencies
This only supports Python 3.10+ (`UPDATE..RETURNING` is only supported in SQLite 3.35.0+).

```bash
# Required for GUI
sudo apt install python3-tk
# Required for images
sudo apt install libcairo2-dev
```

### Install Program
Install the program in the user area (while logged into the `snekframe` user).

```bash
su - snekframe
mkdir -p /home/snekframe/.snekframe
python3 -m venv /home/snekframe/.snekframe/env
source /home/snekframe/.snekframe/env/bin/activate
# Get repo version to be installed
pip install ./snekframe
```

### Setup Autolaunch GUI
This will be launched by systemd, copy the file from install directory into user area.

```bash
cp install/snekframe.service /etc/systemd/system/snekframe.service
sudo systemctl enable snekframe.service
```

## Misc:

- [Screen](https://thepihut.com/products/10-1inch-capacitive-touch-display)
- [Wiki](https://www.waveshare.com/wiki/10.1DP-CAPLCD)
