community.general.proxmox module – Management of instances in Proxmox VE cluster
Note

This module is part of the community.general collection (version 10.3.0).

You might already have this collection installed if you are using the ansible package. It is not included in ansible-core. To check whether it is installed, run ansible-galaxy collection list.

To install it, use: ansible-galaxy collection install community.general. You need further requirements to be able to use this module, see Requirements for details.

To use it in a playbook, specify: community.general.proxmox.

Synopsis

Requirements

Parameters

Attributes

See Also

Examples

Synopsis
Allows you to create/delete/stop instances in Proxmox VE cluster.

The module automatically detects containerization type (lxc for PVE 4, openvz for older).

Since community.general 4.0.0 on, there are no more default values.

Requirements
The below requirements are needed on the host that executes this module.

proxmoxer

requests

Parameters
Parameter

Comments

api_host 
string / required

Specify the target host of the Proxmox VE cluster.

api_password 
string

Specify the password to authenticate with.

You can use PROXMOX_PASSWORD environment variable.

api_port 
integer

added in community.general 9.1.0

Specify the target port of the Proxmox VE cluster.

Uses the PROXMOX_PORT environment variable if not specified.

api_token_id 
string

added in community.general 1.3.0

Specify the token ID.

Requires proxmoxer>=1.1.0 to work.

api_token_secret 
string

added in community.general 1.3.0

Specify the token secret.

Requires proxmoxer>=1.1.0 to work.

api_user 
string / required

Specify the user to authenticate with.

clone 
integer

added in community.general 4.3.0

ID of the container to be cloned.

description, hostname, and pool will be copied from the cloned container if not specified.

The type of clone created is defined by the clone_type parameter.

This operator is only supported for Proxmox clusters that use LXC containerization (PVE version >= 4).

clone_type 
string

added in community.general 4.3.0

Type of the clone created.

full creates a full clone, and storage must be specified.

linked creates a linked clone, and the cloned container must be a template container.

opportunistic creates a linked clone if the cloned container is a template container, and a full clone if not. storage may be specified, if not it will fall back to the default.

Choices:

"full"

"linked"

"opportunistic" ← (default)

cores 
integer

Specify number of cores per socket.

cpus 
integer

Number of allocated cpus for instance.

cpuunits 
integer

CPU weight for a VM.

description 
string

added in community.general 0.2.0

Specify the description for the container. Only used on the configuration web interface.

This is saved as a comment inside the configuration file.

disk 
string

This option was previously described as “hard disk size in GB for instance” however several formats describing a lxc mount are permitted.

Older versions of Proxmox will accept a numeric value for size using the storage parameter to automatically choose which storage to allocate from, however new versions enforce the <STORAGE>:<SIZE> syntax.

