#!/bin/bash
#########################################################
# This script is intended to be run like this:
#
#   curl -L https://power-mailinabox.net/setup.sh | sudo bash
#
#########################################################

# Are we running as root?
if [[ $EUID -ne 0 ]]; then
	echo "This script must be run as root. Did you leave out sudo?"
	exit 1
fi

if [ ! -f /usr/bin/lsb_release ]; then
	# Try installing it (apt install lsb-release)
	if [ ! -f /usr/bin/apt-get ]; then
		echo "This operating system does not have apt-get! This means it is unsupported!"
		echo "This script must be run on a system running one of the following OS-es:"
		echo "* Debian 10 (buster)"
		echo "* Debian 11 (bullseye)"
		echo "* Ubuntu 20.04 LTS (Focal Fossa)"
		echo "* Ubuntu 22.04 LTS (Jammy Jellyfish)"
		exit 1
	fi

	echo "Installing lsb-release to understand which operating system we're running..."
	apt-get -q -q update
	DEBIAN_FRONTEND=noninteractive apt-get -q -q install -y lsb-release < /dev/null
fi

if [ -z "$TAG" ]; then
	# Make sure we're running on the correct operating system
	OS=$(lsb_release -d | sed 's/.*:\s*//')
	if  [ "$OS" == "Debian GNU/Linux 11 (bullseye)" ] ||
		[ "$(echo $OS | grep -o 'Ubuntu 20.04')" == "Ubuntu 20.04" ] ||
		[ "$(echo $OS | grep -o 'Ubuntu 22.04')" == "Ubuntu 22.04" ]
	then
		TAG=v60.5
	elif [ "$OS" == "Debian GNU/Linux 10 (buster)" ]; then
		echo "We are going to install the last version of Power Mail-in-a-Box supporting Debian 10 (buster)."
		echo "IF THIS IS A NEW INSTALLATION, STOP NOW, AND USE A SUPPORTED DISTRIBUTION INSTEAD (ONE OF THESE):"
		echo "* Debian 11 (bullseye)"
		echo "* Ubuntu 20.04 LTS (Focal Fossa)"
		echo "* Ubuntu 22.04 LTS (Jammy Jellyfish)"
		echo
		echo "IF YOU'RE UPGRADING THE BOX TO THE LATEST VERSION, PLEASE VISIT THIS PAGE FOR NOTES ON HOW TO"
		echo "UPGRADE YOUR SISTEM TO DEBIAN 11 (bullseye)"
		echo "https://power-mailinabox.net/buster-eol"

		while true; do
			read -p "Do you want to proceed? ([Y]es/[N]o) " yn

			case $yn in
				Yes | Y | yes | y )
					break
					;;
				No | N | no | n )
					echo "Installation cancelled."
					exit 1
					;;
				* )
					;;
			esac
		done

		TAG=v56.5
	else
		echo "This script must be run on a system running one of the following OS-es:"
		echo "* Debian 11 (bullseye)"
		echo "* Ubuntu 20.04 LTS (Focal Fossa)"
		echo "* Ubuntu 22.04 LTS (Jammy Jellyfish)"
		exit 1
	fi
fi

# Clone the Mail-in-a-Box repository if it doesn't exist.
if [ ! -d $HOME/mailinabox ]; then
	if [ ! -f /usr/bin/git ]; then
		echo Installing git . . .
		apt-get -q -q update
		DEBIAN_FRONTEND=noninteractive apt-get -q -q install -y git < /dev/null
		echo
	fi

	echo Downloading Mail-in-a-Box $TAG. . .
	git clone \
		-b $TAG --depth 1 \
		https://github.com/ddavness/power-mailinabox \
		$HOME/mailinabox \
		< /dev/null 2> /dev/null

	echo
fi

# Change directory to it.
cd $HOME/mailinabox

# Update it.
if [ "$TAG" != "$(git describe --tags)" ]; then
	echo Updating Mail-in-a-Box to $TAG . . .
	git fetch --depth 1 --force --prune origin tag $TAG
	if ! git checkout -q $TAG; then
		echo "Update failed. Did you modify something in $(pwd)?"
		exit 1
	fi
	echo
fi

# Start setup script.
setup/start.sh

