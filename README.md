# Power Mail-in-a-Box
**[Installation](#installation)** (current version: v60.2)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/davness)

Power Mail-in-a-Box (a fork of [Mail-in-a-Box](https://mailinabox.email/)) is a complete pre-configured mail appliance, quickly deployable in a matter of minutes.

It's main difference to the main project is focused on ad-hoc, advanced features. While Mail-in-a-Box caters to beginners by providing sane configurations, Power Mail-in-a-Box also attempts to cater to advanced users that want deeper levels of customization.

## Features
- Configure Power Mail-in-a-Box to use an external SMTP relay;
- Brand new admin panel (with up-to-date libraries);
- Perform backups right away from the admin panel;
- Account quotas support (thanks to **@[jrsupplee](https://github.com/jrsupplee/mailinabox)**!)
- Customize TTL's for custom DNS records;
- Publish OpenPGP keys authoritatively via a WKD server;
- - **In the future:** Allow usage of OpenPGP keys to encrypt backups;
- Per-domain nginx configuration;

## Goals
- **Easy of use** - deployment shouldn't take too many technical details to understand. Power Mail-in-a-Box already comes with default configurations which should be good for most users.
- **Privacy, security and independence** - keeping your mail and data safe from advertisers and prying eyes.
- **Accessible customizability** - bring the features closer to the people instead of tucking them away in configuration files.
- **Customizability potential** - allow for deep customization by power users.
- **Concentration** - all the services you need in just one box.
- **Support** - support a wide range of operating systems when possible, without compromising the codebase as a whole.
- **Lightweight** - should be able to run even with very limited resources.

## Non-goals
- **Scalability** - this appliance is geared towards individuals and small/mid-sized organizations. If your use case is mission-critical it probably is a better idea to shop for a product that provides support.
- **Portability** - I didn't figure out yet a way to easily transition from Mail-in-a-Box to Power Mail-in-a-Box.

# Minimum Pre-requisites
The machine this appliance will be installed on needs to have the following specs (or better). Most cloud providers are able to provide VM's that satisfy these specs at relatively low cost.

<small>_These specs depend on the number of users being served and/or amount of traffic_</small>
- 1 CPU core;
- 512MB of RAM (**at least 1GB** is recommended);
- 10GB of disk;
- **One of the following operating systems:**
- - Debian GNU/Linux 11 (Bullseye)
- - Ubuntu LTS 20.04 (Focal Fossa)
- - Ubuntu LTS 22.04 (Jammy Jellyfish)

## Legacy Support
The following distributions are no longer supported for the latest version, but they used to be supported at a earlier time:
- **Debian 10 (Buster)** <= **v56.5**

<small>_These network requirements are usually not provided by residential ISP's. They are not **strictly required** for Power Mail-in-a-Box to install, but it will take more work to get it running as intended._</small>
- Static, public IPv4 (most residential connections **do not** provide static addresses);
- - If the machine is behind a NAT, manual configuration might be required.
- Reverse DNS for that IPv4 address (**Caution:** some cloud providers do not provide this);
- You should be able to edit the firewall for that address. **In particular, outbound port 25 should not be blocked.**

# Firewall
If the machine is behind an external firewall or NAT, the following **inbound ports SHOULD** be open to external traffic:

- `25/tcp`
- `53/tcp`
- `53/udp`
- `80/tcp`
- `443/tcp`
- `465/tcp`
- `587/tcp`
- `993/tcp`
- `995/tcp`
- `4190/tcp`

# Installation

1. Power Mail-in-a-Box uses `ufw` to configure it's internal firewall. If your cloud provider requires you to use another tool (usually it does not, but <small>\*cough\* _Oracle Cloud_ \*cough\*</small>), you can follow [these instructions](https://github.com/ddavness/power-mailinabox/discussions/21).

2. Make sure `curl` is installed and locales are configured correctly - you'll want to make sure the primary locale is set to `en_US.UTF-8`:
```
sudo apt install curl locales
sudo dpkg-reconfigure locales
```

3. Run the following command, and then follow the instructions that appear on the screen:
```
curl -L https://power-mailinabox.net/setup.sh | sudo bash
```
