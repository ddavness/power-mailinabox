
# -*- mode: ruby -*-
# vi: set ft=ruby :

ip = 2
machines = [
  {
    'iso' => "debian/buster64",
    'host' => "buster"
  },
  {
    'iso' => "generic/ubuntu2004",
    'host' => "focal"
  },
  {
    'iso' => "debian/bullseye64",
    'host' => "bullseye"
  },
	{
    'iso' => "generic/ubuntu2204",
    'host' => "jammy"
  },
]

Vagrant.configure("2") do |config|
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--cpus", 1, "--memory", 512]
  end
  config.vm.provider :libvirt do |v|
    v.memory = 512
    v.cpus = 1
    v.nested = true
  end
  config.vm.provider :kvm do |kvm|
    kvm.memory_size = '512m'
  end

  # Network config: Since it's a mail server, the machine must be connected
  # to the public web. However, we currently don't want to expose SSH since
  # the machine's box will let anyone log into it. So instead we'll put the
  # machine on a private network.
  config.vm.synced_folder ".", "/vagrant", nfs_version: "4"

  (0..(machines.size - 1)).each do |n|
    node = machines[n]
    config.vm.define node['host'] do |m|
      m.vm.box = node['iso']
      m.vm.hostname = "#{node['host']}.mailinabox.lan"
      m.vm.network "private_network", ip: "192.168.168.#{ip+n}"

      m.vm.provision "shell", :inline => <<-SH
        # Make sure we have IPv6 loopback (::1)
        sysctl -w net.ipv6.conf.lo.disable_ipv6=0
        echo -e "fs.inotify.max_user_instances=1024\nnet.ipv6.conf.lo.disable_ipv6=0" > /etc/sysctl.conf
        # Set environment variables so that the setup script does
        # not ask any questions during provisioning. We'll let the
        # machine figure out its own public IP.
        export NONINTERACTIVE=1
        export PUBLIC_IP=192.168.168.#{ip+n}
        export PUBLIC_IPV6=auto
        export PRIVATE_IP=192.168.168.#{ip+n}
        export PRIMARY_HOSTNAME=\"#{node['host']}.mailinabox.lan\"
        export SKIP_NETWORK_CHECKS=1
        # Start the setup script.
        cd /vagrant
        setup/start.sh
        # After setup is done, fully open the ssh ports again
        ufw allow ssh
  SH

        m.vm.provision "shell", run: "always", :inline => <<-SH
          service mailinabox restart
  SH
    end
  end
end
