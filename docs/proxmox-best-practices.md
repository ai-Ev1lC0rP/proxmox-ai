I usually recommend putting all your network ports into a Bond and making that bond be the bridge. Instead of just a single network connection.

When making VMs, use HOST as the CPU type. The default is safe and compatible with a lot of older systems. HOST allows the VMs to use all the CPUs features. Which, in your case, is probably a very good idea.

For the Proxmox install, I usually install it to a small SSD (small to me is like 128GB) and then make a RAID1 out of 2 SSDs and use that for the VMs OS drives. Then for extra storage I use some HDDs in a use case appropriate RAID, then use that storage as a secondary drive to add space to VMs. As needed.

keep an eye on "df -i" and "df -h" free space and inode usage can bite you if not watched.

turn off "ballooning mem usage"

set processor type to HOST for vm's

periodically remove the junk that builds up under samba/msg.sock folder



Your question is mostly storage focused. Connect your storage over 10Gbit fiber, use multiple paths. Make sure your HBAs are compatible and you SFPs and your switches. Don’t use spinning disks, use SSD or NVME at the very least. The mechanical disks will be brutal to wait on if you decide to increase VM density. This is less of a proxmox design concern and more off a VDI in general design concern. Proxmox is no different than any other hypervisor at the end of the day. The same thing you’d do for VMware or Xen or HyperV, is what you should do for Proxmox. I have lots of experience with the SAS10k versus SSD. The SAS10k are not worth the price versus going with SSD. Just compare IOPS for example.



My advice would be to think carefully about your storage and backup. I've got a medium sized cluster running VMs and containers with VHDs on the NFS - this is great for shared storage - if I want to move a host I just stop it and start it elsewhere (this is a lot quicker than migrating a running machine - but Proxmox lets me do that too) however when running backups (using the PVE backup facility) the hosts can pause/lose connectivity in the middle. That's not a problem as I'm only running test and dev machines there currently - but would be a concern if I wanted 24x7 availability.

Hardware RAID is BAD. Particularly when you buy it from one of the big vendors. If you intend to keep your hardware under warranty for its lifetime, then hardware raid is a simple solution. But I for one am appalled at the poor quality of support HPE offer and my experience is that paying a premium for the hardware and warranty is money wasted. Also bear in mind that more boxes is better than bigger boxes. Unless you want to spend a very long time at the console / and searching the internet, use ZFS to build RAID sets. If it were me, I'd use the 2 smaller SSDs for ZIL on a RAIDZ1 set with the 4 big drives and configure the remaining 960Gb drives as a separate volume - not sure what your data usage looks like.

You might consider pulling one of the disks out of there, setting up a RAID5 array with 6 drives, the remaining one as a hot spare and put an ssd configured as an accelerator / cache in the freed slot. And definitely look at the cost for 10G networking between the PVE node and the storage if don't already have that in place.



