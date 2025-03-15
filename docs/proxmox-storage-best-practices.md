Should I use ZFS at all?​
For once this requires a disclaimer first: I am using ZFS nearly everywhere, where it is easily possible, though exceptions do exists. In any case I am definitely biased pro ZFS.

That said..., the correct answer is obviously: “Yes, of course” ;-)

Integrity​
ZFS assures integrity. It will deliver exactly the very same data when you read it as was written at some point of time in the past.

“But all filesystems do this, right?” Well, there is more to it. ZFS works hard to actively assure the correctness. An additional checksum is calculated (and written to disk as “meta-data”) when you write the actual data. When you read the data the same checksum is again re-calculated and only if both are the same it is okay to deliver it to the reading process.

Most other “classic” filesystems just do not do this kind of check and do deliver the data coming from the disk as it is instead. For most on-disk-problems a “read-error” will occur, avoiding to hand over damaged data. This applies to all filesystems, being the next higher level of data flow above the physical disk. These days this can happen every 10^15th block of data read and it is called an “URE” (“Unrecoverable Read Error”).
A much higher number of blocks needs to be read to deliver actually different/wrong/damaged data without an error message reported by that bottom layer. On the other hand this is not the whole story: errors may get introduced not only on the platters or inside an SSD-cell but also on the physical wire, the physical connectors on both ends, on the motherboard’s data bus, in RAM (+ first/second/third level cache) or inside the CPU registers. So yeah, to receive damaged data in your application is not probable but also not impossible! ZFS works hard to avoid this.

