source /etc/mailinabox.conf
source setup/functions.sh # load our functions

echo Removing packages for LXC...
apt_remove ntp systemd-timesyncd