Additional options are available by using some combination of the following key-value pairs as a comma-delimited list [volume=]<volume> [,acl=<1|0>] [,mountoptions=<opt[;opt...] [,quota=<1|0>] [,replicate=<1|0>] [,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>].

See https://pve.proxmox.com/wiki/Linux_Container for a full description.

This option is mutually exclusive with disk_volume.

disk_volume 
dictionary

added in community.general 9.2.0

Specify a hash/dictionary of the rootfs disk.

See https://pve.proxmox.com/wiki/Linux_Container#pct_mount_points for a full description.

This option is mutually exclusive with storage and disk.

host_path 
path

disk_volume.host_path defines a bind or device path on the PVE host to use for the rootfs.

Mutually exclusive with disk_volume.storage, disk_volume.volume, and disk_volume.size.

options 
dictionary

disk_volume.options is a dict of extra options.

The value of any given option must be a string, for example "1".

size 
integer

disk_volume.size is the size of the storage to use.

The size is given in GiB.

Required only if disk_volume.storage is defined, and mutually exclusive with disk_volume.host_path.

storage 
string

disk_volume.storage is the storage identifier of the storage to use for the rootfs.

Mutually exclusive with disk_volume.host_path.

volume 
string

disk_volume.volume is the name of an existing volume.

If not defined, the module will check if one exists. If not, a new volume will be created.

If defined, the volume must exist under that name.

Required only if disk_volume.storage is defined, and mutually exclusive with disk_volume.host_path.

features 
list / elements=string

added in community.general 2.0.0

Specifies a list of features to be enabled. For valid options, see https://pve.proxmox.com/wiki/Linux_Container#pct_options.

Some features require the use of a privileged container.

force 
boolean

Forcing operations.

Can be used only with states present, stopped, restarted.

With state=present force option allow to overwrite existing container.

With states stopped, restarted allow to force stop instance.

Choices:

false ← (default)

true

hookscript 
string

added in community.general 0.2.0

Script that will be executed during various steps in the containers lifetime.

hostname 
string

The instance hostname.

Required only for state=present.

Must be unique if vmid is not passed.

ip_address 
string

Specifies the address the container will be assigned.

memory 
integer

Memory size in MB for instance.

mount_volumes 
list / elements=dictionary

added in community.general 9.2.0

Specify additional mounts (separate disks) for the container. As a hash/dictionary defining mount points.

See https://pve.proxmox.com/wiki/Linux_Container#pct_mount_points for a full description.

This Option is mutually exclusive with mounts.

host_path 
path

mount_volumes[].host_path defines a bind or device path on the PVE host to use for the rootfs.

Mutually exclusive with mount_volumes[].storage, mount_volumes[].volume, and mount_volumes[].size.

id 
string / required

mount_volumes[].id is the identifier of the mount point written as mp[n].

mountpoint 
path / required

mount_volumes[].mountpoint is the mount point of the volume.

options 
dictionary

mount_volumes[].options is a dict of extra options.

The value of any given option must be a string, for example "1".

size 
integer

mount_volumes[].size is the size of the storage to use.

The size is given in GiB.

Required only if mount_volumes[].storage is defined and mutually exclusive with mount_volumes[].host_path.

storage 
string

mount_volumes[].storage is the storage identifier of the storage to use.

Mutually exclusive with mount_volumes[].host_path.

volume 
string

mount_volumes[].volume is the name of an existing volume.

If not defined, the module will check if one exists. If not, a new volume will be created.

If defined, the volume must exist under that name.

Required only if mount_volumes[].storage is defined and mutually exclusive with mount_volumes[].host_path.

mounts 
dictionary

Specifies additional mounts (separate disks) for the container. As a hash/dictionary defining mount points as strings.

This Option is mutually exclusive with mount_volumes.

nameserver 
string

Sets DNS server IP address for a container.

netif 
dictionary

Specifies network interfaces for the container. As a hash/dictionary defining interfaces.

node 
string

Proxmox VE node on which to operate.

Only required for state=present.

For every other states it will be autodiscovered.

onboot 
boolean

Specifies whether a VM will be started during system bootup.

Choices:

false

true

ostemplate 
string

The template for VM creating.

Required only for state=present.

ostype 
string

added in community.general 8.1.0

Specifies the ostype of the LXC container.

If set to auto, no ostype will be provided on instance creation.

Choices:

"auto" ← (default)

"debian"

"devuan"

"ubuntu"

"centos"

"fedora"

"opensuse"

"archlinux"

"alpine"

"gentoo"

"nixos"

"unmanaged"

password 
string

The instance root password.

pool 
string

Add the new VM to the specified pool.

pubkey 
string

Public key to add to /root/.ssh/authorized_keys. This was added on Proxmox 4.2, it is ignored for earlier versions.

purge 
boolean

added in community.general 2.3.0

Remove container from all related configurations.

For example backup jobs, replication jobs, or HA.

Related ACLs and Firewall entries will always be removed.

Used with state=absent.

Choices:

false ← (default)

true

searchdomain 
string

Sets DNS search domain for a container.

startup 
list / elements=string

added in community.general 8.5.0

Specifies the startup order of the container.

Use order=# where # is a non-negative number to define the general startup order. Shutdown in done with reverse ordering.

Use up=# where # is in seconds, to specify a delay to wait before the next VM is started.

Use down=# where # is in seconds, to specify a delay to wait before the next VM is stopped.

state 
string

Indicate desired state of the instance.

template was added in community.general 8.1.0.

Choices:

"present" ← (default)

"started"

"absent"

"stopped"

"restarted"

"template"

storage 
string

Target storage.

This option is mutually exclusive with disk_volume and mount_volumes.

Default: "local"

swap 
integer

Swap memory size in MB for instance.

tags 
list / elements=string

added in community.general 6.2.0

List of tags to apply to the container.

Tags must start with [a-z0-9_] followed by zero or more of the following characters [a-z0-9_-+.].

Tags are only available in Proxmox 7+.

timeout 
integer

Timeout for operations.

Default: 30

timezone 
string

added in community.general 7.1.0

Timezone used by the container, accepts values like Europe/Paris.

The special value host configures the same timezone used by Proxmox host.

unprivileged 
boolean

Indicate if the container should be unprivileged.

The default change to true in community.general 7.0.0. It used to be false before.

Choices:

false

true ← (default)

update 
boolean

added in community.general 8.1.0

If true, the container will be updated with new values.

The current default value of false is deprecated and should will change to true in community.general 11.0.0. Please set update explicitly to false or true to avoid surprises and get rid of the deprecation warning.

Choices:

false

true

validate_certs 
boolean

If false, SSL certificates will not be validated.

This should only be used on personally controlled sites using self-signed certificates.

Choices:

false ← (default)

true

vmid 
integer

Specifies the instance ID.

If not set the next available ID will be fetched from ProxmoxAPI.

Attributes
Attribute

Support

Description

action_group 
Action group: community.general.proxmox

added in community.general 9.0.0

Use group/community.general.proxmox in module_defaults to set defaults for this module.

check_mode 
none

Can run in check_mode and return changed status prediction without modifying target.

diff_mode 
none

Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.

See Also
See also

community.general.proxmox_vm_info
Retrieve information about one or more Proxmox VE virtual machines.

Examples
- name: Create new container with minimal options
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'

- name: Create new container with minimal options specifying disk storage location and size
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    disk: 'local-lvm:20'

- name: Create new container with minimal options specifying disk storage location and size via disk_volume
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    disk_volume:
      storage: local
      size: 20

- name: Create new container with hookscript and description
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    hookscript: 'local:snippets/vm_hook.sh'
    description: created with ansible

- name: Create new container automatically selecting the next available vmid.
  community.general.proxmox:
    node: 'uk-mc02'
    api_user: 'root@pam'
    api_password: '1q2w3e'
    api_host: 'node1'
    password: '123456'
    hostname: 'example.org'
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'

- name: Create new container with minimal options with force(it will rewrite existing container)
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    force: true

- name: Create new container with minimal options use environment PROXMOX_PASSWORD variable(you should export it before)
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'

- name: Create new container with minimal options defining network interface with dhcp
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    netif:
      net0: "name=eth0,ip=dhcp,ip6=dhcp,bridge=vmbr0"

- name: Create new container with minimal options defining network interface with static ip
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    netif:
      net0: "name=eth0,gw=192.168.0.1,ip=192.168.0.2/24,bridge=vmbr0"

- name: Create new container with more options defining network interface with static ip4 and ip6 with vlan-tag and mtu
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    netif:
      net0: "name=eth0,gw=192.168.0.1,ip=192.168.0.2/24,ip6=fe80::1227/64,gw6=fe80::1,bridge=vmbr0,firewall=1,tag=934,mtu=1500"

- name: Create new container with minimal options defining a mount with 8GB
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    mounts:
      mp0: "local:8,mp=/mnt/test/"

- name: Create new container with minimal options defining a mount with 8GB using mount_volumes
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    mount_volumes:
      - id: mp0
        storage: local
        size: 8
        mountpoint: /mnt/test

- name: Create new container with minimal options defining a cpu core limit
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    cores: 2

- name: Create new container with minimal options and same timezone as proxmox host
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    timezone: host

- name: Create a new container with nesting enabled and allows the use of CIFS/NFS inside the container.
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    password: 123456
    hostname: example.org
    ostemplate: 'local:vztmpl/ubuntu-14.04-x86_64.tar.gz'
    features:
      - nesting=1
      - mount=cifs,nfs

- name: >
    Create a linked clone of the template container with id 100. The newly created container with be a
    linked clone, because no storage parameter is defined
  community.general.proxmox:
    vmid: 201
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    clone: 100
    hostname: clone.example.org

- name: Create a full clone of the container with id 100
  community.general.proxmox:
    vmid: 201
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    clone: 100
    hostname: clone.example.org
    storage: local

- name: Update container configuration
  community.general.proxmox:
    vmid: 100
    node: uk-mc02
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    netif:
      net0: "name=eth0,gw=192.168.0.1,ip=192.168.0.3/24,bridge=vmbr0"
    update: true

- name: Start container
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: started

- name: >
    Start container with mount. You should enter a 90-second timeout because servers
    with additional disks take longer to boot
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: started
    timeout: 90

- name: Stop container
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: stopped

- name: Stop container with force
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    force: true
    state: stopped

- name: Restart container(stopped or mounted container you can't restart)
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: restarted

- name: Convert container to template
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: template

- name: Convert container to template (stop container if running)
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: template
    force: true

- name: Remove container
  community.general.proxmox:
    vmid: 100
    api_user: root@pam
    api_password: 1q2w3e
    api_host: node1
    state: absent