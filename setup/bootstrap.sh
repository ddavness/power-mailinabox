#!/bin/bash
#########################################################
# This script is intended to be run like this:
#
#   curl https://dvn.pt/power-miab | sudo bash
#
#########################################################

if [ -z "$TAG" ]; then
	OS=`lsb_release -d | sed 's/.*:\s*//'`
	if [ "$OS" == "Debian GNU/Linux 10 (buster)" -o "$(echo $OS | grep -o 'Ubuntu 20.04')" == "Ubuntu 20.04" ]; then
		TAG=v0.53.POWER.1
	else
fi

# Change directory to it.
cd $HOME/mailinabox

# Update it.
if [ "$TAG" != "`git describe --tags`" ]; then
	echo Updating Mail-in-a-Box to $TAG . . .
	git fetch --depth 1 --force --prune origin tag $TAG
	if ! git checkout -q $TAG; then
		echo "Update failed. Did you modify something in `pwd`?"
		exit 1
	fi
	echo
fi

# Start setup script.
setup/start.sh

