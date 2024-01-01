# Photo Display for Raspberry Pi

## Setup OS

### 1. Setup Raspberry Pi
If you use Raspberry Pi image can setup WiFi and root user, otherwise that needs to be done separately.

Needs Raspberry Pi OS including desktop environment.

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
System user (cannot be logged into) which stores the relevant files and is used to run the program.

```bash
sudo useradd --system --comment "User for the photo display program" --no-create-home photoframe
sudo mkdir -p /var/photoframe
sudo chown photoframe:photoframe /var/photoframe
sudo chmod a-rwx,g+rx,u+rwx /var/photoframe
```

Install the sudoers file to allow the `photoframe` user to perform operations like shutdown and reboot.
```bash
sudo cp install/sudoer.photoframe /etc/sudoers.d/photoframe
sudo chown root:root /etc/sudoers.d/photoframe
```

### 5. Setup Login User
Login user that the GUI runs in.

```bash
sudo useradd --comment "Auto login user for the photo display program" --create-home photologin
sudo passwd photologin
sudo raspi-config nonint do_boot_behaviour B4
sudo raspi-config nonint do_blanking 1
```

Modify the `/etc/lightdm/lightdm.conf`:
- `autologin-user=photologin`
  - Change auto login user to `photologin`
  - (Taken from `raspi-config` script)
- `xserver-command=X -nocursor`
  - Disable cursor

## Setup Program

### Install Dependencies
This only supports Python 3.10+ (`UPDATE..RETURNING` is only supported in SQLite 3.35.0+).

```bash
# Required for GUI
sudo apt install python3-tk
```

### Misc:

- [Screen](https://thepihut.com/products/10-1inch-capacitive-touch-display)
- [Wiki](https://www.waveshare.com/wiki/10.1DP-CAPLCD)