Snapshots​
The concept of “copy-on-write” (“CoW”) allows to implement technically cheap snapshots while most other filesystems do not have this capability. “LVM-thick” does not offer snapshot at all and LVM-thin has other drawbacks. Directory storages allow for .qcow-files but they introduce a whole new layer of complexity compared to raw block devices (“ZVOL”) used for virtual disks. (Do not mix this up with PVE-VM-snapshots, used for e.g. backups. That’s a completely independent mechanism.) See (#1) for a table.

Compression​
ZFS allows for transparent and cheap compression - you just can store more data on the same disk. A long time ago the CPU had to do this in discrete software. Since several years all CPUs do that “in hardware” by specific internal instructions - this is usually so fast that you won’t notice any delay. Actually reading/writing data may happen faster as less actual data has to be transferred!

ZFS scales! ​
You can always add an additional vdev at any time to grow capacity. Some people were missing “in-vdev”-“raidz-expansion” which is (probably; not confirmed) coming to PVE in 2025. (It is in ZFS Version 2.3.)

Combining classic HDD plus fast SSD/NVMe​
Using ZFS you can combine old rotating rust and speedy SSD/NVMe by utilizing a “Special Device”. This allows using ZFS in some (but not in each and every) more use cases which are impossible to make a good use of ZFS otherwise. A SD will mainly store pure metadata (and possibly some more “small blocks”, depending on the configuration). This speeds up some operations, depending on the application. Usually the resulting pool could be at least twice as fast as before because we have a higher number vdevs now --> the need of physical head movements is drastically reduced.

And because the SD may be really small (I’ve found values from 0.06%-2.26%, and one of my pools utilizes 1 % of the pool size - already including “small blocks”) this is a cheap and recommended optimization option. Use fast devices in a mirror for this - if the SD dies the pool is completely gone. (If your data is RaidZ2 use a triple mirror!)

Device redundancy​
For a stable and continuous operation you need to have some redundancy. There are several flavors (Mirrors, RaidZ1/2/3) available, as different use cases need different optimization approaches. Note that this is valid on multiple levels - “Storage Devices” only being one of several, for example: “Power Supplies”, “Networking stack including physical Switches”, “Whole Nodes” and probably others. For VM storage always use mirrors, allowing one single device (per vDev) to fail.

Global Checkpoints​
You may create exactly one single checkpoint. This snapshots the whole pool and might be very useful before a large modification happens, think “dist-upgrade”.

Replication​
For “High-Availability” you need to have “Shared Storage”. This may be difficult to create and expensive to setup, at least in a small Homelab. ZFS allows to replicate virtual disks every few minutes to the other cluster members. This qualifies as "being shared" in regard of HA in PVE. When a node fails another one may start the same VM with the previously replicated data. The data written to disk since the last replication point in time ist lost, of course. See (#1).

RAM usage​
Consuming a lot of RAM (for the ARC = Adaptive Replacement Cache) is often criticized when someone stated it is required - which would be bad. See: RAM is used for buffers and caches by each and every filesystem! ZFS is just more clever and makes potentially use of more RAM. The default ARC size used to be 50% of System Ram (which probably was the source of this myth) in the past, but now the documentation states: “For new installations starting with Proxmox VE 8.1, the ARC usage limit will be set to 10 % of the installed physical memory, clamped to a maximum of 16 GiB.”. And you may limit it further, if necessary. See (#2).
But it needs ECC Ram! No, that’s simply not true. ZFS works as fine with non-ECC Ram as any other filesystem does. It is recommended to have ECC in each and every server, completely independent from the used filesystem.

More optimization potential​
This is not a “howto for everything”, so I should stop now - especially as I started with "Homelab" as the target, not a Petabyte datacenter - so take the following list with a grain of salt. But I need at least to mention that there are several more sophisticated approaches to further enhance a pool:
Special Devices = a fast device for metadata - mentioned above.
SLOG = a fast device - will speed up synchronous writes drastically. This is not a “write-cache” and it may be small as it buffers max 10 seconds of incoming data.
Cache = a fast device - acts as a read-cache - only recommended if you have already maxed out the RAM capacity - it consumes RAM, which might already be scarce
Ram, Ram, Ram... ;-)
dRaid = another new approach for large capacities - requires a lot of drives - see (#3).
Deduplicaton = consolidating identical data into one single block - this is usually NOT recommended as it has some heavy drawbacks. But for some specific use cases it may be really great.


Now for the bad news: all of the above comes with a price tag, leading to the most often presented counter arguments:
It requires “Enterprise”-class devices​
For every single write of actual data additional metadata and ZIL (ZFS Intent Log) operations are required. ZFS writes more data more frequent than other filesystems. This is more stress for a cheap SSD than another filesystem would generate and this will shorten the lifetime of a cheap SSD. And it slows down especially “sync-writes”. Usual “async”-data is quickly buffered in Ram for up to 5 seconds before it is written to the ZIL and then to disk, so this should feel fast.
To compensate this “slowing down”-effect it is highly recommended to use “Enterprise”-class devices with “Power-loss-Protection” (“PLP”) instead of cheap “Consumer”-class ones. Unfortunately these devices are much more expensive...

For me this is the only valid counter argument. You may add some more in your reply ;-)


See also:
#1 https://pve.proxmox.com/pve-docs/chapter-pvesm.html#_storage_types
#2 https://pve.proxmox.com/pve-docs/pve-admin-guide.html#sysadmin_zfs_limit_memory_usage
#3 https://openzfs.github.io/openzfs-docs/Basic Concepts/dRAID Howto.html
https://pve.proxmox.com/wiki/ZFS_on_Linux
https://forum.proxmox.com/search/7994094/?q=FabU&c[title_only]=1&c[users]=UdoB&o=date - some more of this series of posts may be added over time...
https://github.com/jameskimmel/opinions_about_tech_stuff/blob/main/ZFS/PLP isn't about security and has nothing to do with your UPS.md
https://www.servethehome.com/what-is-the-zfs-zil-slog-and-what-makes-a-good-one/
search for SSD with PLP, german: https://geizhals.de/?cat=hdssd&xf=4643_Power-Loss+Protection

PS: this post is too long to be static --> edited multiple times to add/correct small details.